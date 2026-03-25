#!/bin/bash
# worker-watchdog.sh — Comprova si el worker corre i el reinicia si no
# S'executa cada 5 minuts via cron

LOCK_FILE="$HOME/.openclaw/workspace/tasks/worker.lock"
LOG="$HOME/claude-worker.log"
WORKER_SCRIPT="$HOME/biblioteca-universal-arion/sistema/automatitzacio/claude-worker.sh"

# Comprovar si el worker corre
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Worker actiu, sortir
        exit 0
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔧 Watchdog: Lock obsolet trobat, netejant..." >> "$LOG"
        rm -f "$LOCK_FILE"
    fi
fi

# Comprovar si hi ha processos claude actius (tasca en curs)
if pgrep -f "claude-worker" > /dev/null || pgrep -f "claude-exec" > /dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔧 Watchdog: Procés actiu detectat, sortint..." >> "$LOG"
    exit 0
fi

# No hi ha worker, iniciar
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Watchdog: Iniciant worker..." >> "$LOG"
cd "$HOME/biblioteca-universal-arion"
nohup bash "$WORKER_SCRIPT" >> "$LOG" 2>&1 &
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Watchdog: Worker iniciat (PID $!)" >> "$LOG"