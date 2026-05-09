#!/bin/bash
# 09-audit-catalog.sh — Auditoria del catàleg (mode consolidació)
MODULE_NAME="audit-catalog"
source "${BASH_SOURCE[0]%/*}/common.sh"

audit_catalog() {
    log "🔧 Mode consolidació: auditant catàleg..."
    log_json "info" "auditing_catalog"
    
    local AUDIT_LAST="$PROJECT/config/.last_audit"
    local AUDIT_INTERVAL=43200  # 12 hores
    
    local should_audit=false
    if [ ! -f "$AUDIT_LAST" ]; then
        should_audit=true
    else
        local last=$(cat "$AUDIT_LAST")
        local now=$(date +%s)
        [ $((now - last)) -gt "$AUDIT_INTERVAL" ] && should_audit=true
    fi
    
    if [ "$should_audit" = true ]; then
        bash "$PROJECT/sistema/automatitzacio/auditar-cataleg.sh" --fix
        date +%s > "$AUDIT_LAST"
        log "   ✅ Auditoria completada"
        log_json "info" "audit_completed"
    else
        log "   ⏭️ Auditoria recent, saltant"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    audit_catalog
fi
