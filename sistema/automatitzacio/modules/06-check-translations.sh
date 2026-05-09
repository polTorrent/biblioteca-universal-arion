#!/bin/bash
# 06-check-translations.sh — Obres pendents de traducció
MODULE_NAME="check-translations"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_translations() {
    log "📚 Analitzant obres pendents..."
    log_json "info" "checking_translations"
    
    bash "$PROJECT/sistema/automatitzacio/detectar-incompletes.sh" 2>/dev/null || true
    
    python3 "$PROJECT/sistema/scripts/check_translations.py" 2>/dev/null | while IFS='|' read -r action autor titol lingua obra_path categoria; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        case "$action" in
            FETCH)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "fetch" "mkdir -p $obra_path && python3 sistema/traduccio/cercador_fonts_v2.py \"$autor\" \"$titol\" \"$lingua\" \"$obra_path\" && if [ ! -s $obra_path/original.md ]; then echo ERROR && exit 1; fi && git add -A && git commit -m \"font: $titol de $autor\" && git push"
                    log "   📥 Fetch: $titol de $autor ($lingua)"
                fi
                ;;
            TRANSLATE)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "python3 sistema/traduccio/traduir_pipeline.py $obra_path/"
                    log "   📝 Translate: $titol de $autor"
                fi
                ;;
        esac
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_translations
fi
