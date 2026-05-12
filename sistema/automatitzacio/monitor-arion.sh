#!/bin/bash
# monitor-arion.sh — Monitoritza l'estat del sistema cada 15 minuts
# Genera alertes només quan hi ha problemes detectats

PROJECT="$HOME/biblioteca-universal-arion"
STATE_DIR="$PROJECT/sistema/state"
ALERT_FILE="$STATE_DIR/monitor_alerts.json"
STATUS_FILE="$STATE_DIR/monitor_status.json"
LOG="$PROJECT/sistema/logs/monitor.log"

mkdir -p "$STATE_DIR"

timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
alerts=()
status="OK"
severity="info"

# 1. Comprovar worker actiu
worker_pids=$(pgrep -f "worker.sh" | tr '\n' ' ' | sed 's/ $//')
if [ -z "$worker_pids" ]; then
    alerts+=("Worker ATURAT — cap procés actiu")
    status="CRITICAL"
    severity="critical"
fi

# 2. Comprovar tasques orfes (running sense canvi >45 min)
orphaned=0
if [ -d "$PROJECT/sistema/tasks/running" ]; then
    for f in "$PROJECT/sistema/tasks/running/"*.json; do
        [ -f "$f" ] || continue
        age_min=$(( ($(date +%s) - $(stat -c %Y "$f" 2>/dev/null || echo 0)) / 60 ))
        if [ "$age_min" -gt 45 ]; then
            orphaned=$((orphaned + 1))
        fi
    done
fi
if [ "$orphaned" -gt 0 ]; then
    alerts+=("$orphaned tasques ORFES a running (>45 min sense activitat)")
    [ "$status" != "CRITICAL" ] && status="WARNING"
    [ "$severity" != "critical" ] && severity="warning"
fi

# 3. Comprovar DIEM (via venice CLI)
diems="?"
VENICE_CLI="$HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py"
if [ -f "$VENICE_CLI" ]; then
    diems=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
fi
if [ -n "$diems" ] && [ "$diems" != "?" ]; then
    is_low=$(python3 -c "print('yes' if float('$diems') < 3.0 else 'no')" 2>/dev/null)
    if [ "$is_low" = "yes" ]; then
        alerts+=("DIEM CRÍTIC: $diems (mínim: 3.0)")
        [ "$status" != "CRITICAL" ] && status="WARNING"
        [ "$severity" != "critical" ] && severity="warning"
    fi
fi

# 4. Comprovar errors al log recent (>10 errors en última hora)
error_count=0
if [ -f "$PROJECT/sistema/logs/heartbeat.log" ]; then
    error_count=$(grep -cE "ERROR|❌|FAIL" "$PROJECT/sistema/logs/heartbeat.log" 2>/dev/null || echo 0)
fi
if [ "$error_count" -gt 20 ]; then
    alerts+=("$error_count errors acumulats al log")
    [ "$status" != "CRITICAL" ] && status="WARNING"
    [ "$severity" != "critical" ] && severity="warning"
fi

# 5. Comprovar done avui vs running (si 0 done en 2h i worker actiu, pot estar atascat)
done_today=$(find "$PROJECT/sistema/tasks/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
if [ "$done_today" -eq 0 ] && [ -n "$worker_pids" ]; then
    # Només alerta si ja porta >90 min actiu i 0 done
    worker_age=0
    for pid in $worker_pids; do
        age_sec=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$age_sec" ] && [ "$age_sec" -gt 5400 ]; then
            worker_age=$age_sec
            break
        fi
    done
    if [ "$worker_age" -gt 5400 ]; then
        alerts+=("Worker actiu des de 90+ min però 0 tasques completades avui — possible bloqueig")
        [ "$status" != "CRITICAL" ] && status="WARNING"
        [ "$severity" != "critical" ] && severity="warning"
    fi
fi

# 6. Comprovar pending excessiu
pending=$(ls -1 "$PROJECT/sistema/tasks/pending/"*.json 2>/dev/null | wc -l)
if [ "$pending" -gt 100 ]; then
    alerts+=("Cua MASSIVA: $pending tasques pendents")
    [ "$status" != "CRITICAL" ] && status="WARNING"
fi

# Generar JSON d'estat
python3 -c "
import json, datetime
state = {
    'timestamp': '$timestamp',
    'status': '$status',
    'severity': '$severity',
    'worker_pids': '$worker_pids',
    'diem': '$diems',
    'done_today': $done_today,
    'pending': $pending,
    'orphaned': $orphaned,
    'alerts': $(python3 -c "import json; print(json.dumps(${alerts[@]:+"$(printf '%s\n' "${alerts[@]}")"}))" 2>/dev/null || echo '[]')
}
with open('$STATUS_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null

# Si hi ha alertes, guardar-les
if [ ${#alerts[@]} -gt 0 ]; then
    python3 -c "
import json, datetime
alert_data = {
    'timestamp': '$timestamp',
    'status': '$status',
    'severity': '$severity',
    'alerts': $(python3 -c "import json; alerts='''$(printf '%s\n' "${alerts[@]}")'''; print(json.dumps(alerts.strip().split('\n')))" 2>/dev/null || echo '[]')
}
with open('$ALERT_FILE', 'w') as f:
    json.dump(alert_data, f, indent=2)
" 2>/dev/null
    echo "[$timestamp] [$severity] ALERTES: ${alerts[*]}" >> "$LOG"
else
    # Netejar alertes si tot va bé
    rm -f "$ALERT_FILE"
    echo "[$timestamp] [info] Estat OK — Worker: $worker_pids | DIEM: $diems | Done: $done_today | Pending: $pending" >> "$LOG"
fi
