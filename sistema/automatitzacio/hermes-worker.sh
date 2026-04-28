#!/bin/bash
# =============================================================================
# hermes-worker.sh — Worker nocturn per Biblioteca Arion amb Hermes delegate_task
# =============================================================================
# Funció: Executar tasques pendents utilitzant Hermes com a agent executor
# Franja: 00:00 - 09:00 UTC (quan l'usuari dorm)
# Avantatge: Hermes té accés a totes les eines (terminal, file, patch, web, etc.)
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
LOG="$HOME/hermes-worker.log"
LOCKFILE="/tmp/hermes-worker.lock"

MAX_RETRIES=2
MAX_CONSECUTIVE_FAILS=3
COOLDOWN_OK=30
COOLDOWN_FAIL=60
COOLDOWN_EMERGENCY=300
CONSECUTIVE_ERRORS_FILE="/tmp/hermes-worker-errors.txt"
TASK_TIMEOUT=1800
MAX_RUNTIME=32400  # 9 hores

# ── Inicialització ──────────────────────────────────────────────────────────────
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

START_TIME=$(date +%s)
TODAY=$(date '+%Y-%m-%d')

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HERMES] $1" | tee -a "$LOG"; }

# ── Lockfile ────────────────────────────────────────────────────────────────────
acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log "Worker ja actiu (PID $OLD_PID). Sortint."
            exit 1
        else
            log "Lockfile orfe. Netejant."
            rm -f "$LOCKFILE"
        fi
    fi
    echo $$ > "$LOCKFILE"
}

release_lock() {
    rm -f "$LOCKFILE"
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "Retornada a pending: $(basename "$f")"
    done
    log "Worker aturat (PID $$)"
}

trap release_lock EXIT INT TERM

# ── Comptador errors consecutius ────────────────────────────────────────────────
load_errors() { CONSECUTIVE_FAILS=$(cat "$CONSECUTIVE_ERRORS_FILE" 2>/dev/null || echo 0); }
save_errors() { echo "$CONSECUTIVE_FAILS" > "$CONSECUTIVE_ERRORS_FILE"; }
reset_errors() { CONSECUTIVE_FAILS=0; echo 0 > "$CONSECUTIVE_ERRORS_FILE"; }

# ── JSON helper ───────────────────────────────────────────────────────────────────
json_field() {
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$1" "$2" 2>/dev/null
}

# ── Comprovar franja horària ──────────────────────────────────────────────────────
check_time_window() {
    local now=$(date +%s)
    local elapsed=$((now - START_TIME))
    if [ $elapsed -ge $MAX_RUNTIME ]; then
        log "Franja de 9h completada. Finalitzant."
        return 1
    fi
    return 0
}

# ── Executar tasca amb Hermes Executor ──────────────────────────────────────────
run_task_with_hermes() {
    local task_file="$1"
    local task_id=$(json_field "$task_file" "id")
    local task_type=$(json_field "$task_file" "type")
    local obra_path=$(json_field "$task_file" "obra_path")
    local instruction=$(json_field "$task_file" "instruction")
    
    log "Executant amb Hermes executor..."
    log "   Tasca: $task_type"
    log "   Obra: $obra_path"
    
    cd "$PROJECT_DIR"
    
    # executar l'script Python amb totes les eines disponibles
    local executor="$PROJECT_DIR/sistema/automatitzacio/hermes_task_executor.py"
    
    if [ ! -f "$executor" ]; then
        log "ERROR: Executor no trobat: $executor"
        return 1
    fi
    
    timeout "$TASK_TIMEOUT" python3 "$executor" "$task_file" 2>&1
    local exit_code=$?
    
    return $exit_code
}

# ── Auto-commit ──────────────────────────────────────────────────────────────────
auto_commit() {
    local task_id="$1"
    cd "$PROJECT_DIR"
    if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        git add -A 2>/dev/null
        git commit -m "[hermes-worker] $task_id" 2>/dev/null
        git push origin main 2>/dev/null && log "Push OK: $task_id" || log "Push fallit"
        return 0
    fi
    return 1
}

# ── Comprovar canvis ──────────────────────────────────────────────────────────────
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
log "Worker Hermes iniciat (PID $$)"
log "   Franja: 00:00-09:00 UTC (màxim 9h)"
log "   Projecte: $PROJECT_DIR"

while check_time_window; do
    # Safety: massa errors consecutius
    if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
        log "ERROR: $CONSECUTIVE_FAILS errors consecutius. Pausa ${COOLDOWN_EMERGENCY}s."
        sleep $COOLDOWN_EMERGENCY
        reset_errors
        continue
    fi
    
    # Agafar tasca amb prioritat mésalta
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
        log "Sense tasques pendents. Esperant 60s..."
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
    
    if [ -z "$TASK_ID" ]; then
        log "Tasca malformada. Movent a failed/"
        mv "$TASK" "$TASKS_DIR/failed/"
        continue
    fi
    
    TASK_BASENAME=$(basename "$TASK")
    log "=================================================="
    log "EXECUTANT: $TASK_ID (tipus=$TASK_TYPE, intent $((RETRIES + 1))/$MAX_RETRIES)"
    log "   Instrucció: ${INSTRUCTION:0:100}..."
    
    # Moure a running
    if ! mv -n "$TASK" "$TASKS_DIR/running/$TASK_BASENAME" 2>/dev/null; then
        log "No s'ha pogut moure la tasca. Saltant."
        continue
    fi
    
    START_TASK=$(date +%s)
    
    # Executar amb Hermes
    RESULT=$(run_task_with_hermes "$TASKS_DIR/running/$TASK_BASENAME")
    EXIT=$?
    END_TASK=$(date +%s)
    DURATION=$((END_TASK - START_TASK))
    
    # Comprovar resultats
    if [ $EXIT -eq 0 ]; then
        CHANGES=$(check_changes)
        
        if [ "$CHANGES" -gt 0 ]; then
            log "SUCCESS: $TASK_ID completat (${DURATION}s, $CHANGES fitxers canviats)"
            log "   Resultat: $(echo "$RESULT" | head -3 | tr '\n' ' ')"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            reset_errors
            sleep $COOLDOWN_OK
        else
            log "WARNING: $TASK_IDSense canvis (${DURATION}s)"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_errors
            sleep $COOLDOWN_FAIL
        fi
    elif [ $EXIT -eq 124 ]; then
        log "TIMEOUT ${TASK_TIMEOUT}s per $TASK_ID"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        sleep $COOLDOWN_FAIL
    else
        log "ERROR: $TASK_ID fallit (exit=$EXIT, ${DURATION}s)"
        
        RETRIES_NOW=$((RETRIES + 1))
        if [ $RETRIES_NOW -lt $MAX_RETRIES ]; then
            log "   Retry $RETRIES_NOW/$MAX_RETRIES"
            python3 -c "
import json
f = '$TASKS_DIR/running/$TASK_BASENAME'
with open(f) as fh: d = json.load(fh)
d['retries'] = $RETRIES_NOW
with open(f, 'w') as fh: json.dump(d, fh, indent=2)
" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        else
            log "   Màxim de retries. Movent a failed/"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_errors
        fi
        sleep $COOLDOWN_FAIL
    fi
done

log "Franja horària completada. Finalitzant."
exit 0