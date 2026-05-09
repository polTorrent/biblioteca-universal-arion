#!/bin/bash
# 01-check-diem.sh — Comprovació de saldo DIEM
MODULE_NAME="check-diem"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_diem() {
    local balance
    balance=$(python3 $HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    if [ -n "$balance" ]; then
        local ok=$(python3 -c "print('yes' if float('$balance') >= $MIN_DIEM_RESERVE else 'no')" 2>/dev/null)
        if [ "$ok" = "no" ]; then
            log "⚠️ DIEM baix ($balance). No es generen tasques."
            log_json "warning" "DIEM=$balance below minimum $MIN_DIEM_RESERVE"
            return 1
        fi
        log "💰 DIEM: $balance (OK)"
        log_json "info" "DIEM=$balance"
    fi
    return 0
}

# Si s'executa directament
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"
    LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5
    MIN_DIEM_RESERVE=0
    TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_diem
fi
