#!/bin/bash
# =============================================================================
# arion-start.sh — Inicia el sistema Biblioteca Arion
# =============================================================================
# Ús: bash sistema/automatitzacio/arion-start.sh
# Es crida automaticament a les 19:00 UTC via cron
# =============================================================================

PROJECT="$HOME/biblioteca-universal-arion"
LOG="$HOME/arion-schedule.log"
TASKS_DIR="$PROJECT/sistema/tasks"
LOCKFILE="$TASKS_DIR/worker.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] [START] $1" | tee -a "$LOG"
}

# Comprovar si ja està actiu
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "⚠️ Worker ja actiu (PID $PID). Res a fer."
        exit 0
    else
        log "🧹 Netejant lockfile orfe..."
        rm -f "$LOCKFILE"
    fi
fi

log "🚀 Iniciant sistema Arion..."

# 1. Iniciar worker
cd "$PROJECT"
nohup bash sistema/automatitzacio/venice-worker.sh > /dev/null 2>&1 &
log "   ✅ Venice Worker iniciat"

# 2. Afegir cron del heartbeat (cada 2 hores)
(crontab -l 2>/dev/null | grep -v "heartbeat.sh"; echo "0 */2 * * * /bin/bash $PROJECT/sistema/automatitzacio/heartbeat.sh >> $HOME/heartbeat.log 2>&1") | crontab -

log "   ✅ Heartbeat programat (cada 2h)"

# 3. Verificar que el worker està corrent
sleep 3
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "✅ Sistema Arion actiu (PID $PID)"
        log "   Horari: 19:00 - 00:00 UTC"
    else
        log "❌ Error: Worker no ha arrencat correctament"
        exit 1
    fi
else
    log "⚠️ Worker iniciat però sense lockfile"
fi

# 4. Notificar per Discord (si existeix el canal)
if command -v hermes &> /dev/null; then
    hermes send discord:biblioteca-arion "🚀 **Sistema Arion iniciat**\nHorari actiu: 19:00 - 00:00 UTC\nWorker: Actiu (PID $PID)" 2>/dev/null || true
fi