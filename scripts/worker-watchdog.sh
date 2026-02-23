#!/bin/bash
# worker-watchdog.sh — Detecta worker encallat i el reinicia
LOG="$HOME/claude-worker.log"
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WATCHDOG] $1" | tee -a "$LOG"; }

RUNNING=$(ls "$TASKS_DIR/running/"*.json 2>/dev/null | head -1)
[ -z "$RUNNING" ] && exit 0

if pgrep -f "claude.*-p" > /dev/null 2>&1; then
    exit 0
fi

TASK_START=$(stat -c %Y "$RUNNING" 2>/dev/null || echo 0)
NOW=$(date +%s)
ELAPSED=$(( NOW - TASK_START ))

if [ $ELAPSED -gt 300 ]; then
    TASK_NAME=$(basename "$RUNNING" .json)
    log "🐕 Encallat! '$TASK_NAME' porta ${ELAPSED}s sense claude"
    tmux kill-session -t worker 2>/dev/null
    sleep 2
    mv "$RUNNING" "$TASKS_DIR/done/"
    log "🐕 Tasca saltada"
    sleep 2
    tmux new-session -d -s worker "cd $PROJECT_DIR && bash scripts/claude-worker-mini.sh"
    log "🐕 Worker reiniciat"
fi
