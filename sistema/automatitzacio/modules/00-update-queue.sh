#!/bin/bash
# =============================================================================
# 00-update-queue.sh — Actualitzar obra-queue.json i fix-structure
# =============================================================================
# Fase 0 del heartbeat: actualitza l'estat de les obres a obra-queue.json
# i executa fix-structure.sh per auto-correcció d'estructura.
# Fa servir el script Python update_queue_status.py.
# Retorna sempre 0.
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

MODULE_NAME="update-queue"

update_queue_status() {
    log "📋 Actualitzant obra-queue.json..."

    python3 "$PROJECT/sistema/scripts/update_queue_status.py" "$QUEUE" "$PROJECT" 2>/dev/null | while read -r msg; do
        log "   📋 $msg"
    done
    jsonl_log "$MODULE_NAME" "info" "obra-queue.json actualitzat"
}

run_update_queue() {
    update_queue_status
    # Auto-correcció estructura
    bash "$PROJECT/sistema/automatitzacio/fix-structure.sh" 2>/dev/null || true
    return 0
}

# ── Execució independent ────────────────────────────────────────────────────
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    : "${PROJECT:=$HOME/biblioteca-universal-arion}"
    : "${TASKS_DIR:=$PROJECT/sistema/tasks}"
    : "${LOG:=$PROJECT/sistema/logs/heartbeat.log}"
    : "${QUEUE:=$PROJECT/sistema/state/obra-queue.json}"
    export PROJECT TASKS_DIR LOG QUEUE
    run_update_queue
fi
