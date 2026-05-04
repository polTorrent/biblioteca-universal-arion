#!/bin/bash
# =============================================================================
# arion-stop.sh — Atura el sistema Biblioteca Arion
# =============================================================================
# Ús: bash sistema/automatitzacio/arion-stop.sh
# Es crida automaticament a les 00:00 UTC via cron
# =============================================================================

PROJECT="$HOME/biblioteca-universal-arion"
LOG="$HOME/arion-schedule.log"
TASKS_DIR="$PROJECT/sistema/tasks"
LOCKFILE="$TASKS_DIR/worker.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] [STOP] $1" | tee -a "$LOG"
}

log "🛑 Aturant sistema Arion..."

# 1. Eliminar cron del heartbeat
crontab -l 2>/dev/null | grep -v "heartbeat.sh" | crontab -
log "   ✅ Heartbeat desprogramat"

# 2. Aturar worker
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "   Aturant worker (PID $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        
        # Forçar si encara corre
        if kill -0 "$PID" 2>/dev/null; then
            log "   Forçant aturada..."
            kill -9 "$PID" 2>/dev/null
            sleep 1
        fi
        
        rm -f "$LOCKFILE"
        log "   ✅ Worker aturat"
    else
        log "   🧹 Netejant lockfile orfe..."
        rm -f "$LOCKFILE"
    fi
else
    log "   ℹ️ Worker ja aturat (sense lockfile)"
fi

# 3. Aturar qualsevol procés venice-worker residual
pkill -f "venice-worker" 2>/dev/null || true
pkill -f "hermes-worker" 2>/dev/null || true
log "   ✅ Processos workers netejats"

# 4. Verificar estat final
if pgrep -f "venice-worker" > /dev/null 2>&1; then
    log "⚠️ Alerta: encara hi ha processos venice-worker corrent"
else
    log "✅ Sistema Arion aturat completament"
fi

# 5. Notificar per Discord (si existeix el canal)
if command -v hermes &> /dev/null; then
    hermes send discord:biblioteca-arion "🛑 **Sistema Arion aturat**\nHorari actiu finalitzat: 00:00 UTC\nWorker: Aturat" 2>/dev/null || true
fi