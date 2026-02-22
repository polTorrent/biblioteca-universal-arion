#!/bin/bash
# Worker mínim - funciona segur
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
LOG="$HOME/claude-worker.log"

source ~/.nvm/nvm.sh 2>/dev/null
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

log "Worker mini iniciat (PID $$)"

while true; do
    # Agafar primera tasca
    TASK=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | head -1)
    
    if [ -z "$TASK" ]; then
        sleep 60
        continue
    fi
    
    TASK_ID=$(python3 -c "import json; print(json.load(open('$TASK'))['id'])")
    INSTRUCTION=$(python3 -c "import json; print(json.load(open('$TASK'))['instruction'])")
    
    log "═══ Executant: $TASK_ID ═══"
    mv "$TASK" "$TASKS_DIR/running/"
    
    # Executar Claude - EXACTAMENT com funciona manualment
    RESULT=$(cd "$PROJECT_DIR" && claude -p "$INSTRUCTION" --max-turns 10 --output-format text 2>&1)
    EXIT=$?
    
    if [ $EXIT -eq 0 ] && [ -n "$RESULT" ]; then
        log "✅ $TASK_ID completat"
        log "Resultat: $(echo "$RESULT" | head -3)"
        mv "$TASKS_DIR/running/$(basename "$TASK")" "$TASKS_DIR/done/"
        
        # Auto-commit si hi ha canvis
        cd "$PROJECT_DIR"
        if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard)" ]; then
            git add -A && git commit -m "auto: $TASK_ID" && git push origin main 2>/dev/null
            log "📤 Auto-commit + push"
        fi
    else
        log "❌ $TASK_ID fallit (exit=$EXIT)"
        mv "$TASKS_DIR/running/$(basename "$TASK")" "$TASKS_DIR/failed/"
    fi
    
    log "⏸️ Cooldown 30s..."
    sleep 30
done
