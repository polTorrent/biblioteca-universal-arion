#!/usr/bin/env python3
"""pre_supervisio.py — Supervisió prèvia a traducció.

Analitza una obra ABANS de traduir-la per:
1. Verificar integritat de l'original
2. Comprovar estat de traducció existent
3. Detectar errors de traduccions anteriors
4. Determinar punts de represa (chunks pendents)
5. Generar informe executable pel worker

Ús:
    python3 sistema/scripts/pre_supervisio.py obres/filosofia/aristotil/peri-psykhes
    python3 sistema/scripts/pre_supervisio.py obres/filosofia/aristotil/peri-psykhes --json
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PROJECT = Path.home() / "biblioteca-universal-arion"

# ── Checks ──────────────────────────────────────────────────────────────────

def check_original(obra_dir: Path) -> dict:
    """Verifica integritat de l'original."""
    original = obra_dir / "original.md"
    result = {"exists": original.exists(), "size_bytes": 0, "lines": 0,
              "words": 0, "encoding_ok": True, "empty_lines_pct": 0, "warnings": []}

    if not original.exists():
        result["warnings"].append("Falta original.md — no es pot traduir")
        return result

    try:
        text = original.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result["encoding_ok"] = False
        result["warnings"].append("original.md té problemes d'encoding")
        return result

    result["size_bytes"] = original.stat().st_size
    result["lines"] = text.count("\n") + 1
    result["words"] = len(text.split())
    empty = sum(1 for l in text.split("\n") if not l.strip())
    result["empty_lines_pct"] = round(empty / max(result["lines"], 1) * 100, 1)

    # Detectar si l'original conté metadades web (Problema conegut: Perseus scrapes)
    web_markers = ["URI:", "HTTP", "www.perseus.tufts.edu", "DOCTYPE", "<html",
                   "Creative Commons", "Perseus Digital Library"]
    found_web = [m for m in web_markers if m in text[:5000]]
    if found_web:
        result["warnings"].append(f"original.md conté metadades web: {found_web}")

    # Detectar si l'original està en l'idioma esperat (vs traducció equivocada)
    metadata_path = obra_dir / "metadata.yml"
    if metadata_path.exists():
        try:
            import yaml
            meta = yaml.safe_load(metadata_path.read_text())
            source_lang = meta.get("source_language", "").lower()
            # Si és grec, verificar que hi ha caràcters grecs
            if source_lang in ("grec", "greek", "gr"):
                has_greek = bool(re.search(r'[α-ωά-ώϊϋΐΰ]', text[:3000]))
                if not has_greek:
                    result["warnings"].append(
                        f"metadata indica idioma='{source_lang}' però no es detecten "
                        f"caràcters grecs als primers 3000 chars — possible obra equivocada"
                    )
            # Si és llatí
            elif source_lang in ("llatí", "llati", "latin"):
                has_latin = bool(re.search(r'(?:quod|est|dicit|anim|corpus|anima)', text[:3000], re.I))
                if not has_latin:
                    result["warnings"].append(
                        f"metadata indica idioma='{source_lang}' però no es detecta llatí"
                    )
        except Exception:
            pass

    return result


def check_existing_translation(obra_dir: Path) -> dict:
    """Analitza la traducció existent (si n'hi ha)."""
    traduccio = obra_dir / "traduccio.md"
    result = {"exists": traduccio.exists(), "size_bytes": 0, "lines": 0,
              "words": 0, "completion_pct": 0.0, "quality_issues": [],
              "resume_from_chunk": 0, "can_continue": False}

    if not traduccio.exists():
        return result

    text = traduccio.read_text(encoding="utf-8", errors="replace")
    result["size_bytes"] = traduccio.stat().st_size
    result["lines"] = text.count("\n") + 1
    result["words"] = len(text.split())

    # Calcular % completat vs original
    original = obra_dir / "original.md"
    if original.exists():
        orig_size = original.stat().st_size
        result["completion_pct"] = round(len(text.encode("utf-8")) / max(orig_size, 1) * 100, 1)

    # Detectar problemes de qualitat
    issues = []

    # 1. Blocs ERROR — distingir errors de pagament vs errors reals
    error_lines_raw = [l for l in text.split("\n") if "[ERROR:" in l]
    payment_errors = sum(1 for l in error_lines_raw if "spend limit" in l or "402" in l or "billing" in l.lower() or "quota" in l.lower())
    real_errors = len(error_lines_raw) - payment_errors
    result["payment_errors"] = payment_errors
    result["real_errors"] = real_errors
    if payment_errors > 0:
        issues.append(f"{payment_errors} blocs [ERROR] de pagament — es poden ignorar,Continuar després")
    if real_errors > 0:
        issues.append(f"{real_errors} blocs [ERROR] reals — cal retraduir aquests chunks")

    # 2. Text en anglès (signe d'al·lucinació del model)
    english_patterns = [
        r'\bthe\b', r'\band\b', r'\bis\b', r'\bthat\b', r'\bwith\b',
        r'\bthis\b', r'\bfrom\b', r'\bwhich\b', r'\bwere\b'
    ]
    # Comprovar últims 2000 chars (zona més probable d'errors)
    tail = text[-2000:] if len(text) > 2000 else text
    eng_count = sum(len(re.findall(p, tail, re.I)) for p in english_patterns)
    if eng_count > 15:  # Llindar alt = probablement anglès
        issues.append(f"Possible text en anglès al final ({eng_count} paraules angleses en 2000 chars)")

    # 3. Text buit o placeholders
    placeholder_patterns = ["[TRANSLATION PENDING]", "[NOT TRANSLATED]", "...", "TODO"]
    for ph in placeholder_patterns:
        if ph in text:
            issues.append(f"Placeholder trobat: '{ph}'")

    # 4. Línia massa llarga (possible error de chunking)
    long_lines = sum(1 for l in text.split("\n") if len(l) > 2000)
    if long_lines > 0:
        issues.append(f"{long_lines} línies >2000 chars — possible error de chunking")

    # 5. Verificar estructura — índex, llibres, capítols
    original = obra_dir / "original.md"
    if original.exists():
        orig_text = original.read_text(encoding="utf-8", errors="replace")

        # 5a. Headers duplicats (mateix nivell, mateix text)
        trad_headers = re.findall(r'^(#{1,4})\s+(.+)', text, re.M)
        seen = {}
        for level, title in trad_headers:
            key = f"{level} {title.strip()}"
            seen[key] = seen.get(key, 0) + 1
        dupes = {k: v for k, v in seen.items() if v > 1}
        if dupes:
            for k, v in dupes.items():
                issues.append(f"Header duplicat ({v}x): '{k}' — estructura corrompuda,errors estructurals")

        # 5b. Nombre de llibres/parts — comparar amb original
        orig_books = re.findall(r'^##\s+.+', orig_text, re.M)
        trad_books = re.findall(r'^##\s+.+', text, re.M)
        if len(orig_books) > 0 and len(trad_books) > len(orig_books) * 1.5:
            issues.append(f"Massa headers H2: original={len(orig_books)}, traducció={len(trad_books)} — possible duplicació de chunks,errors estructurals")

        # 5c. Ordre de capítols — detectar desordenació
        trad_h3_nums = re.findall(r'^###\s+(?:Capítol|Chapter|Κεφάλαιον)\s+(\d+)', text, re.M)
        if len(trad_h3_nums) > 3:
            nums = [int(n) for n in trad_h3_nums]
            for i in range(1, len(nums)):
                if nums[i] < nums[i-1] and nums[i] != 1:
                    issues.append(f"Capítols desordenats: #{nums[i-1]} seguit de #{nums[i]} — possible chunk desordenat,errors estructurals")
                    break

        # 5d. Detectar línees d'índex (TOC) que haurien d'estar al principi
        toc_lines = [l for l in text.split("\n") if re.match(r'^\s*[-*]\s+.*\.\.\.+', l) or re.match(r'^\s*\d+\.\s+\[', l)]
        if toc_lines and not text.strip().startswith("#"):
            issues.append(f"{len(toc_lines)} línies d'índex (TOC) trobades però no al principi — possible chunk erroni,errors estructurals")

        # 5e. Text no traduït — fragments en idioma original al mig
        orig_lang_markers = ["Κεφάλαιον", "Βιβλίον", "Chapter", "Buch"]
        orig_lang_in_trad = sum(1 for l in text.split("\n") if any(m in l for m in orig_lang_markers))
        if orig_lang_in_trad > 3:
            issues.append(f"{orig_lang_in_trad} línies amb headers en idioma original — possible fragment no traduït,errors estructurals")

    result["quality_issues"] = issues

    # Determinar si es pot continuar — només errors REALS bloquegen
    has_real_errors = any("reals" in i for i in issues)
    if result["completion_pct"] < 5:
        result["can_continue"] = False
        result["resume_from_chunk"] = 0
    elif has_real_errors:
        # Errors reals — millor recomençar si la traducció és curta
        if result["completion_pct"] < 30:
            result["can_continue"] = False
            result["resume_from_chunk"] = 0
        else:
            result["can_continue"] = True
            result["resume_from_chunk"] = max(0, len(text) // 1000 - 2)
    else:
        result["can_continue"] = True
        result["resume_from_chunk"] = len(text) // 1000  # CHUNK_SIZE=1000

    return result


def check_pipeline_state(obra_dir: Path) -> dict:
    """Analitza l'estat del pipeline anterior."""
    state_file = obra_dir / ".pipeline_state.json"
    result = {"exists": state_file.exists(), "errors": [], "warnings": [],
              "quality_avg": None, "phase": None}

    if not state_file.exists():
        return result

    try:
        state = json.loads(state_file.read_text())
        result["phase"] = state.get("fase_actual")
        result["quality_avg"] = state.get("metrics", {}).get("qualitat_mitjana")
        result["errors"] = state.get("errors", [])[:10]  # Primers 10
        result["warnings"] = state.get("warnings", [])[:5]

        if result["quality_avg"] is not None and result["quality_avg"] < 5.0:
            result["warnings"].append(
                f"Qualitat anterior {result['quality_avg']}/10 — considerar retraducció"
            )
    except Exception as e:
        result["warnings"].append(f"Error llegint .pipeline_state.json: {e}")

    return result


def check_glossary(obra_dir: Path) -> dict:
    """Verifica que el glossari existeix i és usable."""
    glossari = obra_dir / "glossari.yml"
    result = {"exists": glossari.exists(), "terms": 0, "warnings": []}

    if not glossari.exists():
        result["warnings"].append("Falta glossari.yml — la traducció pot ser menys consistent")
        return result

    try:
        import yaml
        data = yaml.safe_load(glossari.read_text())
        termes = data.get("termes", [])
        result["terms"] = len(termes) if isinstance(termes, list) else 0
        if result["terms"] == 0:
            result["warnings"].append("glossari.yml no té termes definits")
    except Exception as e:
        result["warnings"].append(f"Error llegint glossari.yml: {e}")

    return result


def check_metadata(obra_dir: Path) -> dict:
    """Verifica metadata.yml."""
    meta = obra_dir / "metadata.yml"
    result = {"exists": meta.exists(), "fields": {}, "warnings": []}

    if not meta.exists():
        result["warnings"].append("Falta metadata.yml")
        return result

    try:
        import yaml
        data = yaml.safe_load(meta.read_text())
        required = ["title", "author", "source_language", "category"]
        for f in required:
            result["fields"][f] = bool(data.get(f))
            if not data.get(f):
                result["warnings"].append(f"metadata.yml falta camp: {f}")
    except Exception as e:
        result["warnings"].append(f"Error llegint metadata.yml: {e}")

    return result


# ── Revisió amb model lleuger ───────────────────────────────────────────────

VENICE_API_BASE = "https://api.venice.ai/api/v1"


def _venice_api_key() -> str | None:
    """Obté la clau API de Venice."""
    key = os.environ.get("VENICE_API_KEY", "").strip()
    if key:
        return key
    # Provar .env al projecte
    env_file = PROJECT / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if line.startswith("VENICE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def check_with_llm(obra_dir: Path, _sample_chars: int = 6000) -> dict:
    """
    Revisa l'estructura de la traducció amb un model lleuger (~0.15 DIEM).
    En lloc d'enviar contingut tallat (que confon el model), envia:
    - Tota la jerarquia de headers (H1-H4)
    - Enllaços interns trobats
    - Índex (TOC) si existeix
    - Mides del document per context

    Detecta: headers desordenats, duplicats, capítols que falten,
    enllaços trencats, índex mal format.
    """
    traduccio = obra_dir / "traduccio.md"
    original = obra_dir / "original.md"
    result = {"llm_checked": False, "llm_available": False, "issues": [], "cost_diems": 0.0}

    if not traduccio.exists():
        return result

    api_key = _venice_api_key()
    if not api_key:
        result["issues"].append("LLM: VENICE_API_KEY no trobada — check estructura manual")
        return result

    # Extreure estructura del document
    text = traduccio.read_text(encoding="utf-8", errors="replace")
    orig_text = original.read_text(encoding="utf-8", errors="replace") if original.exists() else ""

    # Headers del text traduït
    trad_headers = re.findall(r'^(#{1,4})\s+(.+)', text, re.M)
    headers_list = "\n".join(f"{level} {title}" for level, title in trad_headers)

    # Headers de l'original (per comparar)
    orig_headers = re.findall(r'^(#{1,4})\s+(.+)', orig_text, re.M) if orig_text else []
    orig_headers_list = "\n".join(f"{level} {title}" for level, title in orig_headers)

    # Enllaços interns
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
    links_broken = []
    for label, target in links:
        if target.startswith("#"):
            anchor = target[1:]
            # Normalitzar: treure accents i minúscules per comparar amb headers
            anchor_norm = re.sub(r'[^\w\s-]', '', anchor).lower().replace(" ", "-")
            header_texts = [re.sub(r'[^\w\s-]', '', t).lower().replace(" ", "-") for _, t in trad_headers]
            if anchor_norm not in header_texts:
                links_broken.append(f"[{label}](#{anchor})")
    links_text = "\n".join(links_broken) if links_broken else "Cap enllaç intern trencat detectat"

    # Índex (TOC) — línies amb puntets o numeració
    toc_lines = [l for l in text.split("\n") if re.match(r'^\s*[-*\d]\s+', l) and ("..." in l or "[#" in l)]
    toc_text = "\n".join(toc_lines[:30]) if toc_lines else "No s'ha detectat índex formal"

    prompt = f"""Ets un editor expert en estructura de textos acadèmics. Revisa aquesta estructura de document.

DADES DEL DOCUMENT:
- Mida total: {len(text)} caràcters, {text.count(chr(10))} línies
- Mida original: {len(orig_text)} caràcters

JERARQUIA DE HEADERS (tots els # del document traduït):
{headers_list}

HEADERS DE L'ORIGINAL (per comparar):
{orig_headers_list}

ENLLAÇOS INTERNES TRENCATS (si n'hi ha):
{links_text}

TAULA DE CONTINGUTS (si existeix):
{toc_text}

INSTRUCCIONS:
1. Compara els headers de la traducció amb els de l'original. Detecta si falten capítols, hi ha duplicats, o l'ordre és incorrecte.
2. Revisa els enllaços interns: si hi ha enllaços que apunten a headers inexistents, són trencats.
3. Revisa l'índex: si existeix, comprova que coincideixi amb els headers reals del document.
4. NOMÉS reporta problemes OBJECTIVAMENT demostrables. NO imaginin problemes.
5. IMPORTANT: La presència/absència del nom de l'autor com a header NO és un error. Els traductors sovint canvien els nivells de headers.
6. IMPORTANT: NOMÉS reporta MISSING_SECTION si falten MÚLTIPLES capítols/seccions (3 o més), NO per un sol header que falta.
7. IMPORTANT: Una traducció incompleta (menys headers que l'original) és NORMAL si encara està en curs. NO la reportis com a defecte llevat que faltin molts capítols clau.

Respon EXACTAMENT en aquest format JSON (sense markdown, sense explicacions):

{{"problemes": [{{"tipus": "MISSING_SECTION|BROKEN_TOC|LINK_BROKEN|DUPLICATE|WRONG_ORDER|STRUCTURE", "descripcio": "...", "gravetat": "ALTA|MITJA|BAIXA"}}], "verdict": "OK|AMBIGU|DEFECTUOS"}}

On:
- MISSING_SECTION = capítol/secció falta (comparant traducció vs original, només si n'hi ha molts de diferència)
- BROKEN_TOC = índex incomplet o no coincideix amb headers
- LINK_BROKEN = enllaç intern apunta a header inexistent
- DUPLICATE = header exacte duplicat
- WRONG_ORDER = ordre numèric de capítols incorrecte (ex: 1, 3, 2)
- STRUCTURE = altre problema objectiu (NO incloguis diferències de nivell de headers, que són normals en traduccions)"""

    payload = {
        "model": "zai-org-glm-5",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 600,
        "venice_parameters": {"disable_thinking": True, "strip_thinking_response": True}
    }

    try:
        req = urllib.request.Request(
            f"{VENICE_API_BASE}/chat/completions",
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload).encode()
        )
        resp = urllib.request.urlopen(req, timeout=45)
        data = json.loads(resp.read())

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        result["cost_diems"] = round(usage.get("total_tokens", 3000) / 1000 * 0.15, 3)

        # Parsejar JSON
        content_clean = content.strip()
        if content_clean.startswith("```"):
            lines = content_clean.split("\n")
            content_clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        start = content_clean.find("{")
        end = content_clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            llm_result = json.loads(content_clean[start:end+1])
        else:
            llm_result = {"problemes": [], "verdict": "OK"}

        result["llm_checked"] = True
        result["llm_available"] = True
        result["llm_verdict"] = llm_result.get("verdict", "AMBIGU")

        for p in llm_result.get("problemes", []):
            grav = p.get("gravetat", "BAIXA")
            desc = p.get("descripcio", "")
            tipus = p.get("tipus", "STRUCTURE")
            if grav in ("ALTA", "MITJA") and desc:
                result["issues"].append(f"[LLM-{tipus}] {desc} (gravetat: {grav})")

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:200]
        result["issues"].append(f"LLM: Error HTTP {e.code} — {err_body}")
    except json.JSONDecodeError as e:
        result["issues"].append(f"LLM: Error parsejant resposta del model — {e}")
    except Exception as e:
        result["issues"].append(f"LLM: Error de connexió — {e}")

    return result


# ── Main ────────────────────────────────────────────────────────────────────

def run_supervisio(obra_path: str, output_json: bool = False, use_llm: bool = True) -> dict:
    """Executa totes les comprovacions i retorna informe."""
    obra_dir = PROJECT / obra_path if not Path(obra_path).is_absolute() else Path(obra_path)

    if not obra_dir.exists():
        print(f"❌ Directori no trobat: {obra_dir}", file=sys.stderr)
        sys.exit(1)

    informe = {
        "obra": str(obra_path),
        "original": check_original(obra_dir),
        "traduccio": check_existing_translation(obra_dir),
        "pipeline": check_pipeline_state(obra_dir),
        "glossari": check_glossary(obra_dir),
        "metadata": check_metadata(obra_dir),
        "llm_review": check_with_llm(obra_dir) if use_llm else {"llm_checked": True, "llm_available": False, "issues": ["Omitit per --no-llm"], "cost_diems": 0.0},
    }

    # Decisions automàtiques
    accio = "TRADUIR_COMPLET"
    motiu = "Obra sense traducció"

    trad = informe["traduccio"]
    orig = informe["original"]
    llm = informe["llm_review"]

    # Problemes estructurals del LLM poden canviar la decisió
    llm_high = any("(gravetat: ALTA)" in i for i in llm.get("issues", []))
    llm_med = any("(gravetat: MITJA)" in i for i in llm.get("issues", []))
    llm_defectuos = llm.get("llm_verdict") == "DEFECTUOS"
    # Estructura trencada: NO retraduir, només notificar. L'usuari decideix.
    llm_struct_critical = False  # Desactivat: mai esborrar traducció automàticament
    # MISSING_SECTION mai és crític — sempre és més intel·ligent completar que recomençar
    llm_missing_critical = False
    llm_missing_completar = any("MISSING_SECTION" in i for i in llm.get("issues", []))

    if not orig["exists"]:
        accio = "BLOQUEJAR"
        motiu = "No existeix original.md"
    elif orig["warnings"]:
        # Si hi ha metadades web o obra equivocada
        web_warnings = [w for w in orig["warnings"] if "web" in w.lower() or "equivocada" in w.lower()]
        if web_warnings:
            accio = "BLOQUEJAR"
            motiu = "; ".join(web_warnings)
    elif trad["exists"]:
        has_real_errors = any("reals" in i for i in trad["quality_issues"])
        has_struct_errors = any("errors estructurals" in i for i in trad["quality_issues"])

        # OVERRIDE: qualitat anterior desastrosa (encara és l'únic que pot activar RETRADUIR)
        if trad["completion_pct"] < 30 and has_real_errors:
            accio = "RETRADUIR"
            motiu = f"Traducció {trad['completion_pct']}% amb errors reals — millor recomençar"
        elif trad["completion_pct"] >= 95 and not has_real_errors and not has_struct_errors and not llm_high:
            accio = "SUPERVISAR"
            motiu = f"Traducció {trad['completion_pct']}% completada — només supervisió"
        elif trad["can_continue"] and not has_real_errors and not llm_high:
            accio = "CONTINUAR"
            motiu = f"Traducció al {trad['completion_pct']}% — continuar des chunk {trad['resume_from_chunk']}"
        else:
            accio = "CONTINUAR"
            motiu = f"Traducció al {trad['completion_pct']}% — continuar des chunk {trad['resume_from_chunk']}"
    # Afegir warning si qualitat pipeline anterior era baixa
    if informe["pipeline"]["quality_avg"] is not None and informe["pipeline"]["quality_avg"] < 5:
        if accio == "CONTINUAR":
            accio = "RETRADUIR"
            motiu += " [OVERRIDE: qualitat anterior <5/10, recomanat retraduir]"

    # Si LLM troba problemes mitjans, afegir com a nota però no canviar acció
    if llm_med and accio in ("CONTINUAR", "SUPERVISAR"):
        motiu += f" [LLM: {len(llm['issues'])} problemes estructurals detectats]"

    informe["decisio"] = {"accio": accio, "motiu": motiu}

    if output_json:
        print(json.dumps(informe, ensure_ascii=False, indent=2))
    else:
        print_supervisio(informe)

    return informe


def print_supervisio(informe: dict):
    """Imprimeix informe llegible per humans."""
    d = informe["decisio"]
    print(f"{'='*60}")
    print(f"📋 PRE-SUPERVISIÓ: {informe['obra']}")
    print(f"{'='*60}")

    o = informe["original"]
    print(f"\n📖 Original: {o['words']} paraules, {o['lines']} línies, {o['size_bytes']/1024:.1f}KB")
    for w in o["warnings"]:
        print(f"   ⚠️  {w}")

    t = informe["traduccio"]
    if t["exists"]:
        print(f"\n📝 Traducció: {t['words']} paraules, {t['completion_pct']}% completat")
        print(f"   Pot continuar: {'✅' if t['can_continue'] else '❌'} (des chunk {t['resume_from_chunk']})")
        for i in t["quality_issues"]:
            print(f"   🔴 {i}")
    else:
        print(f"\n📝 Traducció: ❌ No existeix")

    p = informe["pipeline"]
    if p["exists"]:
        print(f"\n🔧 Pipeline: fase={p['phase']}, qualitat={p['quality_avg']}/10")
        for e in p["errors"][:3]:
            print(f"   🔴 {e}")

    g = informe["glossari"]
    print(f"\n📚 Glossari: {'✅' if g['exists'] else '❌'} ({g['terms']} termes)")
    for w in g["warnings"]:
        print(f"   ⚠️  {w}")

    m = informe["metadata"]
    print(f"\n📋 Metadata: {'✅' if m['exists'] else '❌'}")
    for w in m["warnings"]:
        print(f"   ⚠️  {w}")

    # Resultats del LLM
    llm = informe.get("llm_review", {})
    if llm.get("llm_checked"):
        print(f"\n🤖 Revisió LLM ({llm.get('cost_diems', 0)} DIEM):")
        print(f"   Verdict: {llm.get('llm_verdict', '—')}")
        if llm.get("issues"):
            for i in llm["issues"]:
                print(f"   🔴 {i}")
        else:
            print(f"   ✅ Sense problemes estructurals detectats")
    elif llm.get("llm_available") is False and llm.get("issues"):
        print(f"\n🤖 Revisió LLM: ⚠️  {llm['issues'][0]}")

    print(f"\n{'='*60}")
    emoji = {"TRADUIR_COMPLET": "🆕", "CONTINUAR": "▶️", "RETRADUIR": "🔄",
             "SUPERVISAR": "✅", "BLOQUEJAR": "🛑"}
    print(f"👉 DECISIÓ: {emoji.get(d['accio'], '❓')} {d['accio']} — {d['motiu']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-supervisió d'una obra")
    parser.add_argument("obra_path", help="Ruta de l'obra (ex: obres/filosofia/aristotil/peri-psykhes)")
    parser.add_argument("--json", action="store_true", help="Sortida JSON")
    parser.add_argument("--no-llm", action="store_true", help="Ometre revisió amb model lleuger (estalvia DIEM)")
    args = parser.parse_args()

    run_supervisio(args.obra_path, output_json=args.json, use_llm=not args.no_llm)
