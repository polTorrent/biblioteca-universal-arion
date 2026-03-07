#!/bin/bash
# Regenera el botó de propostes - FIX PERMANENT
# S'executa al heartbeat i també via cron cada 10 minuts

LAST_MESSAGE_FILE="/home/jo/.openclaw/workspace/propostes-button-message.txt"
CHANNEL_ID="1479599316380291276"
TOKEN="MTQ2OTM0NTE0ODEzODk0Njc1Mg.GfH2xn.CHohbG2Mtdsc6iWwj-nAqA_svGT8MwKG5WF-RE"

TIMESTAMP=$(date +%s)

# Eliminar missatge antic
if [ -f "$LAST_MESSAGE_FILE" ]; then
    OLD_ID=$(cat "$LAST_MESSAGE_FILE")
    curl -s -X DELETE "https://discord.com/api/v10/channels/$CHANNEL_ID/messages/$OLD_ID" \
        -H "Authorization: Bot $TOKEN" 2>/dev/null
fi

# Crear nou missatge amb botó
NEW_ID=$(curl -s -X POST "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
    -H "Authorization: Bot $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "flags": 32768,
        "components": [{
            "type": 17,
            "accent_color": 5793266,
            "components": [
                {"type": 10, "content": "# 📚 Biblioteca Universal Arion — Propostes de Traducció\n\nClica el botó per proposar una nova obra per traduir al català."},
                {"type": 10, "content": "📝 Envia la teva proposta"},
                {"type": 1, "components": [{"type": 2, "style": 1, "label": "➕ Nova proposta", "custom_id": "occomp:cid=btn_'"$TIMESTAMP"';mid=mdl_'"$TIMESTAMP"'"}]}
            ]
        }]
    }' | grep -oP '"id":\s*"\K[0-9]+')

if [ -n "$NEW_ID" ] && [ "$NEW_ID" != "null" ]; then
    echo "$NEW_ID" > "$LAST_MESSAGE_FILE"
    echo "✅ Botó regenerat: $NEW_ID"
else
    echo "❌ Error regenerant botó"
fi