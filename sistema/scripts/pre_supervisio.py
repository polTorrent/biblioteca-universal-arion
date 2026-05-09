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
import re
import sys
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

    # 5. Verificar coherència de capítols
    original = obra_dir / "original.md"
    if original.exists():
        orig_text = original.read_text(encoding="utf-8", errors="replace")
        orig_headers = set(re.findall(r'^#{1,3}\s+.+', orig_text, re.M))
        trad_headers = set(re.findall(r'^#{1,3}\s+.+', text, re.M))
        missing = len(orig_headers) - len(orig_headers & trad_headers)
        if missing > 2 and len(orig_headers) > 0:
            issues.append(f"Possible manca de {missing} seccions vs original")

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


# ── Main ────────────────────────────────────────────────────────────────────

def run_supervisio(obra_path: str, output_json: bool = False) -> dict:
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
    }

    # Decisions automàtiques
    accio = "TRADUIR_COMPLET"
    motiu = "Obra sense traducció"

    trad = informe["traduccio"]
    orig = informe["original"]

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
        if trad["completion_pct"] >= 95 and not has_real_errors:
            accio = "SUPERVISAR"
            motiu = f"Traducció {trad['completion_pct']}% completada — només supervisió"
        elif trad["can_continue"] and not has_real_errors:
            accio = "CONTINUAR"
            motiu = f"Traducció al {trad['completion_pct']}% — continuar des chunk {trad['resume_from_chunk']}"
        elif trad["completion_pct"] < 30 and has_real_errors:
            accio = "RETRADUIR"
            motiu = f"Traducció {trad['completion_pct']}% amb errors reals — millor recomençar"
        else:
            accio = "CONTINUAR"
            motiu = f"Traducció al {trad['completion_pct']}% — continuar des chunk {trad['resume_from_chunk']}"

    # Afegir warning si qualitat pipeline anterior era baixa
    if informe["pipeline"]["quality_avg"] is not None and informe["pipeline"]["quality_avg"] < 5:
        if accio == "CONTINUAR":
            accio = "RETRADUIR"
            motiu += " [OVERRIDE: qualitat anterior <5/10, recomanat retraduir]"

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

    print(f"\n{'='*60}")
    emoji = {"TRADUIR_COMPLET": "🆕", "CONTINUAR": "▶️", "RETRADUIR": "🔄",
             "SUPERVISAR": "✅", "BLOQUEJAR": "🛑"}
    print(f"👉 DECISIÓ: {emoji.get(d['accio'], '❓')} {d['accio']} — {d['motiu']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-supervisió d'una obra")
    parser.add_argument("obra_path", help="Ruta de l'obra (ex: obres/filosofia/aristotil/peri-psykhes)")
    parser.add_argument("--json", action="store_true", help="Sortida JSON")
    args = parser.parse_args()
    run_supervisio(args.obra_path, output_json=args.json)
