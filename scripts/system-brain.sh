#!/bin/bash
# =============================================================================
# system-brain.sh — Cervell intel·ligent del sistema Arion
# =============================================================================
# Funcions:
#   1. check_duplicates    — Deduplicació de tasques (helper pel heartbeat)
#   2. propose_translations — Propostes intel·ligents de traducció
#   3. check_web_health    — Revisió automàtica de la web
#   4. track_evolution     — Memòria d'evolució del projecte
#   5. propose_features    — Propostes de funcionalitats del roadmap
#   6. consell_editorial   — Manté la obra-queue.json plena amb obres noves
#
# Ús:
#   source scripts/system-brain.sh          # Carregar funcions (pel heartbeat)
#   bash scripts/system-brain.sh daily      # Executar totes les funcions diàries
#   bash scripts/system-brain.sh <funció>   # Executar una funció concreta
# =============================================================================

# ── Configuració ────────────────────────────────────────────────────────────
PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
TASKS_DIR="${TASKS_DIR:-$HOME/.openclaw/workspace/tasks}"
TASK_MANAGER="${TASK_MANAGER:-$PROJECT/scripts/task-manager.sh}"
QUEUE="${QUEUE:-$PROJECT/config/obra-queue.json}"
ROADMAP="$PROJECT/config/roadmap.json"
METRICS_DIR="$PROJECT/metrics"
TASK_HISTORY="$METRICS_DIR/task-history.json"
EVOLUTION_FILE="$METRICS_DIR/evolution.json"
LOG="${LOG:-$HOME/claude-worker.log}"

mkdir -p "$METRICS_DIR"
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# ── Logger ──────────────────────────────────────────────────────────────────
brain_log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BRAIN] $1" | tee -a "$LOG"; }

# ── Control del bot OpenClaw ────────────────────────────────────────────────
# El gateway corre com a systemd user service: openclaw-gateway.service
# Parem abans de tocar fitxers a ~/.openclaw/, reiniciem després.
# Guard global per evitar doble stop/start si ja s'ha parat des d'un altre script.
OPENCLAW_SERVICE="openclaw-gateway.service"
BRAIN_STOPPED_OPENCLAW=false

_brain_stop_openclaw() {
    # No parar si ja l'hem parat nosaltres o si un altre script ja ho ha fet
    if [ "$BRAIN_STOPPED_OPENCLAW" = true ]; then
        return
    fi
    if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
        brain_log "🛑 Parant OpenClaw abans de tocar ~/.openclaw/..."
        systemctl --user stop "$OPENCLAW_SERVICE" 2>/dev/null
        local tries=0
        while systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            brain_log "   ⚠️ Servei encara actiu després de 10s. Forçant kill..."
            systemctl --user kill "$OPENCLAW_SERVICE" 2>/dev/null
            sleep 2
        fi
        BRAIN_STOPPED_OPENCLAW=true
        brain_log "   ✅ OpenClaw aturat"
    else
        brain_log "   ℹ️ OpenClaw ja estava aturat"
    fi
}

_brain_start_openclaw() {
    # Només reiniciar si l'hem parat nosaltres
    if [ "$BRAIN_STOPPED_OPENCLAW" = true ]; then
        brain_log "🚀 Reiniciant OpenClaw..."
        systemctl --user start "$OPENCLAW_SERVICE" 2>/dev/null
        local tries=0
        while ! systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            brain_log "   ✅ OpenClaw reiniciat correctament"
        else
            brain_log "   ❌ ERROR: OpenClaw no ha arrencat! Comprova amb: systemctl --user status $OPENCLAW_SERVICE"
        fi
        BRAIN_STOPPED_OPENCLAW=false
    fi
}

# ── Inicialitzar fitxers si no existeixen ───────────────────────────────────
_init_files() {
    [ ! -f "$TASK_HISTORY" ] && echo '{}' > "$TASK_HISTORY"
    [ ! -f "$EVOLUTION_FILE" ] && echo '[]' > "$EVOLUTION_FILE"
    [ ! -f "$ROADMAP" ] && echo '[]' > "$ROADMAP"
}

# =============================================================================
# 1. DEDUPLICACIÓ DE TASQUES
# =============================================================================
# Genera una clau hash única per una tasca basada en tipus + objecte.
# Retorna 0 si la tasca es pot crear, 1 si és duplicada.
#
# Ús des del heartbeat:
#   if brain_check_duplicate "translate" "seneca" "epistola-1"; then
#       add_task "translate" "..."
#   fi
# =============================================================================

# Generar clau de tasca: tipus_objecte (normalitzat)
_task_key() {
    local type="$1"
    local object="$2"
    # Normalitzar: minúscules, espais a guions, eliminar accents bàsics
    local normalized
    normalized=$(echo "${type}_${object}" | tr '[:upper:]' '[:lower:]' | \
        tr ' ' '-' | tr -d "'" | \
        sed 's/[àá]/a/g; s/[èé]/e/g; s/[ìí]/i/g; s/[òó]/o/g; s/[ùú]/u/g; s/ç/c/g' | \
        sed 's/[^a-z0-9_-]//g')
    echo "$normalized"
}

# Registrar una tasca a l'historial
_record_task() {
    local key="$1"
    local result="$2"  # created, completed, failed

    _init_files

    python3 -c "
import json, time

history_path = '$TASK_HISTORY'
try:
    with open(history_path) as f:
        history = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    history = {}

key = '$key'
result = '$result'
now = time.time()

if key not in history:
    history[key] = {'events': [], 'fail_count': 0}

entry = history[key]
entry['events'].append({'timestamp': now, 'result': result})

# Mantenir només els últims 20 events per clau
entry['events'] = entry['events'][-20:]

if result == 'failed':
    entry['fail_count'] = entry.get('fail_count', 0) + 1
    entry['last_fail'] = now
elif result == 'completed':
    entry['fail_count'] = 0
    entry['last_completed'] = now

with open(history_path, 'w') as f:
    json.dump(history, f, indent=2, ensure_ascii=False)
" 2>/dev/null
}

# Comprovar si una tasca és duplicada
# Retorna 0 = es pot crear, 1 = duplicada/bloquejada
brain_check_duplicate() {
    local type="$1"
    local object="$2"
    local key
    key=$(_task_key "$type" "$object")

    _init_files

    # a) Comprovar si existeix tasca idèntica a pending/ o running/
    if grep -rl "$object" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null | head -1 | grep -q .; then
        brain_log "   ⏭ Duplicada (pending/running): $key"
        return 1
    fi

    # b) i c) Comprovar historial: completada <48h o fallida 3+ cops (blacklist 7 dies)
    local result
    result=$(python3 -c "
import json, time

history_path = '$TASK_HISTORY'
try:
    with open(history_path) as f:
        history = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    print('ok')
    exit()

key = '$key'
now = time.time()
h48 = 48 * 3600
d7 = 7 * 86400

if key not in history:
    print('ok')
    exit()

entry = history[key]

# Completada en les últimes 48h?
last_completed = entry.get('last_completed', 0)
if now - last_completed < h48:
    print('recent_done')
    exit()

# Fallida 3+ cops amb última fallada < 7 dies?
fail_count = entry.get('fail_count', 0)
last_fail = entry.get('last_fail', 0)
if fail_count >= 3 and now - last_fail < d7:
    print('blacklisted')
    exit()

print('ok')
" 2>/dev/null)

    case "$result" in
        recent_done)
            brain_log "   ⏭ Completada recentment (<48h): $key"
            return 1
            ;;
        blacklisted)
            brain_log "   🚫 Blacklisted (3+ fallades, 7 dies): $key"
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Wrapper: add_task amb deduplicació integrada
# Ús: brain_add_task "translate" "seneca" "epistola-1" "Tradueix l'Epístola 1..."
brain_add_task() {
    local type="$1"
    local object="$2"
    local instruction="$3"

    if ! brain_check_duplicate "$type" "$object"; then
        return 1
    fi

    local key
    key=$(_task_key "$type" "$object")

    # Crear tasca via task-manager
    bash "$TASK_MANAGER" add "$type" "$instruction" 2>/dev/null
    _record_task "$key" "created"
    brain_log "   ➕ [$type] $object: $(echo "$instruction" | head -c 80)..."
    return 0
}


# =============================================================================
# 2. PROPOSTES INTEL·LIGENTS DE TRADUCCIÓ
# =============================================================================
propose_translations() {
    brain_log "📚 Proposant traduccions intel·ligents..."

    [ ! -f "$QUEUE" ] && { brain_log "   No hi ha obra-queue.json"; return; }

    # Comprovar si ja hi ha traduccions pendents/running (NO failed)
    local trad_pending=0
    local trad_running=0
    trad_pending=$(grep -rl '"type".*translate\|"type".*fetch' "$TASKS_DIR/pending/" 2>/dev/null | wc -l)
    trad_running=$(grep -rl '"type".*translate\|"type".*fetch' "$TASKS_DIR/running/" 2>/dev/null | wc -l)
    local trad_total=$((trad_pending + trad_running))
    if [ "$trad_total" -ge 3 ]; then
        brain_log "   Ja hi ha $trad_total traduccions en curs ($trad_pending pending + $trad_running running). Saltant propostes."
        return
    fi

    # Analitzar obres pendents i generar ranking
    local py_output
    py_output=$(python3 << 'PYEOF'
import json, os, sys
from pathlib import Path

project = os.environ.get('PROJECT', os.path.expanduser('~/biblioteca-universal-arion'))
queue_path = os.path.join(project, 'config', 'obra-queue.json')
history_path = os.path.join(project, 'metrics', 'task-history.json')

try:
    with open(queue_path) as f:
        queue = json.load(f)
except Exception:
    sys.exit(0)

try:
    with open(history_path) as f:
        history = json.load(f)
except Exception:
    history = {}

# Filtrar obres pendents
pendents = []
for obra in queue.get('obres', []):
    status = obra.get('status', 'pending')
    if status in ('done', 'skip', 'validated', 'in_progress'):
        continue
    pendents.append(obra)

if not pendents:
    print("CAP_PENDENT")
    sys.exit(0)

# Comprovar si tenen original disponible
obres_dir = Path(project) / 'obres'
for obra in pendents:
    autor = obra['autor']
    titol = obra['titol']
    categoria = obra.get('categoria', 'filosofia')
    # IMPORTANT: usar obra_dir del JSON (té el path real amb guions)
    obra_dir_json = obra.get('obra_dir', '')
    if obra_dir_json:
        obra_dir = Path(project) / obra_dir_json
    else:
        import unicodedata, re as _re
        def _slug(t):
            t = unicodedata.normalize('NFKD', t.lower())
            t = ''.join(c for c in t if not unicodedata.combining(c))
            return _re.sub(r'[^a-z0-9]+', '-', t).strip('-')
        obra_dir = obres_dir / categoria / _slug(autor) / _slug(titol)
        obra_dir_json = str(obra_dir.relative_to(Path(project)))
    obra['has_original'] = (obra_dir / 'original.md').exists()
    obra['has_dir'] = obra_dir.is_dir()
    obra['obra_dir_rel'] = obra_dir_json

# Puntuació per prioritzar
# Criteri: curtes primer, amb font disponible, diversificar categories
categories_vistes = set()
scored = []
for obra in pendents:
    score = 0
    paraules = obra.get('paraules_aprox', 10000)
    dificultat = obra.get('dificultat', 3)
    categoria = obra.get('categoria', 'filosofia')

    # Més curtes = més punts
    if paraules <= 5000:
        score += 30
    elif paraules <= 10000:
        score += 20
    elif paraules <= 20000:
        score += 10

    # Menys difícils = més punts
    score += (6 - dificultat) * 5

    # Amb original ja disponible = bonus
    if obra.get('has_original'):
        score += 25
    elif obra.get('has_dir'):
        score += 10

    # Fonts disponibles = bonus
    if obra.get('fonts'):
        score += len(obra['fonts']) * 3

    # Diversificació: penalitzar si la categoria ja ha sortit
    if categoria in categories_vistes:
        score -= 15
    categories_vistes.add(categoria)

    # Comprovar blacklist (fallades recents)
    key = f"translate_{autor.lower().replace(' ', '-')}_{titol.lower().replace(' ', '-')}"
    key = ''.join(c for c in key if c.isalnum() or c in '-_')
    entry = history.get(key, {})
    if entry.get('fail_count', 0) >= 3:
        score -= 50

    obra['score'] = score
    scored.append(obra)

scored.sort(key=lambda x: x['score'], reverse=True)

for i, obra in enumerate(scored[:3]):
    fonts_str = ','.join(obra.get('fonts', []))
    has_orig = 'SI' if obra.get('has_original') else 'NO'
    print(f"RANK|{i+1}|{obra['autor']}|{obra['titol']}|{obra.get('categoria','?')}|{obra.get('paraules_aprox',0)}|{obra.get('dificultat',3)}|{obra['score']}|{has_orig}|{fonts_str}|{obra.get('llengua','?')}|{obra.get('obra_dir_rel','')}")
PYEOF
)

    if [ "$py_output" = "CAP_PENDENT" ]; then
        brain_log "   Totes les obres estan en curs o completades!"
        return
    fi

    brain_log "   📊 Ranking de propostes:"
    local first_autor="" first_titol="" first_llengua="" first_categoria=""

    echo "$py_output" | while IFS='|' read -r _ rank autor titol categoria paraules dificultat score has_orig fonts llengua obra_dir_rank; do
        brain_log "   #$rank: $titol ($autor) — cat:$categoria, ${paraules}p, dif:$dificultat, score:$score, orig:$has_orig"
        # Guardar la primera per crear tasca
        if [ "$rank" = "1" ]; then
            echo "$autor|$titol|$llengua|$categoria|$obra_dir_rank" > /tmp/brain_top_pick.tmp
        fi
    done

    # Crear tasca per la primera del ranking
    if [ -f /tmp/brain_top_pick.tmp ]; then
        IFS='|' read -r autor titol llengua categoria obra_path < /tmp/brain_top_pick.tmp
        rm -f /tmp/brain_top_pick.tmp

        if [ -f "$PROJECT/$obra_path/original.md" ]; then
            # Ja té original → traduir directament
            brain_add_task "translate" "${slug_autor}_${slug_titol}" \
                "cd ~/biblioteca-universal-arion && python3 scripts/traduir_pipeline.py $obra_path/"
        else
            # No té original → primer obtenir el text
            brain_add_task "fetch" "${slug_autor}_${slug_titol}" \
                "cd ~/biblioteca-universal-arion && mkdir -p $obra_path && python3 scripts/cercador_fonts_v2.py \"$autor\" \"$titol\" \"$llengua\" \"$obra_path\" && if [ ! -s $obra_path/original.md ]; then echo 'ERROR: No s.ha pogut obtenir original.md' && exit 1; fi && git add -A && git commit -m \"font: $titol de $autor\" && git push"
        fi
    fi
}


# =============================================================================
# 3. REVISIÓ WEB AUTOMÀTICA
# =============================================================================
check_web_health() {
    brain_log "🌐 Revisió salut web..."

    local issues=0

    # 3a. Verificar que docs/index.html existeix
    if [ ! -f "$PROJECT/docs/index.html" ]; then
        brain_log "   ❌ docs/index.html NO existeix!"
        issues=$((issues + 1))
    else
        # Comprovar antiguitat
        local docs_age
        docs_age=$(( ($(date +%s) - $(stat -c %Y "$PROJECT/docs/index.html" 2>/dev/null || echo 0)) / 3600 ))
        if [ "$docs_age" -gt 24 ]; then
            brain_log "   ⚠️ docs/index.html té ${docs_age}h d'antiguitat"
            issues=$((issues + 1))
        else
            brain_log "   ✅ docs/index.html actualitzat (${docs_age}h)"
        fi
    fi

    # 3b. Comprovar que cada obra validada apareix a la web
    local validated_not_web=0
    while IFS= read -r validated_file; do
        local obra_dir
        obra_dir=$(dirname "$validated_file")
        local obra_name
        obra_name=$(basename "$obra_dir")

        # Buscar si apareix a docs/
        if [ -d "$PROJECT/docs" ] && ! grep -rq "$obra_name" "$PROJECT/docs/" 2>/dev/null; then
            brain_log "   ⚠️ Obra validada '$obra_name' NO apareix a la web"
            validated_not_web=$((validated_not_web + 1))
        fi
    done < <(find "$PROJECT/obres" -name ".validated" 2>/dev/null)

    if [ "$validated_not_web" -gt 0 ]; then
        brain_log "   ⚠️ $validated_not_web obres validades no estan a la web"
        issues=$((issues + 1))
    fi

    # 3c. Detectar links trencats (obres referenciades a docs/ que ja no existeixen)
    if [ -d "$PROJECT/docs" ]; then
        local broken_links=0
        for html_file in "$PROJECT/docs"/*.html; do
            [ -f "$html_file" ] || continue
            # Buscar referències a obres/ dins els HTML
            grep -oP 'href="[^"]*obres/[^"]*"' "$html_file" 2>/dev/null | \
                grep -oP 'obres/[^"]*' | while read -r ref; do
                if [ ! -e "$PROJECT/$ref" ] && [ ! -e "$PROJECT/docs/$ref" ]; then
                    brain_log "   🔗 Link trencat a $(basename "$html_file"): $ref"
                    broken_links=$((broken_links + 1))
                fi
            done
        done
    fi

    # 3d. Verificar README.md reflecteix catàleg
    if [ -f "$PROJECT/README.md" ]; then
        local total_validated
        total_validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
        local readme_mentions
        readme_mentions=$(grep -c "validada\|validated\|✅" "$PROJECT/README.md" 2>/dev/null || echo 0)
        # Si hi ha molt de desfasament, avisar
        if [ "$total_validated" -gt 0 ] && [ "$readme_mentions" -eq 0 ]; then
            brain_log "   ⚠️ README.md no menciona cap obra validada (n'hi ha $total_validated)"
            issues=$((issues + 1))
        fi
    fi

    # 3e. Si hi ha problemes i no hi ha tasca pendent → crear-ne una
    if [ "$issues" -gt 0 ]; then
        # Comprovar obres noves validadas
        local recent_validated
        recent_validated=$(find "$PROJECT/obres" -name ".validated" -mtime -1 2>/dev/null | wc -l)

        if [ "$recent_validated" -gt 0 ] || [ ! -f "$PROJECT/docs/index.html" ]; then
            brain_add_task "publish" "web-health" \
                "Web desactualitzada ($issues problemes). Executa 'python3 scripts/build.py' per regenerar docs/. Verifica que totes les obres amb .validated apareixen. Commit i push."
        fi
    else
        brain_log "   ✅ Web saludable"
    fi
}


# =============================================================================
# 4. MEMÒRIA D'EVOLUCIÓ
# =============================================================================
track_evolution() {
    brain_log "📈 Registrant evolució..."

    _init_files

    local py_output
    py_output=$(python3 << 'PYEOF'
import json, os, time, subprocess
from datetime import datetime
from pathlib import Path

project = os.environ.get('PROJECT', os.path.expanduser('~/biblioteca-universal-arion'))
evolution_path = os.path.join(project, 'metrics', 'evolution.json')
tasks_dir = os.path.expanduser('~/.openclaw/workspace/tasks')

# Carregar evolució
try:
    with open(evolution_path) as f:
        evolution = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    evolution = []

today = datetime.now().strftime('%Y-%m-%d')

# No duplicar entrades del mateix dia
if evolution and evolution[-1].get('date') == today:
    print(f"SKIP|Ja registrat avui ({today})")
    exit()

# Recollir mètriques
obres_dir = Path(project) / 'obres'
obres_total = obres_validades = obres_needs_fix = traduccions = 0

if obres_dir.exists():
    for cat in obres_dir.iterdir():
        if not cat.is_dir(): continue
        for aut in cat.iterdir():
            if not aut.is_dir(): continue
            for obra in aut.iterdir():
                if not obra.is_dir(): continue
                obres_total += 1
                files = [f.name for f in obra.iterdir()]
                if '.validated' in files: obres_validades += 1
                if '.needs_fix' in files: obres_needs_fix += 1
                if any('traduccio' in f.lower() for f in files): traduccions += 1

# Errors últimes 24h
errors_24h = 0
failed_dir = Path(tasks_dir) / 'failed'
if failed_dir.exists():
    cutoff = time.time() - 86400
    for f in failed_dir.glob('*.json'):
        if f.stat().st_mtime > cutoff: errors_24h += 1

# Tasques completades avui
done_today = 0
done_dir = Path(tasks_dir) / 'done'
if done_dir.exists():
    today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    for f in done_dir.glob('*.json'):
        if f.stat().st_mtime > today_start: done_today += 1

# Scripts millorats (fitxers .py/.sh modificats últimes 24h)
scripts_millorats = 0
for ext in ['*.py', '*.sh']:
    for f in Path(project).rglob(ext):
        try:
            if f.stat().st_mtime > time.time() - 86400: scripts_millorats += 1
        except: pass

# Comprovar worker actiu
try:
    result = subprocess.run(['tmux', 'has-session', '-t', 'worker'],
                          capture_output=True, timeout=5)
    uptime_worker = result.returncode == 0
except Exception:
    uptime_worker = False

# Crear entrada
entry = {
    'date': today,
    'obres_total': obres_total,
    'obres_validades': obres_validades,
    'obres_needs_fix': obres_needs_fix,
    'traduccions': traduccions,
    'done_today': done_today,
    'errors_24h': errors_24h,
    'scripts_millorats': scripts_millorats,
    'uptime_worker': uptime_worker,
}

# Comparar amb ahir
if evolution:
    prev = evolution[-1]
    delta_obres = entry['obres_total'] - prev.get('obres_total', 0)
    delta_valid = entry['obres_validades'] - prev.get('obres_validades', 0)
    delta_errors = entry['errors_24h'] - prev.get('errors_24h', 0)
    entry['delta'] = {'obres': delta_obres, 'validades': delta_valid, 'errors': delta_errors}
    improving = delta_valid > 0 or (delta_obres > 0 and delta_errors <= 0)
    worsening = delta_errors > 0 and delta_valid <= 0 and delta_obres <= 0
    entry['tendencia'] = 'millora' if improving else ('empitjora' if worsening else 'estable')
else:
    entry['delta'] = {'obres': 0, 'validades': 0, 'errors': 0}
    entry['tendencia'] = 'primera_entrada'

evolution.append(entry)
evolution = evolution[-90:]

with open(evolution_path, 'w') as f:
    json.dump(evolution, f, indent=2, ensure_ascii=False)

print(f"OK|obres:{obres_total} valid:{obres_validades} err:{errors_24h} tend:{entry['tendencia']}")

# Comprovar 3 dies consecutius empitjorant
if len(evolution) >= 3:
    last3 = evolution[-3:]
    if all(e.get('tendencia') == 'empitjora' for e in last3):
        print("ALERT|3 dies consecutius empitjorant!")

# Report setmanal (dilluns)
day_of_week = datetime.now().weekday()  # 0=dilluns
if day_of_week == 0 and len(evolution) >= 7:
    week = evolution[-7:]
    total_done = sum(e.get('done_today', 0) for e in week)
    total_errors = sum(e.get('errors_24h', 0) for e in week)
    obres_start = week[0].get('obres_total', 0)
    obres_end = week[-1].get('obres_total', 0)
    valid_start = week[0].get('obres_validades', 0)
    valid_end = week[-1].get('obres_validades', 0)
    print(f"WEEKLY|tasques:{total_done} errors:{total_errors} obres:{obres_start}->{obres_end} valid:{valid_start}->{valid_end}")
PYEOF
)

    echo "$py_output" | while IFS='|' read -r action msg; do
        case "$action" in
            SKIP)
                brain_log "   $msg"
                ;;
            OK)
                brain_log "   📊 $msg"
                ;;
            ALERT)
                brain_log "   🚨 $msg"
                brain_add_task "maintenance" "analisi-profunda" \
                    "ANÀLISI PROFUNDA: El sistema porta 3 dies empitjorant. Revisa: 1) Errors recents a ~/.openclaw/workspace/tasks/failed/. 2) Qualitat de les últimes traduccions. 3) Logs del worker. 4) Genera un informe amb causes i solucions proposades a metrics/analisi-profunda.md."
                ;;
            WEEKLY)
                brain_log "   📅 Report setmanal: $msg"
                ;;
        esac
    done
}


# =============================================================================
# 5. PROPOSTES DE FUNCIONALITATS
# =============================================================================
propose_features() {
    brain_log "💡 Proposant funcionalitats del roadmap..."

    [ ! -f "$ROADMAP" ] && { brain_log "   No hi ha roadmap.json"; return; }

    # Només proposar un cop per setmana (dilluns o si no hi ha cap in_progress)
    local day_of_week
    day_of_week=$(date +%u)  # 1=dilluns
    local in_progress
    in_progress=$(python3 -c "
import json
try:
    with open('$ROADMAP') as f:
        items = json.load(f)
    print(sum(1 for i in items if i.get('status') == 'in_progress'))
except:
    print(0)
" 2>/dev/null)

    if [ "$day_of_week" != "1" ] && [ "${in_progress:-0}" -gt 0 ]; then
        brain_log "   Ja hi ha funcionalitats in_progress. Saltant."
        return
    fi

    # Buscar la pròxima funcionalitat a proposar
    local feature_info
    feature_info=$(ROADMAP_PATH="$ROADMAP" python3 -c "
import json, os
roadmap_path = os.environ['ROADMAP_PATH']
try:
    with open(roadmap_path) as f:
        items = json.load(f)
except Exception:
    exit()
candidates = [i for i in items if i.get('status', 'pending') not in ('done', 'in_progress', 'skip')]
if not candidates:
    print('CAP')
    exit()
candidates.sort(key=lambda x: x.get('priority', 99))
best = candidates[0]
print(f\"{best['id']}|{best['desc']}|{best.get('priority', 99)}\")
" 2>/dev/null)

    if [ -z "$feature_info" ] || [ "$feature_info" = "CAP" ]; then
        brain_log "   Totes les funcionalitats estan completades o en curs!"
        return
    fi

    local feature_id feature_desc feature_priority
    IFS='|' read -r feature_id feature_desc feature_priority <<< "$feature_info"

    brain_log "   💡 Proposta: [$feature_id] $feature_desc (prioritat $feature_priority)"

    # Crear tasca
    if brain_add_task "implement-feature" "$feature_id" \
        "IMPLEMENTAR FUNCIONALITAT '$feature_id': $feature_desc. Detalls: 1) Llegeix config/roadmap.json per context. 2) Implementa la funcionalitat seguint les convencions del projecte. 3) Afegeix tests si escau. 4) Actualitza roadmap.json: marca status='done'. 5) Commit+push."; then

        # Marcar com in_progress al roadmap
        ROADMAP_PATH="$ROADMAP" FEATURE_ID="$feature_id" TODAY="$(date +%Y-%m-%d)" python3 -c "
import json, os
roadmap_path = os.environ['ROADMAP_PATH']
feature_id = os.environ['FEATURE_ID']
today = os.environ['TODAY']
with open(roadmap_path) as f:
    items = json.load(f)
for item in items:
    if item['id'] == feature_id:
        item['status'] = 'in_progress'
        item['started_at'] = today
        break
with open(roadmap_path, 'w') as f:
    json.dump(items, f, indent=2, ensure_ascii=False)
" 2>/dev/null
        brain_log "   ✅ Funcionalitat '$feature_id' marcada com in_progress"
    fi
}


# =============================================================================
# CONSELL EDITORIAL — Manté la obra-queue.json plena
# =============================================================================
run_consell_editorial() {
    brain_log "📚 Consell Editorial — Comprovant cua d'obres..."

    local pending
    pending=$(python3 -c "
import json
with open('$QUEUE') as f:
    data = json.load(f)
pending = [o for o in data.get('obres', []) if o.get('status') == 'pending']
print(len(pending))
" 2>/dev/null || echo "0")

    local MAX_PENDING=10
    if [ "$pending" -ge "$MAX_PENDING" ] 2>/dev/null; then
        brain_log "   Cua amb $pending obres pending (>= $MAX_PENDING). No cal afegir-ne."
        return
    fi

    brain_log "   Cua amb $pending obres pending (< $MAX_PENDING). Llançant consell editorial..."

    local output
    output=$(bash "$PROJECT/scripts/consell-editorial.sh" 2>&1) || {
        brain_log "   ❌ Error executant consell-editorial.sh"
        return
    }

    # Extreure quantes s'han afegit del resum
    local afegides
    afegides=$(echo "$output" | grep -oP '\d+ afegides' | grep -oP '\d+' || echo "0")
    brain_log "   ✅ Consell editorial completat: $afegides obres noves afegides"

    # Log complet
    echo "$output" | while IFS= read -r line; do
        brain_log "   $line"
    done
}


# =============================================================================
# EXECUCIÓ DIÀRIA (totes les funcions no-helper)
# =============================================================================
run_daily() {
    brain_log "═══════════════════════════════════════════════════"
    brain_log "🧠 SYSTEM BRAIN — Execució diària"

    # Comprovar si han passat 2+ hores des de l'última execució
    local LAST_RUN_FILE="$TASKS_DIR/.brain-last-run"
    local INTERVAL=7200  # 2 hores en segons
    if [ -f "$LAST_RUN_FILE" ]; then
        local last_run_ts now_ts elapsed elapsed_min
        last_run_ts=$(cat "$LAST_RUN_FILE" 2>/dev/null)
        now_ts=$(date +%s)
        elapsed=$(( now_ts - last_run_ts ))
        if [ "$elapsed" -lt "$INTERVAL" ] 2>/dev/null; then
            elapsed_min=$(( elapsed / 60 ))
            brain_log "   Executat fa ${elapsed_min}min. Saltant."
            brain_log "═══════════════════════════════════════════════════"
            return
        fi
    fi

    _init_files

    # Totes les funcions diàries poden crear tasques a ~/.openclaw/workspace/tasks/
    # Parem el bot, executem, i reiniciem.
    _brain_stop_openclaw
    trap '_brain_start_openclaw' EXIT

    propose_translations
    check_web_health
    track_evolution
    propose_features
    run_consell_editorial

    date +%s > "$LAST_RUN_FILE"

    _brain_start_openclaw
    trap - EXIT

    brain_log "🧠 SYSTEM BRAIN — Execució diària completada"
    brain_log "═══════════════════════════════════════════════════"
}


# =============================================================================
# MAIN — Permet execució directa o sourced
# =============================================================================
# Si s'executa directament (no sourced), processar arguments
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    # Funcions que escriuen a ~/.openclaw/ → necessiten stop/start
    _with_openclaw_guard() {
        _brain_stop_openclaw
        trap '_brain_start_openclaw' EXIT
        "$@"
        _brain_start_openclaw
        trap - EXIT
    }

    case "${1:-daily}" in
        daily)
            run_daily
            ;;
        propose-translations|propose_translations)
            _init_files
            _with_openclaw_guard propose_translations
            ;;
        check-web|check_web_health)
            _init_files
            _with_openclaw_guard check_web_health
            ;;
        track-evolution|track_evolution)
            _init_files
            _with_openclaw_guard track_evolution
            ;;
        propose-features|propose_features)
            _init_files
            _with_openclaw_guard propose_features
            ;;
        consell-editorial|run_consell_editorial)
            _init_files
            _with_openclaw_guard run_consell_editorial
            ;;
        check-duplicate)
            # Només lectura, no cal stop/start
            _init_files
            if brain_check_duplicate "$2" "$3"; then
                echo "OK: Es pot crear"
            else
                echo "SKIP: Duplicada o bloquejada"
            fi
            ;;
        record-task)
            # Escriu a metrics/, no a ~/.openclaw/
            _init_files
            _record_task "$2" "$3"
            ;;
        *)
            echo "Ús: system-brain.sh [daily|propose-translations|check-web|track-evolution|propose-features|consell-editorial|check-duplicate]"
            exit 1
            ;;
    esac
fi
