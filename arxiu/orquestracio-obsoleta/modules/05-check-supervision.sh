#!/bin/bash
# 05-check-supervision.sh — Traduccions sense validar
MODULE_NAME="check-supervision"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_supervision() {
    log "🔎 Supervisió de traduccions..."
    log_json "info" "checking_supervision"
    
    python3 "$PROJECT/sistema/scripts/check_supervision.py" 2>/dev/null | while IFS='|' read -r action relpath autor_name obra_name; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        case "$action" in
            MISSING_META)
                if ! task_exists "metadata.*$obra_name" > /dev/null 2>&1; then
                    add_task "supervision" "Falta metadata.yml a $relpath. Crea'l amb: title, author, source_language, category, date, status."
                fi
                ;;
            NEEDS_REVIEW)
                if ! task_exists "supervis.*$obra_name\|qualitat.*$obra_name" > /dev/null 2>&1; then
                    add_task "supervision" "SUPERVISIÓ QUALITAT de '$obra_name' a $relpath. 1) python3 scripts/verificar_traduccio.py ${relpath}/original.md ${relpath}/traduccio.md 2) Compara 5-10 unitats. 3) Si >=7/10 crea .validated. Si <7/10 crea .needs_fix amb problemes."
                fi
                ;;
        esac
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_supervision
fi
