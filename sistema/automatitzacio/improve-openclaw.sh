#!/bin/bash
exit 0  # 🛑 CONSOLIDACIÓ: pausat per estalviar DIEM
# =============================================================================
# improve-openclaw.sh — Analitzador i millorador del sistema OpenClaw
# =============================================================================
# Analitza logs, skills, scripts i tasques fallides per detectar problemes
# i generar tasques de millora o propostes de canvi.
#
# Ús: bash sistema/automatitzacio/improve-openclaw.sh
#
# Política de canvis:
#   - Scripts tècnics (claude.sh, heartbeat.sh, etc.) → pot modificar amb BACKUP
#   - Fitxers de personalitat (SOUL.md, HEARTBEAT.md) → MAI modificar, crear proposta
#   - SKILL.md → pot modificar amb backup
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT="$HOME/biblioteca-universal-arion"
OPENCLAW_DIR="$HOME/.openclaw"
WORKSPACE="$OPENCLAW_DIR/workspace"
TASKS_DIR="$WORKSPACE/tasks"
TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
PROPOSALS_DIR="$WORKSPACE/proposals"
METRICS_FILE="$PROJECT/metrics/openclaw-health.json"
LOG="$HOME/claude-worker.log"
OPENCLAW_LOG="$HOME/openclaw.log"
MAX_IMPROVE_PENDING=2

# Fitxers a analitzar
SKILL_MD="$WORKSPACE/skills/claude-code/SKILL.md"
CLAUDE_SH="$WORKSPACE/skills/claude-code/scripts/claude.sh"
HEARTBEAT_REPORT="$WORKSPACE/last_heartbeat_report.md"

# ── Control del bot OpenClaw ─────────────────────────────────────────────────
# El gateway corre com a systemd user service: openclaw-gateway.service
# Parem abans de tocar fitxers a ~/.openclaw/, reiniciem després.
OPENCLAW_SERVICE="openclaw-gateway.service"
OPENCLAW_STOPPED=false

stop_openclaw() {
    # Comprovar si el servei està actiu
    if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
        log "🛑 Parant OpenClaw ($OPENCLAW_SERVICE)..."
        systemctl --user stop "$OPENCLAW_SERVICE" 2>/dev/null
        # Esperar fins que el procés acabi (màx 10s)
        local tries=0
        while systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            log "   ⚠️ Servei encara actiu després de 10s. Forçant kill..."
            systemctl --user kill "$OPENCLAW_SERVICE" 2>/dev/null
            sleep 2
        fi
        OPENCLAW_STOPPED=true
        log "   ✅ OpenClaw aturat"
    else
        log "   ℹ️ OpenClaw ja estava aturat"
        OPENCLAW_STOPPED=false
    fi
}

start_openclaw() {
    # Només reiniciar si l'hem parat nosaltres
    if [ "$OPENCLAW_STOPPED" = true ]; then
        log "🚀 Reiniciant OpenClaw ($OPENCLAW_SERVICE)..."
        systemctl --user start "$OPENCLAW_SERVICE" 2>/dev/null
        # Esperar que arrenqui (màx 10s)
        local tries=0
        while ! systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            log "   ✅ OpenClaw reiniciat correctament"
        else
            log "   ❌ ERROR: OpenClaw no ha arrencat! Comprova amb: systemctl --user status $OPENCLAW_SERVICE"
        fi
        OPENCLAW_STOPPED=false
    else
        log "   ℹ️ No cal reiniciar (no l'hem parat nosaltres)"
    fi
}

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [IMPROVE-OC] $1" | tee -a "$LOG"; }

count_improve_pending() {
    grep -rl "improve-openclaw" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null | wc -l
}

add_improve_task() {
    local instruction="$1"
    if [ "$(count_improve_pending)" -ge "$MAX_IMPROVE_PENDING" ]; then
        log "   Ja hi ha $MAX_IMPROVE_PENDING tasques improve-openclaw pendents. Saltant."
        return 1
    fi
    bash "$TASK_MANAGER" add "improve-openclaw" "$instruction" 2>/dev/null
    log "   + Tasca creada: $(echo "$instruction" | head -c 80)..."
    return 0
}

make_backup() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.bak.$(date +%Y%m%d)"
        if [ ! -f "$backup" ]; then
            cp "$file" "$backup"
            log "   Backup: $backup"
        fi
    fi
}

create_proposal() {
    local fitxer_objectiu="$1"
    local motiu="$2"
    local contingut="$3"
    mkdir -p "$PROPOSALS_DIR"
    local ts=$(date +%Y%m%d-%H%M%S)
    local proposal_file="$PROPOSALS_DIR/proposta-${ts}.md"
    cat > "$proposal_file" << EOF
# Proposta de canvi — $ts

**Fitxer objectiu:** $fitxer_objectiu
**Motiu:** $motiu
**Estat:** pendent

## Canvi proposat

$contingut

---
Generat automàticament per improve-openclaw.sh
EOF
    log "   Proposta creada: $proposal_file"
}

# =============================================================================
# 1. ANALITZAR LOGS D'OPENCLAW
# =============================================================================
analyze_openclaw_log() {
    log "Analitzant openclaw.log..."

    [ ! -f "$OPENCLAW_LOG" ] && { log "   openclaw.log no trobat"; return; }

    local errors_24h=0
    local timeouts=0
    local delegations_failed=0
    local recurring_errors=""

    # Comptar errors de les últimes 24h (buscar patrons d'error)
    errors_24h=$(tail -500 "$OPENCLAW_LOG" 2>/dev/null | grep -ciE "error|exception|failed|crash" || echo 0)

    # Timeouts
    timeouts=$(tail -500 "$OPENCLAW_LOG" 2>/dev/null | grep -ci "timeout" || echo 0)

    # Delegacions fallides
    delegations_failed=$(tail -500 "$OPENCLAW_LOG" 2>/dev/null | grep -ciE "delegat.*fail|skill.*error|command.*fail" || echo 0)

    # Errors recurrents (mateixa línia repetida 3+ cops)
    recurring_errors=$(tail -200 "$OPENCLAW_LOG" 2>/dev/null | \
        grep -iE "error|fail|exception" | \
        sed 's/\[.*\]//g' | sort | uniq -c | sort -rn | \
        awk '$1 >= 3 {print}' | head -5)

    log "   Errors 24h: $errors_24h | Timeouts: $timeouts | Delegacions fallides: $delegations_failed"

    # Exportar per mètriques
    METRIC_ERRORS_24H=$errors_24h
    METRIC_TIMEOUTS=$timeouts

    # Si hi ha errors recurrents, generar tasca
    if [ -n "$recurring_errors" ]; then
        local error_summary
        error_summary=$(echo "$recurring_errors" | head -3 | tr '\n' '; ')
        add_improve_task "Errors recurrents detectats a openclaw.log. Patrons: $error_summary. Investiga la causa i proposa solucions. Revisa els logs amb: tail -200 ~/openclaw.log | grep -i error"
    fi
}

# =============================================================================
# 2. ANALITZAR SKILL.MD
# =============================================================================
analyze_skill_md() {
    log "Analitzant SKILL.md..."

    [ ! -f "$SKILL_MD" ] && { log "   SKILL.md no trobat"; return; }

    local issues=""

    # Comprovar referència a worker incorrecte (claude-worker.sh en lloc de mini)
    if grep -q "claude-worker\.sh" "$SKILL_MD" 2>/dev/null; then
        issues="${issues}Referència a claude-worker.sh (hauria de ser claude-worker-mini.sh). "
    fi

    # Comprovar si falta unset CLAUDECODE
    if ! grep -qi "CLAUDECODE\|nested" "$SKILL_MD" 2>/dev/null; then
        issues="${issues}No menciona CLAUDECODE/nested sessions. "
    fi

    # Comprovar si pkill referencia worker incorrecte
    if grep -q 'pkill -f "claude-worker.sh"' "$SKILL_MD" 2>/dev/null; then
        issues="${issues}pkill referencia worker antic. "
    fi

    # Comprovar si falta tipus improve-openclaw a les accions
    if ! grep -qi "improve-openclaw\|millorar openclaw" "$SKILL_MD" 2>/dev/null; then
        issues="${issues}Falta acció improve-openclaw a les accions disponibles. "
    fi

    if [ -n "$issues" ]; then
        log "   Problemes trobats: $issues"
        make_backup "$SKILL_MD"
        add_improve_task "Actualitza SKILL.md del skill claude-code. Problemes: $issues. Fitxer: $SKILL_MD. Fes backup abans de modificar (cp SKILL.md SKILL.md.bak.\$(date +%Y%m%d)). Canvis necessaris: 1) Substitueix 'claude-worker.sh' per 'claude-worker-mini.sh'. 2) Afegeix nota sobre unset CLAUDECODE per evitar nested sessions. 3) Afegeix acció improve-openclaw."
    else
        log "   SKILL.md OK"
    fi
}

# =============================================================================
# 3. ANALITZAR CLAUDE.SH
# =============================================================================
analyze_claude_sh() {
    log "Analitzant claude.sh..."

    [ ! -f "$CLAUDE_SH" ] && { log "   claude.sh no trobat"; return; }

    local issues=""

    # Comprovar si no fa unset CLAUDECODE
    if ! grep -q "CLAUDECODE" "$CLAUDE_SH" 2>/dev/null; then
        issues="${issues}No fa unset CLAUDECODE (risc nested sessions). "
    fi

    # Comprovar si té Write a allowedTools (mode write)
    if ! grep -q '"Write"' "$CLAUDE_SH" 2>/dev/null; then
        issues="${issues}Falta 'Write' a allowedTools del mode write. "
    fi

    # Comprovar si manca Read a allowedTools
    if ! grep -q '"Read"' "$CLAUDE_SH" 2>/dev/null; then
        issues="${issues}Falta 'Read' a allowedTools. "
    fi

    # Comprovar timeout (300s pot ser curt per traduccions)
    local timeout_val
    timeout_val=$(grep -oP 'timeout \K\d+' "$CLAUDE_SH" 2>/dev/null | head -1)
    if [ "${timeout_val:-0}" -lt 600 ]; then
        issues="${issues}Timeout de ${timeout_val:-?}s pot ser curt per traduccions llargues. "
    fi

    # Comprovar si no té --max-turns
    if ! grep -q "max-turns" "$CLAUDE_SH" 2>/dev/null; then
        issues="${issues}No defineix --max-turns (pot fer loops infinits). "
    fi

    # Comprovar git add/commit/push als allowedTools
    if ! grep -q "git add" "$CLAUDE_SH" 2>/dev/null; then
        issues="${issues}Falta git add/commit/push als allowedTools del mode write. "
    fi

    if [ -n "$issues" ]; then
        log "   Problemes trobats: $issues"
        make_backup "$CLAUDE_SH"
        add_improve_task "Millora claude.sh del skill claude-code. Problemes: $issues. Fitxer: $CLAUDE_SH. Canvis necessaris: 1) Afegir 'unset CLAUDECODE' abans de cridar claude. 2) Afegir Write, Read als allowedTools. 3) Afegir --max-turns 25. 4) Considerar augmentar timeout a 600s. 5) Afegir git add/commit/push als tools del mode write."
    else
        log "   claude.sh OK"
    fi
}

# =============================================================================
# 4. ANALITZAR TASQUES FALLIDES
# =============================================================================
analyze_failed_tasks() {
    log "Analitzant tasques fallides..."

    local failed_dir="$TASKS_DIR/failed"
    [ ! -d "$failed_dir" ] && { log "   Directori failed/ no trobat"; return; }

    local failed_count
    failed_count=$(ls -1 "$failed_dir/"*.json 2>/dev/null | wc -l)
    METRIC_FAILED_24H=${failed_count:-0}

    if [ "${failed_count:-0}" -eq 0 ]; then
        log "   Cap tasca fallida"
        return
    fi

    log "   $failed_count tasques fallides"

    # Trobar patrons: agrupar per tipus
    local pattern_summary
    pattern_summary=$(python3 -c "
import json, os, sys
from collections import Counter
from pathlib import Path

failed_dir = Path('$failed_dir')
types = Counter()
errors = []

for f in failed_dir.glob('*.json'):
    try:
        data = json.loads(f.read_text())
        task_type = data.get('type', 'unknown')
        types[task_type] += 1
        err = data.get('error', '')
        if err:
            errors.append(f'{task_type}: {str(err)[:60]}')
    except:
        pass

# Tipus amb >= 3 fallades
problematic = {t: c for t, c in types.items() if c >= 3}
if problematic:
    for t, c in sorted(problematic.items(), key=lambda x: -x[1]):
        print(f'PATTERN|{t}|{c}')

# Errors comuns
if errors:
    for e in errors[:3]:
        print(f'ERROR|{e}')
" 2>/dev/null)

    if [ -n "$pattern_summary" ]; then
        echo "$pattern_summary" | while IFS='|' read -r tag info count_or_detail; do
            case "$tag" in
                PATTERN)
                    if [ "$(count_improve_pending)" -lt "$MAX_IMPROVE_PENDING" ]; then
                        add_improve_task "Patró de fallada detectat: $count_or_detail tasques de tipus '$info' fallen repetidament. Investiga les causes a $failed_dir. Comprova: 1) Si les instruccions són prou clares. 2) Si les dependències estan disponibles. 3) Si hi ha problemes de timeout o rate limit. Proposa correccions al heartbeat.sh o al pipeline."
                    fi
                    ;;
                ERROR)
                    log "   Error recent: $info $count_or_detail"
                    ;;
            esac
        done
    fi
}

# =============================================================================
# 5. ANALITZAR HEARTBEAT REPORT
# =============================================================================
analyze_heartbeat_report() {
    log "Analitzant heartbeat report..."

    [ ! -f "$HEARTBEAT_REPORT" ] && { log "   Heartbeat report no trobat"; return; }

    local report
    report=$(cat "$HEARTBEAT_REPORT" 2>/dev/null)

    # Extreure mètriques del report
    local validated
    validated=$(echo "$report" | grep -oP '\d+(?= validades)' | head -1)
    local needs_fix
    needs_fix=$(echo "$report" | grep -oP '\d+(?= pendents fix)' | head -1)
    local failed_report
    failed_report=$(echo "$report" | grep -oP '\d+(?= fallides)' | head -1)
    local done_today
    done_today=$(echo "$report" | grep -oP '\d+(?= tasques avui)' | head -1)

    METRIC_DONE_24H=${done_today:-0}

    log "   Validades: ${validated:-?} | Needs fix: ${needs_fix:-?} | Fallides: ${failed_report:-?} | Avui: ${done_today:-?}"

    # Detectar problemes
    if [ "${failed_report:-0}" -gt 20 ] && [ "${done_today:-0}" -lt 5 ]; then
        log "   Proporció fallades/completades dolenta"
        if [ "$(count_improve_pending)" -lt "$MAX_IMPROVE_PENDING" ]; then
            add_improve_task "Rendiment baix del worker: ${failed_report} fallides vs ${done_today} completades avui. Investiga: 1) tail -50 ~/claude-worker.log per veure errors recents. 2) ls ~/.openclaw/workspace/tasks/failed/ per patrons. 3) Comprova rate limits. 4) Verifica que el worker-mini funciona correctament."
        fi
    fi

    # Worker inactiu
    if echo "$report" | grep -qi "INACTIU"; then
        log "   Worker inactiu detectat al report"
        if [ "$(count_improve_pending)" -lt "$MAX_IMPROVE_PENDING" ]; then
            add_improve_task "Worker INACTIU segons l'últim heartbeat report. Comprova: 1) pgrep -f claude-worker-mini. 2) cat ~/.openclaw/workspace/tasks/worker.lock. 3) Reinicia si cal amb: tmux new-session -d -s worker 'cd ~/biblioteca-universal-arion && bash sistema/automatitzacio/claude-worker-mini.sh'"
        fi
    fi
}

# =============================================================================
# 6. ANALITZAR SOUL.MD / HEARTBEAT.MD (NOMÉS PROPOSTES)
# =============================================================================
analyze_personality_files() {
    log "Analitzant fitxers de personalitat..."

    # SOUL.md — buscar inconsistències
    local soul="$WORKSPACE/SOUL.md"
    if [ -f "$soul" ]; then
        # Comprovar si referència worker antic
        if grep -q "claude-worker\.sh" "$soul" 2>/dev/null && ! grep -q "claude-worker-mini" "$soul" 2>/dev/null; then
            create_proposal "$soul" \
                "SOUL.md referència el worker antic (claude-worker.sh) que no funciona" \
                "Substituir referències a \`claude-worker.sh\` per \`claude-worker-mini.sh\` a les instruccions del worker."
        fi
    fi

    # HEARTBEAT.md — buscar instruccions obsoletes
    local heartbeat_md="$WORKSPACE/HEARTBEAT.md"
    if [ -f "$heartbeat_md" ]; then
        if grep -q "claude-worker\.sh" "$heartbeat_md" 2>/dev/null && ! grep -q "claude-worker-mini" "$heartbeat_md" 2>/dev/null; then
            create_proposal "$heartbeat_md" \
                "HEARTBEAT.md referència worker antic" \
                "Actualitzar referència de worker a \`claude-worker-mini.sh\`."
        fi
    fi
}

# =============================================================================
# 7. RECOLLIR I GUARDAR MÈTRIQUES
# =============================================================================
collect_metrics() {
    log "Recollint mètriques..."

    mkdir -p "$(dirname "$METRICS_FILE")"

    # Variables de mètriques (algunes ja omplides per les funcions anteriors)
    local done_24h=${METRIC_DONE_24H:-0}
    local failed_24h=${METRIC_FAILED_24H:-0}
    local errors_24h=${METRIC_ERRORS_24H:-0}

    # Temps mitjà de delegació (extreure del log si es pot)
    local avg_delegation="null"
    local delegation_times
    delegation_times=$(tail -500 "$LOG" 2>/dev/null | \
        grep -oP 'completat \(\K\d+' | \
        head -20)
    if [ -n "$delegation_times" ]; then
        avg_delegation=$(echo "$delegation_times" | awk '{s+=$1; n++} END {if(n>0) printf "%.0f", s/n; else print "null"}')
    fi

    # Últim heartbeat OK
    local last_heartbeat_ts="null"
    if [ -f "$HEARTBEAT_REPORT" ]; then
        last_heartbeat_ts=$(stat -c %Y "$HEARTBEAT_REPORT" 2>/dev/null || echo "null")
    fi

    # Propostes pendents
    local proposals_count=0
    if [ -d "$PROPOSALS_DIR" ]; then
        proposals_count=$(find "$PROPOSALS_DIR" -name "proposta-*.md" -type f 2>/dev/null | wc -l)
    fi

    # Guardar mètriques
    python3 -c "
import json
from datetime import datetime

metrics = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'tasques_completades_24h': $done_24h,
    'tasques_fallides_24h': $failed_24h,
    'errors_log_24h': $errors_24h,
    'temps_mitja_delegacio_s': $avg_delegation,
    'ultim_heartbeat_ok': $last_heartbeat_ts,
    'propostes_pendents': $proposals_count,
}

with open('$METRICS_FILE', 'w') as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)
print('OK')
" 2>/dev/null

    log "   Mètriques guardades a $METRICS_FILE"
    log "   Done: $done_24h | Failed: $failed_24h | Errors: $errors_24h | Propostes: $proposals_count"
}

# =============================================================================
# MAIN
# =============================================================================

# Variables globals per mètriques (s'omplen durant l'anàlisi)
METRIC_DONE_24H=0
METRIC_FAILED_24H=0
METRIC_ERRORS_24H=0
METRIC_TIMEOUTS=0

log "═══════════════════════════════════════════════════"
log "🔧 IMPROVE-OPENCLAW iniciat"

# Crear directoris necessaris
mkdir -p "$PROPOSALS_DIR" "$(dirname "$METRICS_FILE")"
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# ── Control de freqüència: cada 6 hores ─────────────────────────────────────
LAST_RUN_FILE="$TASKS_DIR/.improve-openclaw-last-run"
INTERVAL=21600  # 6 hores en segons
if [ -f "$LAST_RUN_FILE" ]; then
    last_run_ts=$(cat "$LAST_RUN_FILE" 2>/dev/null)
    now_ts=$(date +%s)
    elapsed=$(( now_ts - last_run_ts ))
    if [ "$elapsed" -lt "$INTERVAL" ] 2>/dev/null; then
        elapsed_min=$(( elapsed / 60 ))
        log "   Executat fa ${elapsed_min}min. Saltant."
        log "═══════════════════════════════════════════════════"
        exit 0
    fi
fi

# ── Fase 1: Anàlisis de lectura (no toquen ~/.openclaw/) ────────────────────
analyze_openclaw_log
analyze_failed_tasks
analyze_heartbeat_report

# ── Fase 2: Anàlisis que poden modificar ~/.openclaw/ ───────────────────────
# Parar el bot ABANS de tocar fitxers del workspace
stop_openclaw

# Trap per garantir reinici si l'script falla o s'interromp
trap 'start_openclaw' EXIT

analyze_skill_md
analyze_claude_sh
analyze_personality_files

# ── Fase 3: Reiniciar el bot ────────────────────────────────────────────────
start_openclaw
trap - EXIT  # Netejar trap (ja hem reiniciat)

# Recollir mètriques
collect_metrics

# Guardar timestamp d'execució
date +%s > "$LAST_RUN_FILE"

PENDING=$(count_improve_pending)
log "🔧 IMPROVE-OPENCLAW completat. Tasques improve-openclaw pendents: $PENDING"
log "═══════════════════════════════════════════════════"
