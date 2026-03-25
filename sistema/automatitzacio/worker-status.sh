#!/bin/bash
# =============================================================================
# worker-status.sh — Estat ràpid del sistema worker
# =============================================================================
# Ús: bash sistema/automatitzacio/worker-status.sh
# =============================================================================

TASKS_DIR="$HOME/.openclaw/workspace/tasks"
LOG="$HOME/claude-worker.log"
LOCKFILE="$TASKS_DIR/worker.lock"

# Colors
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; B='\033[0;34m'; NC='\033[0m'

echo ""
echo -e "${B}═══ ESTAT SISTEMA WORKER ═══${NC}"
echo ""

# Worker actiu?
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "Worker:   ${G}✅ ACTIU${NC} (PID $PID)"
    else
        echo -e "Worker:   ${R}❌ MORT${NC} (lockfile orfe, PID $PID)"
    fi
else
    echo -e "Worker:   ${Y}⏸️ ATURAT${NC} (sense lockfile)"
fi

# Cues
PENDING=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
RUNNING=$(ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)
DONE_TODAY=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
DONE_TOTAL=$(ls -1 "$TASKS_DIR/done/"*.json 2>/dev/null | wc -l)
FAILED_TOTAL=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)

echo ""
echo -e "Pending:  ${Y}$PENDING${NC}"
echo -e "Running:  ${B}$RUNNING${NC}"
echo -e "Done avui:${G}$DONE_TODAY${NC} (total: $DONE_TOTAL)"
echo -e "Failed:   ${R}$FAILED_TOTAL${NC}"

# Última activitat
if [ -f "$LOG" ]; then
    echo ""
    echo -e "${B}── Últimes 5 línies del log ──${NC}"
    tail -5 "$LOG"
fi

# Tasques pending (si n'hi ha)
if [ "$PENDING" -gt 0 ]; then
    echo ""
    echo -e "${B}── Tasques pendents ──${NC}"
    for f in "$TASKS_DIR/pending/"*.json; do
        [ -f "$f" ] || continue
        ID=$(python3 -c "import json; print(json.load(open('$f')).get('id','?'))" 2>/dev/null)
        RETRIES=$(python3 -c "import json; print(json.load(open('$f')).get('retries',0))" 2>/dev/null)
        echo "  - $ID (retries: $RETRIES)"
    done
fi

# Tasques failed recents
if [ "$FAILED_TOTAL" -gt 0 ]; then
    echo ""
    echo -e "${B}── Últimes tasques fallides ──${NC}"
    ls -1t "$TASKS_DIR/failed/"*.json 2>/dev/null | head -3 | while read -r f; do
        ID=$(python3 -c "import json; print(json.load(open('$f')).get('id','?'))" 2>/dev/null)
        RETRIES=$(python3 -c "import json; print(json.load(open('$f')).get('retries',0))" 2>/dev/null)
        echo -e "  - ${R}$ID${NC} ($RETRIES intents)"
    done
fi

echo ""
