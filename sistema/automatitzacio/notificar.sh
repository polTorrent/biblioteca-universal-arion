#!/bin/bash
# =============================================================================
# notificar.sh — Notificacions unificades a Discord per al sistema Arion
# =============================================================================
# Ús: bash notificar.sh <nivell> "<missatge>"
# Nivells: info, warning, critical, success
# =============================================================================

NOTIFICATIONS_ENABLED="${ARION_NOTIFICATIONS:-true}"
DISCORD_CHANNEL="${ARION_DISCORD_CHANNEL:-1469504522614476953}"

# Carregar token de Discord (preferentment de .env)
DISCORD_TOKEN="${DISCORD_BOT_TOKEN:-}"
if [ -z "$DISCORD_TOKEN" ] && [ -f "$HOME/.hermes/.env" ]; then
    DISCORD_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" "$HOME/.hermes/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi

# Si no hi ha token, sortir silenciosament
if [ -z "$DISCORD_TOKEN" ]; then
    exit 0
fi

if [ "$NOTIFICATIONS_ENABLED" != "true" ]; then
    exit 0
fi

LEVEL="$1"
MESSAGE="$2"

case "$LEVEL" in
    critical) EMOJI="🔴" ;;
    warning)  EMOJI="⚠️" ;;
    success)  EMOJI="✅" ;;
    info)     EMOJI="📢" ;;
    *)        EMOJI="📢"; LEVEL="info" ;;
esac

PAYLOAD="**$EMOJI $LEVEL** — $(date '+%Y-%m-%d %H:%M:%S UTC')
$MESSAGE"

# Escapar JSON correctament
ESCAPED=$(python3 -c "import json; print(json.dumps('''$PAYLOAD'''))" 2>/dev/null)

curl -s -X POST \
    "https://discord.com/api/v10/channels/${DISCORD_CHANNEL}/messages" \
    -H "Authorization: Bot ${DISCORD_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"content\": ${ESCAPED}}" \
    > /dev/null 2>&1
