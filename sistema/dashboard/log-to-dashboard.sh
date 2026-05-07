#!/bin/bash
# Arion Dashboard Logger per Bash Scripts
# Ús: log-to-dashboard.sh [tipus] [missatge]

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Directori de logs
LOGS_DIR="$DASHBOARD_DIR/logs"

# Map tipus d'event a fitxer
case "$1" in
    hermes)
        LOG_FILE="$LOGS_DIR/hermes.log"
        ;;
    llm)
        LOG_FILE="$LOGS_DIR/llm.log"
        ;;
    worker)
        LOG_FILE="$LOGS_DIR/worker.log"
        ;;
    tools)
        LOG_FILE="$LOGS_DIR/tools.log"
        ;;
    error)
        LOG_FILE="$LOGS_DIR/errors.log"
        ;;
    *)
        echo "Ús: $0 [hermes|llm|worker|tools|error] [missatge]"
        exit 1
        ;;
esac

# Format del missatge
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
MESSAGE="${@:2}"

# Escriure al fitxer
echo "[$TIMESTAMP] $MESSAGE" >> "$LOG_FILE"