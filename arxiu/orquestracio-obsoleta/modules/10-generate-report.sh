#!/bin/bash
# 10-generate-report.sh — Generació del report i notificació
MODULE_NAME="generate-report"
source "${BASH_SOURCE[0]%/*}/common.sh"

generate_report() {
    log "📋 Generant report..."
    log_json "info" "generating_report"
    
    # Actualitzar estat del catàleg
    python3 "$PROJECT/sistema/scripts/update_queue_status.py" 2>/dev/null
    
    # Generar report detallat
    local REPORT_FILE="$PROJECT/sistema/state/last_heartbeat_report.md"
    if [ -f "$PROJECT/scripts/informe_detallat.py" ]; then
        python3 "$PROJECT/scripts/informe_detallat.py" > "$REPORT_FILE" 2>/dev/null
    else
        local validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
        local needs_fix=$(find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | wc -l)
        local total_trad=$(find "$PROJECT/obres" -name "traduccio.md" 2>/dev/null | wc -l)
        local pending=$(count_pending)
        local done_today=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
        local worker_status="❌ INACTIU"
        pgrep -f "worker" > /dev/null 2>&1 && worker_status="✅ ACTIU"
        
        cat > "$REPORT_FILE" << REPORT
💓 **Heartbeat Arion** — $(date '+%H:%M %d/%m')

📊 **Traduccions:** $total_trad total | $validated validades | $needs_fix pendents fix
⚙️ **Worker:** $worker_status | $done_today tasques avui | $pending cua
REPORT
    fi
    
    # Enviar report a Discord
    if [ -f "$PROJECT/sistema/automatitzacio/send-heartbeat-report.sh" ]; then
        bash "$PROJECT/sistema/automatitzacio/send-heartbeat-report.sh" 2>/dev/null || true
    fi
    
    # Processar propostes Discord
    if [ -f "$PROJECT/sistema/automatitzacio/processar-propostes.sh" ]; then
        bash "$PROJECT/sistema/automatitzacio/processar-propostes.sh" 2>/dev/null || true
    fi
    
    # Guardar estat JSON
    local validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
    local needs_fix=$(find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | wc -l)
    local worker_bool="False"
    pgrep -f 'worker' > /dev/null 2>&1 && worker_bool="True"
    python3 -c "
import json, datetime
state = {
    'timestamp': datetime.datetime.now(datetime.UTC).isoformat()+'Z',
    'validated_works': $validated,
    'needs_fix_works': $needs_fix,
    'pending_tasks': $(count_pending),
    'worker_active': $worker_bool
}
with open('$PROJECT/sistema/state/heartbeat_state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    generate_report
fi
