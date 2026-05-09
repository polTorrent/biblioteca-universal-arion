#!/bin/bash
# Worker Wrapper amb Dashboard Logging
# Captura tot l'output del worker i l'envia al dashboard

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dashboard"
LOG_SCRIPT="$DASHBOARD_DIR/log-to-dashboard.sh"

# Funció per enviar logs al dashboard
log_dashboard() {
    local tipus="$1"
    local missatge="$2"
    
    if [ -x "$LOG_SCRIPT" ]; then
        "$LOG_SCRIPT" "$tipus" "$missatge"
    fi
}

# Log inici del worker
log_dashboard "worker" "=== WORKER INICIAT ==="
log_dashboard "worker" "Hora: $(date '+%Y-%m-%d %H:%M:%S')"
log_dashboard "worker" "PID: $$"

# Executar el worker real i capturar output
# Tot l'output va al dashboard en temps real
"$@" 2>&1 | while IFS= read -r line; do
    # Detectar tipus de missatge per enviar al panell correcte
    if echo "$line" | grep -qi "error\|exception\|failed"; then
        log_dashboard "error" "$line"
    elif echo "$line" | grep -qi "thinking"; then
        log_dashboard "llm" "$line"
    elif echo "$line" | grep -qi "terminal:\|patch:\|file:\|read_file:"; then
        log_dashboard "tools" "$line"
    else
        log_dashboard "worker" "$line"
    fi
done

# Log finalització
log_dashboard "worker" "=== WORKER ATURAT ==="
log_dashboard "worker" "Hora: $(date '+%Y-%m-%d %H:%M:%S')"
