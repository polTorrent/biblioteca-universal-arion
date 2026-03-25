#!/bin/bash
# worker-watchdog.sh v2 — Comprova si el worker corre i el reinicia si no
# S'executa cada 5 minuts via cron
#
# Millores v2:
#   - Apunta a claude-worker-mini.sh (l'script correcte)
#   - Detecta workers inactius (sense log >30 min amb tasques pending)
#   - Detecta locks orfes
#   - Detecta tasques a running/ sense procés claude actiu

LOCK_FILE="$HOME/.openclaw/workspace/tasks/worker.lock"
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
LOG="$HOME/claude-worker.log"
WORKER_SCRIPT="$HOME/biblioteca-universal-arion/sistema/automatitzacio/claude-worker-mini.sh"
STALE_MINUTES=30

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🐕 Watchdog: $1" >> "$LOG"; }

# ── 1. Comprovar lock i PID ───────────────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # PID existeix — comprovar si està actiu o encallat

        # Comprovar si hi ha tasques a running/ sense procés claude fill
        RUNNING_COUNT=$(ls "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)
        if [ "$RUNNING_COUNT" -gt 0 ]; then
            # Hi ha tasca running — comprovar que hi ha un procés claude actiu
            if ! pgrep -P "$OLD_PID" > /dev/null 2>&1 && ! pgrep -f "claude -p" > /dev/null 2>&1; then
                # Tasca running però cap procés claude — el worker pot estar encallat
                log "Tasca a running/ però cap procés claude actiu. Possible encallament."
                # Donar 5 min de marge (pot ser entre tasques)
                LAST_LOG_TIME=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
                NOW=$(date +%s)
                DIFF=$(( (NOW - LAST_LOG_TIME) / 60 ))
                if [ "$DIFF" -ge "$STALE_MINUTES" ]; then
                    log "Log sense activitat fa ${DIFF} min amb tasca running. Matant worker $OLD_PID."
                    kill -9 "$OLD_PID" 2>/dev/null
                    # Tornar tasques running a pending
                    for f in "$TASKS_DIR/running/"*.json; do
                        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "Retornada a pending: $(basename "$f")"
                    done
                    rm -f "$LOCK_FILE"
                    # Continuarà a la secció d'iniciar worker
                else
                    exit 0  # Encara dins del marge
                fi
            else
                exit 0  # Claude actiu, tot bé
            fi
        else
            # No hi ha tasques running — worker està idle o processant, tot bé
            exit 0
        fi
    else
        log "Lock orfe trobat (PID $OLD_PID mort). Netejant."
        rm -f "$LOCK_FILE"
        # Tornar tasques running a pending
        for f in "$TASKS_DIR/running/"*.json; do
            [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "Retornada a pending: $(basename "$f")"
        done
    fi
fi

# ── 2. Comprovar si hi ha processos claude-worker actius sense lock ───────────
if pgrep -f "claude-worker-mini" > /dev/null; then
    log "Procés worker actiu detectat sense lock. Sortint."
    exit 0
fi

# ── 3. Iniciar worker ────────────────────────────────────────────────────────
# Només iniciar si hi ha tasques pending
PENDING_COUNT=$(ls "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
if [ "$PENDING_COUNT" -eq 0 ]; then
    # No hi ha tasques, no cal worker
    exit 0
fi

log "Iniciant worker ($PENDING_COUNT tasques pending)..."
cd "$HOME/biblioteca-universal-arion"
source ~/.nvm/nvm.sh 2>/dev/null
nohup bash "$WORKER_SCRIPT" >> "$LOG" 2>&1 &
log "Worker iniciat (PID $!)"
