#!/bin/bash
# =============================================================================
# claude-code-night.sh — Worker nocturn amb subscripció Claude Pro
# =============================================================================
# Funció: Executar tasques Biblioteca Arion amb Claude Code durant la nit
# Franja: 00:00 - 08:00 UTC (quan l'usuari dorm)
# Si s'esgota: cap problema, l'usuari no nota res
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
LOG="$HOME/claude-night.log"
LOCKFILE="/tmp/claude-night.lock"

MAX_RETRIES=2                 # Menys retries (2 en lloc de 3)
MAX_CONSECUTIVE_FAILS=3
COOLDOWN_OK=20                # Menys temps entre tasques (més EFICIENT)
COOLDOWN_FAIL=45
COOLDOWN_EMERGENCY=300        # 5 min pausa emergència (més curt)
CONSECUTIVE_ERRORS_FILE="/tmp/claude-night-errors.txt"
TASK_TIMEOUT=1800             # 30 min per tasca
MAX_RUNTIME=32400             # 9 hores màxim (00:00-09:00 UTC)

# ── Inicialització ────────────────────────────────────────────────────────────
source ~/.nvm/nvm.sh 2>/dev/null
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

START_TIME=$(date +%s)
TODAY=$(date '+%Y-%m-%d')

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CLAUDE-CODE] $1" | tee -a "$LOG"; }

# ── Lockfile ──────────────────────────────────────────────────────────────────
acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log "⛔ Worker nocturn ja actiu (PID $OLD_PID). Sortint."
            exit 1
        else
            log "⚠️ Lockfile orfe (PID $OLD_PID mort). Netejant."
            rm -f "$LOCKFILE"
        fi
    fi
    echo $$ > "$LOCKFILE"
}

release_lock() {
    rm -f "$LOCKFILE"
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "♻️ Retornada a pending: $(basename "$f")"
    done
    log "🛑 Worker nocturn aturat (PID $$)"
}

trap release_lock EXIT INT TERM

# ── Comptador errors consecutius ──────────────────────────────────────────────
load_errors() {
    CONSECUTIVE_FAILS=$(cat "$CONSECUTIVE_ERRORS_FILE" 2>/dev/null || echo 0)
}

save_errors() {
    echo "$CONSECUTIVE_FAILS" > "$CONSECUTIVE_ERRORS_FILE"
}

reset_errors() {
    CONSECUTIVE_FAILS=0
    echo 0 > "$CONSECUTIVE_ERRORS_FILE"
}

# ── JSON helper ───────────────────────────────────────────────────────────────
json_field() {
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$1" "$2" 2>/dev/null
}

# ── Comprovar si encara som dins la franja horària ──────────────────────────────
check_time_window() {
    local now=$(date +%s)
    local elapsed=$((now - START_TIME))
    
    if [ $elapsed -ge $MAX_RUNTIME ]; then
        log "⏰ Franja de 9h completada. Finalitzant."
        return 1
    fi
    return 0
}

# ── Executar tasca amb Claude Code ─────────────────────────────────────────────
run_task() {
    local instruction="$1"
    local result=""
    local exit_code=1
    
    log "🔧 Executant amb Claude Code..."
    
    # Claude Code amb --print mode (no interactiu)
    # --dangerously-skip-permissions per automatització completa
    cd "$PROJECT_DIR"
    
    result=$(timeout "$TASK_TIMEOUT" claude -p "$instruction" \
        --dangerously-skip-permissions \
        --max-turns 30 \
        --output-format text \
        --allowedTools "Read,Edit,Write,Bash" \
        2>&1) || exit_code=$?
    
    echo "$result"
    return $exit_code
}

# ── Auto-commit ────────────────────────────────────────────────────────────────
auto_commit() {
    local task_id="$1"
    cd "$PROJECT_DIR"
    if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        git add -A 2>/dev/null
        git commit -m "[claude-night] $task_id" 2>/dev/null
        git push origin main 2>/dev/null && log "📤 Push OK: $task_id" || log "⚠️ Push fallit"
        return 0
    fi
    return 1
}

# ── Comprovar canvis reals ──────────────────────────────────────────────────────
check_changes() {
    cd "$PROJECT_DIR"
    local changes=$(git diff --name-only 2>/dev/null | wc -l)
    local new_files=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l)
    echo $((changes + new_files))
}

# =============================================================================
# MAIN LOOP
# =============================================================================
acquire_lock
load_errors
log "🌙 Worker nocturn Claude Code iniciat (PID $$)"
log "   Franja: 00:00-09:00 UTC (màxim 9h)"
log "   Projecte: $PROJECT_DIR"

while check_time_window; do
    # Safety: massa errors consecutius
    if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
        log "🛡️ $CONSECUTIVE_FAILS errors consecutius. Pausa ${COOLDOWN_EMERGENCY}s."
        sleep $COOLDOWN_EMERGENCY
        reset_errors
        continue
    fi
    
    # Agafar tasca amb prioritat més alta
    TASK=$(python3 -c "
import json, glob, sys
tasks = []
for f in glob.glob(sys.argv[1] + '/pending/*.json'):
    try:
        with open(f) as fh: d = json.load(fh)
        tasks.append((d.get('priority', 5), f))
    except: pass
if tasks:
    tasks.sort(key=lambda x: x[0])
    print(tasks[0][1])
" "$TASKS_DIR" 2>/dev/null)

    if [ -z "$TASK" ]; then
        log "💤 Sense tasques pendents. Esperant 60s..."
        sleep 60
        continue
    fi
    
    # Llegir tasca
    TASK_ID=$(json_field "$TASK" "id")
    INSTRUCTION=$(json_field "$TASK" "instruction")
    TASK_TYPE=$(json_field "$TASK" "type")
    RETRIES=$(json_field "$TASK" "retries")
    RETRIES=${RETRIES:-0}
    TASK_TYPE=${TASK_TYPE:-unknown}
    
    if [ -z "$TASK_ID" ] || [ -z "$INSTRUCTION" ]; then
        log "⚠️ Tasca malformada. Movent a failed/"
        mv "$TASK" "$TASKS_DIR/failed/"
        continue
    fi
    
    TASK_BASENAME=$(basename "$TASK")
    log "═══════════════════════════════════════════════════"
    log "▶ Executant: $TASK_ID (tipus=$TASK_TYPE, intent $((RETRIES + 1))/$MAX_RETRIES)"
    
    # Moure a running
    if ! mv -n "$TASK" "$TASKS_DIR/running/$TASK_BASENAME" 2>/dev/null; then
        log "⚠️ No s'ha pogut moure la tasca. Saltant."
        continue
    fi
    
    START_TASK=$(date +%s)
    
    # Executar
    RESULT=$(run_task "$INSTRUCTION")
    EXIT=$?
    END_TASK=$(date +%s)
    DURATION=$((END_TASK - START_TASK))
    
    # Comprovar resultats
    if [ $EXIT -eq 0 ]; then
        CHANGES=$(check_changes)
        
        if [ "$CHANGES" -gt 0 ]; then
            log "✅ $TASK_ID completat (${DURATION}s, $CHANGES fitxers canviats)"
            log "   Resultat: $(echo "$RESULT" | head -3 | tr '\n' ' ')"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            reset_errors
            sleep $COOLDOWN_OK
        else
            log "⚠️ $TASK_ID: Sense canvis reals (${DURATION}s)"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_errors
            sleep $COOLDOWN_FAIL
        fi
    elif [ $EXIT -eq 124 ]; then
        log "⏰ TIMEOUT ${TASK_TIMEOUT}s per $TASK_ID"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        sleep $COOLDOWN_FAIL
    else
        log "❌ $TASK_ID fallit (exit=$EXIT, ${DURATION}s)"
        
        RETRIES_NOW=$((RETRIES + 1))
        if [ $RETRIES_NOW -lt $MAX_RETRIES ]; then
            log "   🔄 Retry $RETRIES_NOW/$MAX_RETRIES"
            python3 -c "
import json
f = '$TASKS_DIR/running/$TASK_BASENAME'
with open(f) as fh: d = json.load(fh)
d['retries'] = $RETRIES_NOW
with open(f, 'w') as fh: json.dump(d, fh, indent=2)
" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        else
            log "   ❌ Màxim de retries. Movent a failed/"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_errors
        fi
        sleep $COOLDOWN_FAIL
    fi
done

log "🌙 Franja horària completada. Finalitzant."
exit 0