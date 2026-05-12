#!/bin/bash
# =============================================================================
# send-heartbeat-report.sh — Envia report diari a Discord
# =============================================================================
# S'executa cada dia a les 21:00 UTC via cron
# Utilitza Discord API directament (curl)
# =============================================================================

PROJECT="$HOME/biblioteca-universal-arion"
STATE_FILE="$PROJECT/sistema/state/heartbeat_state.json"
REPORT_FILE="$PROJECT/sistema/state/last_heartbeat_report.md"
LOG_FILE="$PROJECT/sistema/logs/heartbeat.log"

# Carregar Discord token
DISCORD_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" ~/.hermes/.env 2>/dev/null | cut -d'=' -f2)
CHANNEL_ID="1469504522614476953"

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] [REPORT] $1" >> "$LOG_FILE"
}

# Funció per escapar JSON
escape_json() {
    python3 -c "import json; print(json.dumps('''$1'''))" 2>/dev/null
}

# Llegir estat del heartbeat
if [ -f "$STATE_FILE" ]; then
    diem_balance=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('diem_balance', '?'))" 2>/dev/null || echo "?")
    pending_tasks=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('pending_tasks', 0))" 2>/dev/null || echo "0")
    running_tasks=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('running_tasks', 0))" 2>/dev/null || echo "0")
    done_today=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('done_tasks_today', 0))" 2>/dev/null || echo "0")
    failed_tasks=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('failed_tasks', 0))" 2>/dev/null || echo "0")
    validated_works=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('validated_works', 0))" 2>/dev/null || echo "0")
    needs_fix=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('needs_fix_works', 0))" 2>/dev/null || echo "0")
    total_translations=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('total_translations', 0))" 2>/dev/null || echo "0")
    worker_status=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('worker_status', 'DESCONEGUT'))" 2>/dev/null || echo "DESCONEGUT")
    catalog_health=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('catalog_health', '?'))" 2>/dev/null || echo "?")
else
    log "⚠️ No s'ha trobat heartbeat_state.json"
    diem_balance="?"
    pending_tasks=0
    running_tasks=0
    done_today=0
    failed_tasks=0
    validated_works=0
    needs_fix=0
    total_translations=0
    worker_status="DESCONEGUT"
    catalog_health="?"
fi

# Determinar emoji del worker
if [ "$worker_status" = "ACTIVE" ] || [ "$worker_status" = "RUNNING" ]; then
    worker_emoji="🟢"
    worker_text="Actiu"
elif [ "$worker_status" = "IDLE" ]; then
    worker_emoji="🟡"
    worker_text="Inactiu"
else
    worker_emoji="🔴"
    worker_text="Aturat"
fi

# Data i hora (UTC)
now=$(date -u '+%d/%m/%Y %H:%M')

# Construir missatge
message="📊 **BIBLIOTECA UNIVERSAL ARION** — $now
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$worker_emoji **Worker:** $worker_text
💰 **Saldo DIEM:** $diem_balance

## 📈 ACTIVITAT D'AVUI
✅ Completades: $done_today
🔄 En progrés: $running_tasks
📋 Pendents: $pending_tasks
❌ Fallides: $failed_tasks

## 📚 CATÀLEG
📖 Total traduccions: $total_translations
✅ Validades: $validated_works
🔧 Pendents correcció: $needs_fix
📊 Salut del catàleg: $catalog_health"

# Afegir tasca actual si hi ha
if [ -f "$REPORT_FILE" ]; then
    current_task=$(grep -A1 "## 🔄 TASCA ACTUAL" "$REPORT_FILE" 2>/dev/null | tail -1 | sed 's/^[[:space:]]*//')
    if [ -n "$current_task" ] && [ "$current_task" != "⚠️ Cap tasca en execució" ]; then
        message="$message

## 🔄 TASCA ACTUAL
$current_task"
    fi
fi

# Afegir problemes crítics
if [ -f "$STATE_FILE" ]; then
    critical_issues=$(python3 -c "
import json
d = json.load(open('$STATE_FILE'))
issues = d.get('critical_issues', [])
if issues:
    print('\\n'.join(['⚠️ ' + i for i in issues]))
" 2>/dev/null)
    if [ -n "$critical_issues" ]; then
        message="$message

## ⚠️ PROBLEMES
$critical_issues"
    fi
fi

# Enviar via Discord API
if [ -z "$DISCORD_TOKEN" ]; then
    log "❌ DISCORD_BOT_TOKEN no configurat"
    exit 1
fi

escaped_message=$(escape_json "$message")

# Enviar i capturar NOMÉS el codi HTTP (descartar resposta JSON)
http_code=$(curl -s -X POST \
    "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
    -H "Authorization: Bot $DISCORD_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"content\": $escaped_message}" \
    -o /dev/null \
    -w "%{http_code}" 2>/dev/null || echo "000")

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    log "✅ Report diari enviat a Discord (HTTP $http_code)"
else
    log "❌ Error enviant report (HTTP $http_code)"
    exit 1
fi