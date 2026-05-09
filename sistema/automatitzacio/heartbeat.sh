#!/bin/bash
# =============================================================================
# heartbeat.sh v6 — Orchestrador modular (refactoritzat de v5 monolítica)
# =============================================================================
set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
export PROJECT="$HOME/biblioteca-universal-arion"
export TASKS_DIR="$PROJECT/sistema/tasks"
export LOG="$PROJECT/sistema/logs/heartbeat.log"
export TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
export MAX_PENDING=5
export MIN_DIEM_RESERVE=3

MODULES_DIR="$PROJECT/sistema/automatitzacio/modules"

# ── Carregar System Brain (deduplicació) ────────────────────────────────────
BRAIN_SCRIPT="$PROJECT/sistema/automatitzacio/system-brain.sh"
BRAIN_LOADED=false
[ -f "$BRAIN_SCRIPT" ] && source "$BRAIN_SCRIPT" && BRAIN_LOADED=true

# ── Comprovació de pausa ─────────────────────────────────────────────────────
PAUSE_FILE="$PROJECT/PAUSE"
if [ -f "$PAUSE_FILE" ]; then
    PAUSED_UNTIL=$(grep "PAUSED_UNTIL=" "$PAUSE_FILE" 2>/dev/null | cut -d'=' -f2)
    TODAY=$(date '+%Y-%m-%d')
    [ -n "$PAUSED_UNTIL" ] && [[ "$TODAY" < "$PAUSED_UNTIL" ]] && echo "⏸️ Pausa activa fins $PAUSED_UNTIL" && exit 0
fi

# ── Logging ──────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HEARTBEAT] $1" | tee -a "$LOG"; }
mkdir -p "$TASKS_DIR"/{pending,running,done,failed,failed_permanent} "$PROJECT/sistema/logs" "$PROJECT/sistema/state"

log "═══════════════════════════════════════════════════"
log "💓 HEARTBEAT v6 iniciat (modular)"
[ "$BRAIN_LOADED" = true ] && log "🧠 System Brain carregat" || log "⚠️ System Brain NO disponible"

# ── Fase 0: Comprovacions crítiques ──────────────────────────────────────────
bash "$MODULES_DIR/01-check-diem.sh" || { log "⛔ DIEM insuficient. Aturant."; exit 0; }
bash "$MODULES_DIR/02-check-worker.sh"

# ── Estat ─────────────────────────────────────────────────────────────────────
PENDING=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
RUNNING=$(ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)
DONE_TODAY=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
FAILED=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)
log "📊 Estat: $PENDING pendents, $RUNNING running, $DONE_TODAY done avui, $FAILED fallides"

# ── Fase 1: Auditoria i recuperació ──────────────────────────────────────────
bash "$PROJECT/sistema/automatitzacio/fix-structure.sh" 2>/dev/null || true
bash "$MODULES_DIR/03-check-failed.sh"
bash "$MODULES_DIR/04-check-needs-fix.sh"
bash "$MODULES_DIR/09-audit-catalog.sh"

# ── Fase 2: Generació de tasques (si hi ha espai) ────────────────────────────
if [ "$PENDING" -ge "$MAX_PENDING" ]; then
    log "✅ Cua plena ($PENDING). Saltant generació."
else
    bash "$MODULES_DIR/05-check-supervision.sh"
    bash "$MODULES_DIR/06-check-translations.sh"
    bash "$MODULES_DIR/07-check-web-sync.sh"
fi

# ── Fase 3: Manteniment i report ─────────────────────────────────────────────
bash "$MODULES_DIR/08-check-maintenance.sh"
bash "$MODULES_DIR/10-generate-report.sh"

PENDING_FINAL=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
log "💓 HEARTBEAT v6 completat. Cua: $PENDING → $PENDING_FINAL pendents"
log "═══════════════════════════════════════════════════"
