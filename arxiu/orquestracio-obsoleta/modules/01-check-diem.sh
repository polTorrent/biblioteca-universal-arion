#!/bin/bash
# 01-check-diem.sh — Comprovació de saldo DIEM
MODULE_NAME="check-diem"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_diem() {
    local balance
    balance=$(python3 $HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    if [ -n "$balance" ]; then
        # Marge: sempre es reserva mig DIEM
        local available
        available=$(python3 -c "print(round(float('$balance') - 0.5, 4))" 2>/dev/null)
        local ok=$(python3 -c "print('yes' if float('$available') >= $MIN_DIEM_RESERVE else 'no')" 2>/dev/null)
        if [ "$ok" = "no" ]; then
            log "⚠️ DIEM baix ($balance, disponible amb marge: $available). No es generen tasques."
            log_json "warning" "DIEM=$balance available=$available below minimum $MIN_DIEM_RESERVE"
            # Aturar worker si està actiu
            if pgrep -f 'worker.sh' > /dev/null 2>&1; then
                touch "$PROJECT/sistema/state/diem_stop"
                log "⛔ diem_stop activat — worker s'aturarà al proper check."
            fi
            return 1
        fi
        log "💰 DIEM: $balance (disponible amb marge: $available, OK)"
        log_json "info" "DIEM=$balance available=$available"
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
