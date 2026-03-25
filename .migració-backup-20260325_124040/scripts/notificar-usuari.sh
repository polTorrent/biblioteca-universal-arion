#!/bin/bash
# =============================================================================
# notificar-usuari.sh - Envia notificació a un usuari de Discord
# =============================================================================
# Ús: ./notificar-usuari.sh <usuari_id> "<missatge>"
#     ./notificar-usuari.sh --pending  (processa notificacions pendents)
# =============================================================================

set -euo pipefail

DISCORD_TOKEN="${DISCORD_BOT_TOKEN:-}"
CHANNEL_NOTIFICACIONS="1479504522614476953"
PENDING_FILE="$HOME/.openclaw/workspace/pending_notification.txt"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [NOTIFICACIÓ] $1"
}

# Enviar notificació via curl (Discord API)
send_notification() {
    local user_id="$1"
    local message="$2"
    local channel_id="${3:-$CHANNEL_NOTIFICACIONS}"
    
    if [ -z "$DISCORD_TOKEN" ]; then
        log "⚠️ DISCORD_BOT_TOKEN no configurat. Guardant notificació pendent..."
        mkdir -p "$(dirname "$PENDING_FILE")"
        cat > "$PENDING_FILE" << EOF
channel:${channel_id}
user:${user_id}
message:${message}
timestamp:$(date -Iseconds)
EOF
        return 1
    fi
    
    # Escapar el missatge per JSON
    local escaped_message
    escaped_message=$(python3 -c "import json; print(json.dumps('''$message'''))")
    
    # Afegir mention de l'usuari
    local full_message="<@${user_id}>\n\n${escaped_message}"
    
    # Enviar via Discord API
    local response
    response=$(curl -s -X POST \
        "https://discord.com/api/v10/channels/${channel_id}/messages" \
        -H "Authorization: Bot ${DISCORD_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"content\": ${full_message}}" \
        -w "%{http_code}" \
        2>/dev/null || echo "000")
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log "✅ Notificació enviada a ${user_id}"
        return 0
    else
        log "❌ Error enviant notificació (HTTP $http_code)"
        return 1
    fi
}

# Processar notificacions pendents
process_pending() {
    if [ ! -f "$PENDING_FILE" ]; then
        log "No hi ha notificacions pendents"
        return 0
    fi
    
    local channel user message timestamp
    channel=$(grep "^channel:" "$PENDING_FILE" | cut -d: -f2-)
    user=$(grep "^user:" "$PENDING_FILE" | cut -d: -f2-)
    message=$(grep "^message:" "$PENDING_FILE" | cut -d: -f2-)
    timestamp=$(grep "^timestamp:" "$PENDING_FILE" | cut -d: -f2-)
    
    if [ -n "$user" ] && [ -n "$message" ]; then
        if send_notification "$user" "$message" "$channel"; then
            rm -f "$PENDING_FILE"
            log "✅ Notificació pendent processada"
        else
            log "⚠️ No s'ha pogut enviar la notificació pendent"
        fi
    fi
}

# Main
case "${1:-}" in
    "--pending")
        process_pending
        ;;
    *)
        if [ $# -lt 2 ]; then
            echo "Ús: $0 <usuari_id> \"<missatge>\" [channel_id]"
            echo "     $0 --pending"
            exit 1
        fi
        send_notification "$1" "$2" "${3:-}"
        ;;
esac