#!/bin/bash
# 02-check-worker.sh — Estat del worker + auto-restart
MODULE_NAME="check-worker"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_worker() {
    if pgrep -f "worker\.sh" > /dev/null 2>&1; then
        log "✅ Worker actiu"
        log_json "info" "worker_active=true"
        return 0
    fi
    log "⚠️ Worker NO actiu. Reiniciant..."
    log_json "warning" "worker_active=false, restarting"
    
    # Netejar lockfile orfe
    [ -f "$TASKS_DIR/worker.lock" ] && ! kill -0 "$(cat "$TASKS_DIR/worker.lock")" 2>/dev/null && rm -f "$TASKS_DIR/worker.lock"
    
    # Retornar running a pending
    for f in "$TASKS_DIR/running/"*.json; do [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/"; done
    
    # Reiniciar worker (unificat o venice com a fallback)
    local worker_script="$PROJECT/sistema/automatitzacio/worker.sh"
    [ ! -f "$worker_script" ] && worker_script="$PROJECT/sistema/automatitzacio/venice-worker.sh"
    
    nohup bash "$worker_script" >> "$LOG" 2>&1 &
    disown
    log "✅ Worker reiniciat (PID $!)"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"
    LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3
    TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_worker
fi
