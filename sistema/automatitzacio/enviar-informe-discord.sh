#!/bin/bash
# Envia informe manual a Discord biblioteca-arion

PROJECT="$HOME/biblioteca-universal-arion"
STATE_FILE="$PROJECT/sistema/state/heartbeat_state.json"

# Token de Discord
DISCORD_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" ~/.hermes/.env 2>/dev/null | cut -d'=' -f2)
CHANNEL_ID="1469504522614476953"

if [ -z "$DISCORD_TOKEN" ]; then
    echo "❌ Token no configurat"
    exit 1
fi

# Llegir estat
if [ -f "$STATE_FILE" ]; then
    diem=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('diem_balance', '?'))" 2>/dev/null || echo "?")
    pending=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('pending_tasks', 0))" 2>/dev/null || echo "0")
    running=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('running_tasks', 0))" 2>/dev/null || echo "0")
    done_today=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('done_tasks_today', 0))" 2>/dev/null || echo "0")
else
    diem="?"
    pending="0"
    running="0"
    done_today="0"
fi

# Comptar tasques reals
pending_real=$(ls -1 "$PROJECT/sistema/tasks/pending/"*.json 2>/dev/null | wc -l)
running_real=$(ls -1 "$PROJECT/sistema/tasks/running/"*.json 2>/dev/null | wc -l)

# Comptar obres per estat
validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
needs_fix=$(find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | wc -l)
incomplete=$($PROJECT/sistema/automatitzacio/detectar-incompletes.sh 2>/dev/null | grep "Total tasques creades" | awk '{print $4}')

# Data
now=$(date -u '+%d/%m/%Y %H:%M')

# Missatge
message="📊 **BIBLIOTECA UNIVERSAL ARION** — $now UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 **Worker:** Actiu i processant
💰 **Saldo DIEM:** $diem

## 📈 ACTIVITAT D'AVUI
✅ Completades: $done_today
🔄 En progrés: $running_real
📋 Pendents: $pending_real

## 📚 CATÀLEG
📖 Total obres: ~100
✅ Validades: $validated
🔧 Pendents correcció: $needs_fix
⚠️ Incompletes detectades: 9

## 🆕 NOVETATS
🎯 **Detector V2 actiu**: Comparant originals vs traduccions
📊 Obres amb <30% traduït → Tasques de completar
📚 'Sobre l'ànima' reoberta (48% completat)
🔧 Prioritat: justine (7%), masnavi (8%), menschliches (14%)

## 🔗 DASHBOARD
http://100.93.26.104:9120 (TailScale)"

# Enviar
escaped=$(python3 -c "import json; print(json.dumps('''$message'''))")

http_code=$(curl -s -X POST \
    "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
    -H "Authorization: Bot $DISCORD_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"content\": $escaped}" \
    -w "%{http_code}" \
    -o /dev/null 2>/dev/null)

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "✅ Informe enviat a Discord (HTTP $http_code)"
else
    echo "❌ Error enviant informe (HTTP $http_code)"
fi