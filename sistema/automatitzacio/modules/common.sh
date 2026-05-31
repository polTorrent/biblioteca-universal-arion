#!/bin/bash
# ═══════════════════════════════════════════════════════════
# common.sh — Funcions compartides pels mòduls del heartbeat
# ═══════════════════════════════════════════════════════════

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HEARTBEAT] $1" | tee -a "$LOG"; }

log_json() {
    local type="$1" msg="$2"
    echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"module\":\"${MODULE_NAME:-unknown}\",\"type\":\"$type\",\"msg\":\"$msg\"}" >> "${LOG%/*}/heartbeat.jsonl"
}

count_pending() { ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l; }
count_running() { ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l; }

task_exists() {
    local keyword="$1"
    # Escapem les barres verticals i forcem que només busqui sobre fitxers existents reals a pending o running d'una forma completament compatible sense dependre del comportament d'error de xargs que faria saltar el grep cap al seu codi modificat
    local files=$(find "$TASKS_DIR/pending/" "$TASKS_DIR/running/" -type f 2>/dev/null)
    if [ -n "$files" ]; then
        grep -lE "$keyword" $files 2>/dev/null | head -1
    else
        echo ""
    fi
}

add_task() {
    local type="$1" instruction="$2"
    [ "$(count_pending)" -ge "$MAX_PENDING" ] && return 1
    bash "$TASK_MANAGER" add "$type" "$instruction" 2>/dev/null
    log "   ➕ [$type]: $(echo "$instruction" | head -c 80)..."
    return 0
}
