#!/bin/bash
# =============================================================================
# reset-diem.sh — Reinicia el sistema després del reset de DIEM
# =============================================================================
# S'executa a les 00:00 UTC cada dia via cronjobs de Hermes
# Elimina el fitxer diem_stop i notifica que el sistema torna a estar actiu
# =============================================================================

set -uo pipefail

PROJECT="$HOME/biblioteca-universal-arion"
STATE_DIR="$PROJECT/sistema/state"
LOG="$PROJECT/sistema/logs/reset-diem.log"
DISCORD_CHANNEL="1469504522614476953"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [RESET-DIEM] $1" | tee -a "$LOG"; }

send_discord() {
    local message="$1"
    hermes chat --platform discord --chat-id "$DISCORD_CHANNEL" "$message" 2>/dev/null || true
}

# ── Main ──────────────────────────────────────────────────────────────────────
log "🕐 Executant reset de DIEM..."

# Eliminar fitxer de stop si existeix
if [ -f "$STATE_DIR/diem_stop" ]; then
    rm -f "$STATE_DIR/diem_stop"
    log "✅ Fitxer diem_stop eliminat"
    
    # Notificar
    send_discord "🟢 **Sistema reiniciat**\n\nEls crèdits DIEM s'han restablert. Tots els workers tornen a estar actius.\n\n⏰ Reset executat a $(date '+%Y-%m-%d %H:%M:%S %Z')"
else
    log "ℹ️ No hi havia fitxer diem_stop"
fi

# Guardar estat del reset
echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$STATE_DIR/last_reset"

log "✅ Reset completat"
exit 0