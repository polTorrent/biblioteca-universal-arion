#!/bin/bash
# 04-check-needs-fix.sh — Detectar .needs_fix i crear tasques correctores
MODULE_NAME="check-needs-fix"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_needs_fix() {
    log "🔧 Comprovant obres amb .needs_fix..."
    
    find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | while read -r needs_fix_file; do
        local obra_dir=$(dirname "$needs_fix_file")
        local obra_name=$(basename "$obra_dir")
        local relpath=$(python3 -c "import os; print(os.path.relpath('$obra_dir', '$PROJECT'))")
        
        [ -f "$obra_dir/.fixing" ] && continue
        ls "$TASKS_DIR/pending/"*"$obra_name"* "$TASKS_DIR/running/"*"$obra_name"* 2>/dev/null | grep -q . && continue
        
        local score=$(grep -oP '\d+\.?\d*/10' "$needs_fix_file" | head -1 | cut -d/ -f1)
        local score_int=${score%%.*}
        
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        if [ "${score_int:-0}" -eq 0 ]; then
            log "   🔴 $obra_name: puntuació 0/10 — RETRADUCCIÓ"
            add_task "translation" "Executa el pipeline V2 per retraduir: python3 sistema/traduccio/traduir_pipeline.py $relpath"
        else
            log "   🟡 $obra_name: puntuació ${score}/10 — CORRECCIONS"
            add_task "fix" "CORREGEIX obra a $relpath (puntuació ${score}/10). Llegeix .needs_fix per problemes concrets. Corregeix TOTS. Elimina .needs_fix. Commit+push."
        fi
        
        mv "$needs_fix_file" "$obra_dir/.fixing"
    done
    
    # Comprovar .fixing completats
    find "$PROJECT/obres" -name ".fixing" 2>/dev/null | while read -r fixing_file; do
        local obra_dir=$(dirname "$fixing_file")
        local obra_name=$(basename "$obra_dir")
        if ! ls "$TASKS_DIR/pending/"*"$obra_name"* "$TASKS_DIR/running/"*"$obra_name"* 2>/dev/null | grep -q .; then
            local fixing_time=$(stat -c %Y "$fixing_file" 2>/dev/null || echo 0)
            local found_newer=false
            for done_file in "$TASKS_DIR/done/"*"$obra_name"*.json; do
                [ -f "$done_file" ] || continue
                [ "$(stat -c %Y "$done_file" 2>/dev/null || echo 0)" -gt "$fixing_time" ] && found_newer=true && break
            done
            [ "$found_newer" = true ] && rm -f "$fixing_file" && log "   ✅ $obra_name: fix completat"
        fi
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_needs_fix
fi
