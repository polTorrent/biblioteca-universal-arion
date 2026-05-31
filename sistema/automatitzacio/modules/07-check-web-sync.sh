#!/bin/bash
# 07-check-web-sync.sh — Sincronització web
MODULE_NAME="check-web-sync"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_web_sync() {
    log "🌐 Comprovant web..."
    
    local docs_time=0 obres_time=0
    
    [ -d "$PROJECT/docs" ] && docs_time=$(find "$PROJECT/docs" -name "*.html" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
    [ -d "$PROJECT/obres" ] && obres_time=$(find "$PROJECT/obres" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
    docs_time=${docs_time:-0}; obres_time=${obres_time:-0}
    
    if [ "$obres_time" -gt "$docs_time" ] 2>/dev/null || true; then
        if ! task_exists "build.py|regenera.*web|actualitza.*web" > /dev/null 2>&1; then
            # Tasca de publicació: crear directament, sense comptar contra MAX_PENDING
            export PROJECT
            bash "$TASK_MANAGER" add "publish" "Web desactualitzada. Executa 'python3 sistema/web/build.py'. Commit i push." 2>/dev/null
            log "   🌐 Publicació web afegida"
            log_json "warning" "web_outdated"
        fi
    else
        log "   🌐 Web OK"
        log_json "info" "web_synced"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_web_sync
fi
