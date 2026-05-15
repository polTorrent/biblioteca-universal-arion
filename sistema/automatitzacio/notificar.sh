#!/bin/bash
# =============================================================================
# notificar.sh — Notificacions unificades per Biblioteca Arion
# Reemplaça: notificar.sh, notificar-usuari.sh, enviar-informe-discord.sh,
#            send-heartbeat-report.sh
# =============================================================================
set -uo pipefail

PROJECT="$HOME/biblioteca-universal-arion"

# Carregar Discord token
DISCORD_BOT_TOKEN=""
DISCORD_CHANNEL=""
[ -f "$PROJECT/.env" ] && { DISCORD_BOT_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" "$PROJECT/.env" | head -1 | cut -d'"' -f2); }
[ -z "$DISCORD_BOT_TOKEN" ] && DISCORD_BOT_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" "$HOME/.hermes/.env" 2>/dev/null | head -1 | cut -d'"' -f2)
DISCORD_CHANNEL="1469504522614476953"  # Canal Biblioteca Arion

DISCORD_WEBHOOK=$(cat "$PROJECT/sistema/config/discord_webhook.txt" 2>/dev/null)
LAST_NOTIF_FILE="/tmp/arion-last-notif"
RATE_LIMIT_SECONDS=60

# ── Nivells de severitat ─────────────────────────────────────────────────────
SEVERITY_LOW=0      # Info, stats
SEVERITY_MEDIUM=1   # Advertències, tasques fallides
SEVERITY_HIGH=2     # Errors crítics, DIEM baix
SEVERITY_CRITICAL=3 # Worker aturat, emergència

# ── Rate limiting ────────────────────────────────────────────────────────────
can_notify() {
    local severity="$1"
    # CRITICAL sempre passa
    [ "$severity" -ge "$SEVERITY_CRITICAL" ] && return 0
    
    local now=$(date +%s)
    if [ -f "$LAST_NOTIF_FILE" ]; then
        local last=$(cat "$LAST_NOTIF_FILE")
        local diff=$((now - last))
        # Més severitat = menys cooldown
        local min_interval=$RATE_LIMIT_SECONDS
        [ "$severity" -ge "$SEVERITY_HIGH" ] && min_interval=30
        [ "$severity" -ge "$SEVERITY_MEDIUM" ] && min_interval=45
        [ "$diff" -lt "$min_interval" ] && return 1
    fi
    echo "$now" > "$LAST_NOTIF_FILE"
    return 0
}

# ── Emoji per severitat ──────────────────────────────────────────────────────
severity_emoji() {
    case "$1" in
        0) echo "ℹ️" ;;
        1) echo "⚠️" ;;
        2) echo "🔴" ;;
        3) echo "🚨" ;;
        *) echo "📢" ;;
    esac
}

# ── Enviar a Discord ─────────────────────────────────────────────────────────
send_discord() {
    local message="$1"
    # Intentar amb webhook primer
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -s -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"content\":\"$message\"}" > /dev/null 2>&1
        return $?
    fi
    # Fallback: usar Discord Bot API
    if [ -n "$DISCORD_BOT_TOKEN" ] && [ -n "$DISCORD_CHANNEL" ]; then
        local escaped=$(python3 -c "import json; print(json.dumps('''$message'''))" 2>/dev/null)
        [ -z "$escaped" ] && escaped="$message"
        curl -s -X POST \
            "https://discord.com/api/v10/channels/$DISCORD_CHANNEL/messages" \
            -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"content\":$escaped}" > /dev/null 2>&1
        return $?
    fi
    return 1
}

# ── Enviar a Hermes (reenvia a totes les plataformes) ────────────────────────
send_hermes() {
    local message="$1"
    # Utilitzar el bridge d'Hermes si disponible
    if command -v hermes &> /dev/null; then
        hermes notify "$message" 2>/dev/null
        return $?
    fi
    return 1
}

# ── Funció principal ─────────────────────────────────────────────────────────
notify() {
    local severity="${1:-0}"
    local title="$2"
    local message="$3"
    
    can_notify "$severity" || return 0
    
    local emoji=$(severity_emoji "$severity")
    local full_message="$emoji **$title**: $message"
    
    # Log local
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$emoji $title] $message" >> "$PROJECT/sistema/logs/notifications.log"
    
    # Intentar Discord
    send_discord "$full_message" && return 0
    
    # Fallback a Hermes
    send_hermes "$full_message" && return 0
    
    # Si tot falla, només log
    return 1
}

# ── Shortcuts ─────────────────────────────────────────────────────────────────
notify_info()     { notify 0 "${1:-}" "${2:-}"; }
notify_warning()  { notify 1 "${1:-}" "${2:-}"; }
notify_error()    { notify 2 "${1:-}" "${2:-}"; }
notify_critical() { notify 3 "${1:-}" "${2:-}"; }

# ── Report del heartbeat ─────────────────────────────────────────────────────
send_heartbeat_report() {
    local validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
    local needs_fix=$(find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | wc -l)
    local total_trad=$(find "$PROJECT/obres" -name "traduccio.md" 2>/dev/null | wc -l)
    local pending=$(ls -1 "$PROJECT/sistema/tasks/pending/"*.json 2>/dev/null | wc -l)
    local done_today=$(find "$PROJECT/sistema/tasks/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
    local worker_status="❌ INACTIU"
    pgrep -f "worker" > /dev/null 2>&1 && worker_status="✅ ACTIU"
    local diem=$(python3 "$HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    
    local report="💓 **Heartbeat Arion** — $(date '+%H:%M %d/%m')
📊 Traduccions: $total_trad total | $validated validades | $needs_fix pendents
⚙️ Worker: $worker_status | $done_today tasques avui | $pending cua
💰 DIEM: ${diem:-?}"
    
    notify 0 "Heartbeat" "$report"
}

# ── CLI ──────────────────────────────────────────────────────────────────────
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        info)     shift; notify_info "$@" ;;
        warning)  shift; notify_warning "$@" ;;
        error)    shift; notify_error "$@" ;;
        critical) shift; notify_critical "$@" ;;
        report)   send_heartbeat_report ;;
        *)        echo "Ús: notificar.sh [info|warning|error|critical|report] <títol> <missatge>" ;;
    esac
fi
