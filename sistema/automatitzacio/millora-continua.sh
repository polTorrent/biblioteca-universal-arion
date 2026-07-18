#!/bin/bash
# =============================================================================
# millora-continua.sh — Agent de millora contínua per obres validades
# =============================================================================
# Analitza totes les obres amb .validated i detecta problemes de qualitat,
# completesa i presència web. Crea tasques de tipus "improve" per corregir-los.
#
# Ús:
#   bash sistema/automatitzacio/millora-continua.sh              # Selecciona màx 2 obres
#   bash sistema/automatitzacio/millora-continua.sh --dry-run    # Mostra taula sense crear tasques
#   bash sistema/automatitzacio/millora-continua.sh --all        # Selecciona totes amb score > 0
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
TASKS_DIR="${TASKS_DIR:-$PROJECT/sistema/tasks}"
TASK_MANAGER="${TASK_MANAGER:-$PROJECT/sistema/automatitzacio/task-manager.sh}"
METRICS_DIR="$PROJECT/metrics"
REPORT_FILE="$METRICS_DIR/millora-continua-report.md"
LOG="${LOG:-$HOME/claude-worker.log}"
MAX_OBRES=2

DRY_RUN=false
SELECT_ALL=false

mkdir -p "$METRICS_DIR"
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# ── Arguments ─────────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --all)     SELECT_ALL=true ;;
    esac
done

# ── Logger ────────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MILLORA] $1" | tee -a "$LOG"; }

# =============================================================================
# ANÀLISI PRINCIPAL (Python)
# =============================================================================
run_analysis() {
    python3 << 'PYEOF'
import json, os, re, time, sys
from pathlib import Path
from datetime import datetime, timedelta

project = os.environ.get('PROJECT', os.path.expanduser('~/biblioteca-universal-arion'))
dry_run = os.environ.get('DRY_RUN', 'false') == 'true'
select_all = os.environ.get('SELECT_ALL', 'false') == 'true'
max_obres = int(os.environ.get('MAX_OBRES', '2'))
report_file = os.environ.get('REPORT_FILE', os.path.join(project, 'metrics', 'millora-continua-report.md'))

obres_dir = Path(project) / 'obres'
docs_dir = Path(project) / 'docs'
epub_dir = docs_dir / 'epub'

now = time.time()
day30 = 30 * 86400
day60 = 60 * 86400
day90 = 90 * 86400

# Llegir docs/data/*.json i docs/index.html per verificar presència web.
# La web de Biblioteca Arion carrega el catàleg via JSON (docs/data/cataleg-traduccions.json
# i docs/data/search-index.json); el slug de cada obra apareix com a href o filename "slug.html".
# Per això cal comprovar el SLUG (no obra_name) en aquests fitxers de dades, i també que
# existeixi docs/{slug}.html.
web_data_content = ''
for jf in ['data/cataleg-traduccions.json', 'data/search-index.json', 'index.html']:
    p = docs_dir / jf
    if p.exists():
        web_data_content += p.read_text(errors='ignore') + '\n'

results = []

if not obres_dir.exists():
    print("ERROR|No existeix obres/", file=sys.stderr)
    sys.exit(1)

for cat_dir in sorted(obres_dir.iterdir()):
    if not cat_dir.is_dir():
        continue
    for aut_dir in sorted(cat_dir.iterdir()):
        if not aut_dir.is_dir():
            continue
        for obra_dir in sorted(aut_dir.iterdir()):
            if not obra_dir.is_dir():
                continue

            validated_file = obra_dir / '.validated'
            if not validated_file.exists():
                continue

            obra_name = obra_dir.name
            relpath = str(obra_dir.relative_to(Path(project)))
            problems = []
            improvement_score = 0

            # ── 1. Puntuació del .validated ──
            validated_text = validated_file.read_text(errors='ignore')
            score = 7.0  # default
            m = re.search(r'(?:puntuacio_global|qualitat|score|puntuació)\s*[:=]\s*(\d+\.?\d*)', validated_text)
            if m:
                score = float(m.group(1))

            if score < 7.0:
                improvement_score += 50
                problems.append(f"Puntuació molt baixa ({score}/10)")
            elif score < 8.0:
                # Puntuació dins el llindar acceptable (>=7/10) en mode
                # CONSOLIDACIÓ: no és un problema real, només informatiu.
                # Pondera amb 5 (no 20) per evitar que "envelliment + puntuació
                # generi una riuada de tasques improve sense valor real.
                # Les obres a 7.0 es milloraran quan es detecti un problema
                # estructural real (auditor 09 cada 12h, al·lucinació, falta
                # de portada, notes trencades, etc.).
                improvement_score += 5
                problems.append(f"Puntuació dins llindar ({score}/10)")

            # ── 1b. CHECK AL·LUCINACIÓ (PRIORITAT MÀXIMA) ──
            original_file = obra_dir / 'original.md'
            traduccio_file = obra_dir / 'traduccio.md'
            audit_manual_file = obra_dir / '.audit_manual'
            audit_skip_allucinacio = (
                audit_manual_file.exists()
                and 'al_lucinacio_skip' in audit_manual_file.read_text(errors='ignore')
            )
            if (not audit_skip_allucinacio) and original_file.exists() and traduccio_file.exists():
                import subprocess
                verificador = Path(project) / 'scripts' / 'verificar_traduccio.py'
                if verificador.exists():
                    try:
                        result = subprocess.run(
                            ['python3', str(verificador), str(original_file), str(traduccio_file)],
                            capture_output=True, text=True, timeout=30
                        )
                        if result.returncode != 0:
                            improvement_score += 50
                            problems.append("🚨 POSSIBLE AL·LUCINACIÓ — Recompte d'unitats no coincideix")
                    except Exception:
                        pass

            # ── 2. Antiguitat del .validated ──
            validated_mtime = validated_file.stat().st_mtime
            age_days = int((now - validated_mtime) / 86400)

            if age_days < 30:
                # Massa recent, saltar
                continue

            if age_days > 90:
                # Envelliment informatiu, no problema real per se. Pondera
                # amb 5 (no 20) per evitar la riuada de tasques improve
                # cosmètiques (vegeu nota del bloc de puntuació).
                improvement_score += 5
                problems.append(f"Validació antiga ({age_days} dies)")
            elif age_days > 60:
                improvement_score += 2
                problems.append(f"Validació envellint ({age_days} dies)")

            # ── 3. Portada ──
            portada = obra_dir / 'portada.png'
            if not portada.exists():
                improvement_score += 15
                problems.append("Falta portada.png")
            elif portada.stat().st_size < 10240:
                improvement_score += 15
                problems.append(f"Portada massa petita ({portada.stat().st_size} bytes)")

            # ── 4. metadata.yml ──
            metadata_file = obra_dir / 'metadata.yml'
            required_meta_fields = ['title', 'author', 'source_language', 'category', 'translator', 'date']
            missing_meta = []
            if not metadata_file.exists():
                missing_meta = required_meta_fields[:]
                improvement_score += len(required_meta_fields) * 5
                problems.append("Falta metadata.yml")
            else:
                meta_text = metadata_file.read_text(errors='ignore')
                # Comprovar camps (suporta formats amb i sense obra:)
                for field in required_meta_fields:
                    # Acceptar variants: title/titol, author/autor, etc.
                    variants = {
                        'title': ['title', 'titol'],
                        'author': ['author', 'autor'],
                        'source_language': ['source_language', 'llengua_original'],
                        'category': ['category', 'categoria', 'genere'],
                        'translator': ['translator', 'traductor'],
                        'date': ['date', 'any_traduccio', 'data']
                    }
                    found = False
                    for v in variants.get(field, [field]):
                        if re.search(rf'^\s*{v}\s*:', meta_text, re.MULTILINE):
                            found = True
                            break
                    if not found:
                        missing_meta.append(field)
                        improvement_score += 5

                if missing_meta:
                    problems.append(f"Metadata incompleta: {', '.join(missing_meta)}")

            # ── 5. traduccio.md — qualitat del contingut ──
            traduccio_file = obra_dir / 'traduccio.md'
            bad_lines = []
            word_count = 0
            has_h1 = False
            has_h2 = False
            note_refs = set()

            if traduccio_file.exists():
                trad_text = traduccio_file.read_text(errors='ignore')
                word_count = len(trad_text.split())

                if word_count < 500:
                    improvement_score += 10
                    problems.append(f"Traducció massa curta ({word_count} paraules)")

                for line in trad_text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('# '):
                        has_h1 = True
                    if stripped.startswith('## '):
                        has_h2 = True
                    for pattern in ['ERROR:', 'PLACEHOLDER', 'TODO', '[FALTA', '[MISSING']:
                        if pattern in stripped:
                            bad_lines.append(pattern)

                if not has_h1:
                    improvement_score += 5
                    problems.append("traduccio.md sense capçalera #")

                if bad_lines:
                    unique_bad = list(set(bad_lines))
                    improvement_score += 25
                    problems.append(f"Línies problemàtiques: {', '.join(unique_bad[:5])}")

                # Extreure referències [N] per comprovar notes
                # S'exclouen els [N] que estan enganxats a un caràcter alfanumèric
                # (com els "Fragment 7[21]" de KSA-Nietzsche, que són referències
                # editorials i no pas notes del traductor). Sense això, fragments-postums
                # i altres obres amb notació "Fragment N[M]" es marcaven falsament.
                note_refs = set(re.findall(r'(?<![A-Za-z0-9À-ÿ])\[(\d+)\](?![A-Za-z0-9À-ÿ])', trad_text))
                # Notes definides INLINE al final del propi traduccio.md
                # (format clàssic "^[1] Text..." o "[1] Text..." a inici de línia)
                # Aquestes no són "rocades": són les definicions reals del peu.
                # Sense aquest filtre, obres com hayy-ibn-yaqzan o micromegas
                # es marcaven falsament com a "notes trencades" quan de fet les
                # notes hi estan embedides correctament.
                inline_defined = set(re.findall(r'^\s*[\^]?\[(\d+)\][\s\.\,\;\:\u2014\u2026\)]', trad_text, re.MULTILINE))
                # Notes Markdown footnotes [^N]: definicions a peu de pàgina clàssic
                inline_defined |= set(re.findall(r'^\[\^(\d+)\]:', trad_text, re.MULTILINE))
                note_refs = note_refs - inline_defined
            else:
                improvement_score += 30
                problems.append("Falta traduccio.md")

            # ── 6. notes.md — coherència amb traduccio.md ──
            notes_file = obra_dir / 'notes.md'
            if notes_file.exists() and note_refs:
                notes_text = notes_file.read_text(errors='ignore')
                defined_notes = set(re.findall(r'##\s*\[(\d+)\]', notes_text))
                broken_refs = note_refs - defined_notes
                if broken_refs:
                    improvement_score += len(broken_refs) * 10
                    problems.append(f"Notes trencades: [{'], ['.join(sorted(broken_refs, key=int)[:5])}]")

            # ── 7. glossari.yml ──
            glossari_file = obra_dir / 'glossari.yml'
            if glossari_file.exists():
                glossari_text = glossari_file.read_text(errors='ignore').strip()
                # Comptar entrades: normalment cada entrada és una línia YAML
                # amb `  - original: ...`. Per això cal un patró que permeti
                # espais inicials (indentació YAML) abans del ` - `. El patró
                # `^-\s` (anterior) no coincideix amb línies indentades i donava
                # fals positius: es queia al fallback `^\w.*:` que només comptava
                # el nom de la clau arrel (p.ex "termes:"), marcant gairebé tots
                # els glossaris com a "pobres (1 entrada)".
                entries = len(re.findall(r'^\s*-\s', glossari_text, re.MULTILINE))
                if entries == 0:
                    # Fallback: comptar claus al primer nivell (format pla)
                    entries = len(re.findall(r'^\w.*:', glossari_text, re.MULTILINE))
                if entries < 3:
                    improvement_score += 5
                    problems.append(f"Glossari pobre ({entries} entrades)")

            # ── 8. EPUB ──
            # Construir slug esperant: autor_dir-obra_dir
            slug = f"{aut_dir.name}-{obra_name}"
            epub_file = epub_dir / f"{slug}.epub"
            if not epub_file.exists():
                improvement_score += 5
                problems.append("Falta EPUB")

            # ── 9. Web (presència a docs/{slug}.html + dades JSON) ──
            # El bug anterior cercava `obra_name` literal dins docs/index.html,
            # però l'index.html carrega els continguts via JS/JSON, o sigui que
            # mai trobava el nom i marcava totes les obres com "no apareix a la web".
            # Ara fem la comprovació correcta amb el SLUG real.
            obra_html_file = docs_dir / f"{slug}.html"
            slug_in_web_data = (f"{slug}.html" in web_data_content) or (slug in web_data_content)
            if not obra_html_file.exists():
                improvement_score += 20
                problems.append(f"No apareix a la web (falta docs/{slug}.html)")
            elif not slug_in_web_data:
                improvement_score += 15
                problems.append(f"Slug '{slug}' no indexat al catàleg web (data/*.json)")

            results.append({
                'obra_name': obra_name,
                'relpath': relpath,
                'score': score,
                'age_days': age_days,
                'improvement_score': improvement_score,
                'problems': problems,
                'word_count': word_count,
                'missing_meta': missing_meta,
            })

# Ordenar per improvement_score desc
results.sort(key=lambda x: x['improvement_score'], reverse=True)

# ── Generar report ──
report_lines = [
    f"# Millora Contínua — Report {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
    f"Total obres validades analitzades: {len(results)}",
    "",
    "| Obra | Puntuació | Edat (dies) | Improvement | Problemes |",
    "|------|-----------|-------------|-------------|-----------|",
]

for r in results:
    probs = '; '.join(r['problems'][:3]) if r['problems'] else 'OK'
    report_lines.append(
        f"| {r['obra_name']} | {r['score']}/10 | {r['age_days']} | {r['improvement_score']} | {probs} |"
    )

report_lines.append("")
ok_count = sum(1 for r in results if r['improvement_score'] == 0)
problem_count = sum(1 for r in results if r['improvement_score'] > 0)
report_lines.append(f"Resum: {ok_count} obres OK, {problem_count} amb millores possibles.")

report_text = '\n'.join(report_lines) + '\n'
with open(report_file, 'w') as f:
    f.write(report_text)

# ── Seleccionar obres ──
# Llindar REAL_PROBLEM_THRESHOLD = 30: només es generen tasques improve quan
# l'improvement_score és prou alt (problemàtica REAL acumulada). Per sota
# del llindar hi queden només flags cosmètics (envelliment +5/+2, puntuació
# 7-8 +5) que, combinats, sumen com a molt 12 — i per tant no generen tasques.
# Així s'evita la riuada de tasques improve sense valor real que saturaven
# la cua i feien caure el worker en un bucle de fracàs 0s (Venice chat
# rebutja executar shell).
# Real catch confirmat: al·lucinació (+50), score<7.0 (+50), manca de
# traduccio.md (+30), manca total de metadata (+30), "no web.html" + altre
# structural, notes trencades múltiples, etc. Els problemes estructurals
# individuals (portada sola, glossari pobre sol) els continua cobrint el
# mòdul 09-audit-catalog.sh cada 12h, independentment d'aquest script.
REAL_PROBLEM_THRESHOLD = 30
selected = [r for r in results if r['improvement_score'] >= REAL_PROBLEM_THRESHOLD]
if not select_all:
    selected = selected[:max_obres]

# ── Output ──
# Primer, imprimir la taula completa per al log
for r in results:
    probs = '; '.join(r['problems'][:3]) if r['problems'] else 'OK'
    marker = '>>>' if r in selected and not dry_run else '   '
    print(f"TABLE|{marker}|{r['obra_name']}|{r['score']}|{r['age_days']}|{r['improvement_score']}|{probs}")

# Després, les obres seleccionades per crear tasques
if not dry_run:
    for r in selected:
        # Construir instrucció detallada
        actions = []
        for p in r['problems']:
            if 'ERROR' in p or 'PLACEHOLDER' in p or 'TODO' in p or 'FALTA' in p or 'MISSING' in p:
                actions.append(f"Corregir línies problemàtiques a traduccio.md (llegir original.md i retraduir fragments)")
            elif 'Metadata' in p or 'metadata' in p:
                actions.append(f"Omplir camps metadata faltants: {', '.join(r['missing_meta'])}")
            elif 'Notes trencades' in p:
                actions.append(f"Crear entrades ## [N] a notes.md per les referències trencades")
            elif 'portada' in p.lower():
                actions.append(f"Generar portada: python3 sistema/traduccio/generar_portades.py {r['relpath']}")
            elif 'Puntuació' in p:
                actions.append(f"Millorar estil/qualitat: python3 sistema/traduccio/traduir_pipeline.py {r['relpath']}/ --mode millora")
            elif 'EPUB' in p:
                actions.append(f"Generar EPUB amb EpubGenerator")
            elif 'web' in p.lower():
                actions.append(f"Regenerar web: python3 sistema/web/build.py")
            elif 'Glossari' in p:
                actions.append(f"Ampliar glossari.yml (mínim 5 entrades significatives)")
            elif 'curta' in p:
                actions.append(f"Completar traducció (ara té {r['word_count']} paraules)")
            elif 'capçalera' in p:
                actions.append(f"Afegir capçalera # al traduccio.md")

        instruction = (
            f"MILLORA CONTÍNUA de '{r['obra_name']}' a {r['relpath']} "
            f"(puntuació actual: {r['score']}/10, improvement_score: {r['improvement_score']}). "
            f"Problemes detectats: {'; '.join(r['problems'])}. "
            f"Accions: {' | '.join(actions)}. "
            f"Finalment: re-avaluar qualitat, actualitzar .validated amb nova puntuació i data. "
            f"python3 sistema/web/build.py && git add -A && git commit -m \"improve: {r['obra_name']}\" && git push"
        )
        print(f"TASK|{r['obra_name']}|{r['relpath']}|{instruction}")

print(f"SUMMARY|{len(results)}|{ok_count}|{problem_count}|{len(selected)}")
PYEOF
}

# =============================================================================
# MAIN
# =============================================================================
log "═══════════════════════════════════════════════════"
log "Millora Contínua — Sessió iniciada"

# Exportar variables per Python
export PROJECT TASKS_DIR REPORT_FILE
export DRY_RUN="$DRY_RUN"
export SELECT_ALL="$SELECT_ALL"
export MAX_OBRES="$MAX_OBRES"

# Executar anàlisi
output=$(run_analysis 2>&1)

if [ -z "$output" ]; then
    log "Cap obra validada trobada o error d'anàlisi."
    log "═══════════════════════════════════════════════════"
    exit 0
fi

# Processar output
echo "$output" | while IFS='|' read -r action rest; do
    case "$action" in
        TABLE)
            IFS='|' read -r marker obra_name score age imp_score probs <<< "$rest"
            if [ "$DRY_RUN" = true ]; then
                log "  $marker $obra_name | ${score}/10 | ${age}d | imp:${imp_score} | $probs"
            else
                log "  $obra_name | ${score}/10 | imp:${imp_score}"
            fi
            ;;
        TASK)
            IFS='|' read -r obra_name relpath instruction <<< "$rest"
            # Dedup: si ja existeix una tasca per aquesta obra (patró
            # "MILLORA CONTÍNUA de '<obra>'") en qualsevol estat de la cua,
            # no en creem una de nova. Abans el dedup només mirava pending/
            # i running/, amb la qual cosa les tasques fallides a failed/ i
            # failed_permanent/ quedaven invisibles i millora-continua les
            # recreava una i altra vegada -> bucle infinit sense progrés
            # (vegeu sade-justine i la retirada supervisora de 6 improve_*
            # el 2026-07-18). Ara també es comprova failed/ i
            # failed_permanent/. Per reintentar una obra, esborra el fitxer
            # corresponent a failed_permanent/ i la pròxima execució la
            # tornarà a encuar si encara té improvement_score > 0.
            dedup_pattern="MILLORA CONTÍNUA de '${obra_name}'"
            existing=""
            for sub in pending running failed failed_permanent; do
                if [ -z "$existing" ] && [ -d "$TASKS_DIR/$sub" ]; then
                    existing=$(grep -lF "$dedup_pattern" "$TASKS_DIR/$sub/"*.json 2>/dev/null | head -1)
                    [ -n "$existing" ] && dedup_state="$sub"
                fi
            done
            if [ -n "$existing" ]; then
                log "  ⏭️ Tasca improve per '$obra_name' ja existeix ($dedup_state/): $(basename "$existing"). No se'n crea una de nova."
            else
                log "  Creant tasca improve per: $obra_name"
                bash "$TASK_MANAGER" add improve "$instruction" 2>/dev/null
            fi
            ;;
        SUMMARY)
            IFS='|' read -r total ok prob selected <<< "$rest"
            log "Resum: $total analitzades, $ok OK, $prob amb problemes, $selected seleccionades"
            ;;
    esac
done

log "Report generat a $REPORT_FILE"
[ "$DRY_RUN" = true ] && log "Mode dry-run: no s'han creat tasques."
log "═══════════════════════════════════════════════════"
