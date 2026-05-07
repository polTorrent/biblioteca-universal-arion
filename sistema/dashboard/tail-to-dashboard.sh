#!/bin/bash
# Monitoritza un fitxer de log i envia nous events al dashboard

LOG_FILE="$1"
DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="$DASHBOARD_DIR/logger.py"

if [ ! -f "$LOG_FILE" ]; then
    echo "Ús: $0 <fitxer-log>"
    exit 1
fi

echo "Monitoritzant $LOG_FILE..."

# Seguiment del fitxer amb tail -f
tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
    # Detectar tipus de missatge
    if echo "$line" | grep -qiE "error|exception|failed|❌|⚠️"; then
        python3 "$LOGGER" "error" "$line" 2>/dev/null
    elif echo "$line" | grep -qiE "thinking|🧠|💡|analitz"; then
        python3 "$LOGGER" "llm" "$line" 2>/dev/null
    elif echo "$line" | grep -qiE "executant|terminal|patch|file|🔧|📝"; then
        python3 "$LOGGER" "tools" "$line" 2>/dev/null
    else
        python3 "$LOGGER" "worker" "$line" 2>/dev/null
    fi
done