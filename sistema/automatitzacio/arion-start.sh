#!/bin/bash
# =============================================================================
# arion-start.sh — Inicia el sistema Biblioteca Arion
# =============================================================================
# Ús: bash sistema/automatitzacio/arion-start.sh
# Es crida automaticament a les 16:00 UTC via cron
# =============================================================================

PROJECT="$HOME/biblioteca-universal-arion"
LOG="$HOME/arion-schedule.log"
TASKS_DIR="$PROJECT/sistema/tasks"
STATE_DIR="$PROJECT/sistema/state"
LOCKFILE="$TASKS_DIR/worker.lock"
DIEM_STOP="$STATE_DIR/diem_stop"
VENICE_CLI="$HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py"
MIN_DIEM=1.0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] [START] $1"
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

# Comprovar DIEM_STOP i netejar si el DIEM és suficient
if [ -f "$DIEM_STOP" ]; then
    log "⚠️ Fitxer diem_stop detectat. Comprovant saldo DIEM..."
    
    if [ -f "$VENICE_CLI" ]; then
        BALANCE=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
        
        if [ -n "$BALANCE" ]; then
            IS_LOW=$(python3 -c "print('yes' if float('$BALANCE') < $MIN_DIEM else 'no')" 2>/dev/null)
            
            if [ "$IS_LOW" = "no" ]; then
                log "✅ DIEM suficient ($BALANCE >= $MIN_DIEM). Esborrant diem_stop..."
                rm -f "$DIEM_STOP"
            else
                log "🛑 DIEM insuficient ($BALANCE < $MIN_DIEM). No s'iniciarà el worker."
                log "   Executa manualment: bash sistema/automatitzacio/reset-diem.sh"
                exit 1
            fi
        else
            log "⚠️ No s'ha pogut obtenir el saldo DIEM. Esborrant diem_stop per si de cas..."
            rm -f "$DIEM_STOP"
        fi
    else
        log "⚠️ Venice CLI no trobat. Esborrant diem_stop..."
        rm -f "$DIEM_STOP"
    fi
fi

log "🚀 Iniciant sistema Arion..."

# Netejar estat residual del circuit breaker (persisteix a /tmp)
rm -f /tmp/arion-worker-errors.txt 2>/dev/null
rm -rf /tmp/arion-model-errors/ 2>/dev/null

# 1. Iniciar worker
cd "$PROJECT"
nohup bash sistema/automatitzacio/worker.sh --mode=hybrid > /dev/null 2>&1 &
log "   ✅ Venice Worker iniciat"

# 2. Afegir cron del heartbeat (cada 2 hores, només dins horari actiu)
(crontab -l 2>/dev/null | grep -v "heartbeat.sh"; echo "0 16-23/2 * * * /bin/bash $PROJECT/sistema/automatitzacio/heartbeat.sh >> $HOME/heartbeat.log 2>&1") | crontab -

log "   ✅ Heartbeat programat (16:00-23:59 UTC, cada 2h)"

# 3. Verificar que el worker està corrent
sleep 3
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "✅ Sistema Arion actiu (PID $PID)"
        log "   Horari: 16:00 - 00:00 UTC"
    else
        log "❌ Error: Worker no ha arrencat correctament"
        exit 1
    fi
else
    log "⚠️ Worker iniciat però sense lockfile"
fi

# 4. Notificar per Discord (si existeix el script)
NOTIFICAR="$PROJECT/sistema/automatitzacio/notificar.sh"
if [ -x "$NOTIFICAR" ]; then
    bash "$NOTIFICAR" success "Sistema Arion iniciat — Worker: Actiu (PID $PID)"
fi