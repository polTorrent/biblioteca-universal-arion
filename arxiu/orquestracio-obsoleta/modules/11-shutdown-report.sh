#!/bin/bash
# =============================================================================
# 11-shutdown-report.sh — Informe exhaustiu d'aturada per esgotament DIEM
# =============================================================================
# S'executa quan el worker atura per manca de pressupost.
# Arguments: $1=DIEM_actual $2=DIEM_disponible $3=cost_tasca_rebutjada
# =============================================================================
set -uo pipefail

MODULE_NAME="shutdown-report"
source "${BASH_SOURCE[0]%/*}/common.sh"

DIEM_ACTUAL="${1:-0}"
DIEM_DISPONIBLE="${2:-0}"
COST_REBUTJAT="${3:-0}"

REPORT_FILE="$PROJECT/sistema/state/shutdown_report_$(date '+%Y%m%d_%H%M%S').md"
NOTIFY_SCRIPT="$PROJECT/sistema/automatitzacio/notificar.sh"

generate_report() {
    local now=$(date '+%Y-%m-%d %H:%M:%S UTC')
    local start_time="$START_TIME"
    local uptime=""
    
    if [ -f "$PROJECT/sistema/state/worker_heartbeat.json" ]; then
        start_time=$(python3 -c "
import json, sys
try:
    d = json.load(open('$PROJECT/sistema/state/worker_heartbeat.json'))
    print(d.get('start_time', '$(date +%s)'))
except: print('$(date +%s)')
" 2>/dev/null)
    fi
    
    if [ -n "$start_time" ] && [ "$start_time" != "$(date +%s)" ]; then
        uptime="$(( ($(date +%s) - start_time) / 60 )) minuts"
    else
        uptime="desconegut"
    fi

    # Recompte de tasques
    local done_count=$(find "$PROJECT/sistema/tasks/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
    local fail_count=$(find "$PROJECT/sistema/tasks/failed/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
    local pending_count=$(ls -1 "$PROJECT/sistema/tasks/pending/"*.json 2>/dev/null | wc -l)
    local running_count=$(ls -1 "$PROJECT/sistema/tasks/running/"*.json 2>/dev/null | wc -l)
    local fail_perm_count=$(ls -1 "$PROJECT/sistema/tasks/failed_permanent/"*.json 2>/dev/null | wc -l)

    # DIEM consumit avui
    local diem_start="desconegut"
    if [ -f "$PROJECT/sistema/state/cycle_diem_start" ]; then
        diem_start=$(cat "$PROJECT/sistema/state/cycle_diem_start")
    fi
    local diem_consumed="desconegut"
    if [ "$diem_start" != "desconegut" ]; then
        diem_consumed=$(python3 -c "print(round(float('$diem_start') - float('$DIEM_ACTUAL'), 4))" 2>/dev/null)
    fi

    # Últimes tasques completades
    local last_done=$(find "$PROJECT/sistema/tasks/done/" -name "*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -10)
    local last_done_summary=""
    if [ -n "$last_done" ]; then
        last_done_summary=$(echo "$last_done" | while read -r ts path; do
            local f=$(basename "$path")
            local tid=$(python3 -c "import json; print(json.load(open('$path')).get('id','?'))" 2>/dev/null)
            local ttype=$(python3 -c "import json; print(json.load(open('$path')).get('type','?'))" 2>/dev/null)
            echo "  - $tid ($ttype)"
        done 2>/dev/null)
    fi

    # Últimes tasques fallides
    local last_failed=$(find "$PROJECT/sistema/tasks/failed/" -name "*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -5)
    local last_failed_summary=""
    if [ -n "$last_failed" ]; then
        last_failed_summary=$(echo "$last_failed" | while read -r ts path; do
            local f=$(basename "$path")
            local tid=$(python3 -c "import json; print(json.load(open('$path')).get('id','?'))" 2>/dev/null)
            local terr=$(python3 -c "import json; print(json.load(open('$path')).get('last_error','?'))" 2>/dev/null)
            echo "  - $tid: $terr"
        done 2>/dev/null)
    fi

    # Commits del dia
    local commits_today=$(cd "$PROJECT" && git log --since="$(date '+%Y-%m-%d 00:00:00')" --oneline 2>/dev/null | wc -l)
    local last_commit=$(cd "$PROJECT" && git log --oneline -1 2>/dev/null)

    # Generar informe markdown
    cat > "$REPORT_FILE" << EOF
# 🛑 Informe d'Aturada — Cicle Arion

**Data:** $now
**Motiu:** Pressupost DIEM esgotat

---

## 💰 Estat del Pressupost

| Mètrica | Valor |
|---------|-------|
| DIEM al inici del cicle | $diem_start |
| DIEM actual | $DIEM_ACTUAL |
| DIEM consumit | $diem_consumed |
| Marge reservat (DIEM_RESERVE) | 0.5 |
| Disponible per tasques | $DIEM_DISPONIBLE |
| Cost tasca rebutjada | $COST_REBUTJAT |

---

## 📊 Resum del Cicle

| Mètrica | Valor |
|---------|-------|
| Durada activa | $uptime |
| Tasques completades | $done_count |
| Tasques fallides | $fail_count |
| Tasques pendents (pendent) | $pending_count |
| Tasques en execució (running) | $running_count |
| Fallides permanents | $fail_perm_count |
| Commits avui | $commits_today |

---

## ✅ Últimes tasques completades

$last_done_summary

---

## ❌ Últimes tasques fallides

$last_failed_summary

---

## 📝 Últim commit

$last_commit

---

## ⚠️ Tasques pendents per al proper cicle

Les $pending_count tasques pendents restaran a \`sistema/tasks/pending/\` per al proper cicle.

EOF

    log "📊 Informe d'aturada generat: $REPORT_FILE"
}

send_notification() {
    local msg="🛑 **Arion: Aturada per pressupost DIEM**
DIEM actual: $DIEM_ACTUAL | Consumit: $(python3 -c "print(round(float('$DIEM_ACTUAL') - float('${DIEM_START:-0}'), 2))" 2>/dev/null || echo '?') | Tasques completades: $(find "$PROJECT/sistema/tasks/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
Informe: $REPORT_FILE"
    
    if [ -x "$NOTIFY_SCRIPT" ]; then
        bash "$NOTIFY_SCRIPT" "shutdown" "$msg" 2>/dev/null || true
    fi
    log "📬 Notificació d'aturada enviada"
}

# ── Executar ──────────────────────────────────────────────────────────────────
generate_report
send_notification

log_json "shutdown" "DIEM=$DIEM_ACTUAL available=$DIEM_DISPONIBLE rejected_cost=$COST_REBUTJAT report=$REPORT_FILE"
