#!/bin/bash
# 08-check-maintenance.sh — Manteniment setmanal + rotació logs
MODULE_NAME="check-maintenance"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_maintenance() {
    log "🔧 Manteniment..."
    log_json "info" "checking_maintenance"
    
    # Manteniment setmanal (diumenge)
    local day=$(date +%u)
    if [ "$day" -eq 7 ]; then
        local last_maint=$(find "$TASKS_DIR/done/" -name "*.json" -mtime -7 -type f 2>/dev/null | xargs grep -l "manteniment\|maintenance" 2>/dev/null | head -1)
        if [ -z "$last_maint" ] && ! task_exists "manteniment\|maintenance" > /dev/null 2>&1; then
            add_task "maintenance" "Manteniment setmanal: 1) Neteja Zone.Identifier. 2) Verifica imports. 3) Git gc. 4) Espai disc. 5) Reporta estat."
        fi
    fi
    
    # Rotació done/ (>7 dies)
    local count=$(find "$TASKS_DIR/done/" -name "*.json" -mtime +7 -type f 2>/dev/null | wc -l)
    find "$TASKS_DIR/done/" -name "*.json" -mtime +7 -type f -delete 2>/dev/null
    [ "$count" -gt 0 ] && log "   🧹 $count tasques antigues eliminades"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_maintenance
fi
