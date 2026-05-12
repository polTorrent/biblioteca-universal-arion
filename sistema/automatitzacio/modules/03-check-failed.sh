#!/bin/bash
# 03-check-failed.sh — Recuperació de tasques fallides
MODULE_NAME="check-failed"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_failed() {
    log "♻️ Tasques fallides..."
    log_json "info" "checking_failed_tasks"
    
    mkdir -p "$TASKS_DIR/failed_permanent"
    
    find "$TASKS_DIR/failed/" -name "*.json" -mmin +60 -type f 2>/dev/null | head -5 | while read -r failed; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        local task_info
        task_info=$(python3 -c "
import json
with open('$failed') as fh: d = json.load(fh)
retries = d.get('retries', d.get('retry_count', 0))
instruction = d.get('instruction', '')
task_type = d.get('type', 'unknown')
regen_count = d.get('regen_count', 0)
total_failures = d.get('total_failures', retries + regen_count * 3)
print(f'{retries}|{len(instruction)}|{task_type}|{regen_count}|{total_failures}')
" 2>/dev/null)
        
        local retries inst_len task_type regen_count total_failures
        IFS='|' read -r retries inst_len task_type regen_count total_failures <<< "$task_info"
        retries=${retries:-0}; regen_count=${regen_count:-0}; total_failures=${total_failures:-0}
        
        if [ "$total_failures" -ge 9 ] || [ "$regen_count" -ge 3 ]; then
            mv "$failed" "$TASKS_DIR/failed_permanent/"
            log "   ⛔ Abandonada ($total_failures intents): $(basename "$failed")"
            continue
        fi
        
        local inst_len=${inst_len:-0}
        if [ "$inst_len" -gt 200 ] && [ "$retries" -lt 2 ]; then
            # Regenerar instrucció simplificada amb ruta correcta
            python3 -c "
import json, re, os
with open('$failed') as fh: d = json.load(fh)
instruction = d.get('instruction', '')
obra_path = ''
m = re.search(r'obres/[a-z0-9/_-]+', instruction)
if m: obra_path = m.group(0).rstrip('/')
if obra_path and d.get('type') in ('translate','fetch','translation'):
    full = os.path.expanduser('~/biblioteca-universal-arion')
    has_original = os.path.isfile(os.path.join(full, obra_path, 'original.md'))
    if has_original:
        d['instruction'] = f'Tradueix al català literari. Ruta: {obra_path}'
        d['type'] = 'translate'
d['total_failures'] = d.get('total_failures',0) + d.get('retries',0)
d['retries'] = 0; d['retry_count'] = 0; d['recovered'] = True
d['regen_count'] = d.get('regen_count',0) + 1
with open('$failed','w') as fh: json.dump(d,fh,indent=2,ensure_ascii=False)
" 2>/dev/null
            mv "$failed" "$TASKS_DIR/pending/"
            log "   ♻️ Regenerada: $(basename "$failed")"
        elif [ "$retries" -lt 2 ]; then
            python3 -c "
import json
with open('$failed') as fh: d = json.load(fh)
d['total_failures'] = d.get('total_failures',0) + d.get('retries',0)
d['retries'] = 0; d['retry_count'] = 0; d['recovered'] = True
d['regen_count'] = d.get('regen_count',0) + 1
with open('$failed','w') as fh: json.dump(d,fh,indent=2,ensure_ascii=False)
" 2>/dev/null
            mv "$failed" "$TASKS_DIR/pending/"
            log "   ♻️ Recuperada: $(basename "$failed")"
        else
            mv "$failed" "$TASKS_DIR/failed_permanent/"
            log "   ⛔ Abandonada (max retries): $(basename "$failed")"
        fi
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_failed
fi
