#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# claude-worker.sh — Worker autònom de la Biblioteca Arion
# Processa tasques de la cua, executa Opus 4.6, auto-commit+push
# ═══════════════════════════════════════════════════════════════

set -uo pipefail

# ── Config ──────────────────────────────────────────────────
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
LOG_FILE="$HOME/claude-worker.log"
REPORT_FILE="/tmp/claude-worker-report.txt"
STATUS_FILE="/tmp/claude-worker-status.txt"
LOCK_FILE="$TASKS_DIR/worker.lock"

# Safety limits
MAX_TASKS_PER_DAY=20
MAX_CONSECUTIVE_FAILS=3
MAX_COMMITS_PER_HOUR=5
COOLDOWN_SECONDS=60
MAX_TASK_MINUTES=30
MAX_WORKER_HOURS=8

# Counters
TASKS_TODAY=0
CONSECUTIVE_FAILS=0
COMMITS_THIS_HOUR=0
HOUR_START=$(date +%s)
WORKER_START=$(date +%s)

# ── Funcions auxiliars ──────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

report() {
    echo "$1" >> "$REPORT_FILE"
    log "REPORT: $1"
}

set_status() {
    echo "$1" > "$STATUS_FILE"
}

# Cleanup on exit
cleanup() {
    rm -f "$LOCK_FILE"
    set_status "STOPPED"
    log "Worker aturat"
}
trap cleanup EXIT

# Check if another worker is running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
            log "ERROR: Ja hi ha un worker corrent (PID $OLD_PID)"
            exit 1
        else
            log "WARN: Lock file obsolet, eliminant"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# Reset hourly commit counter
check_hourly_reset() {
    local now=$(date +%s)
    local elapsed=$(( now - HOUR_START ))
    if [ $elapsed -ge 3600 ]; then
        COMMITS_THIS_HOUR=0
        HOUR_START=$now
    fi
}

# Check if worker should stop
check_runtime() {
    local now=$(date +%s)
    local elapsed=$(( now - WORKER_START ))
    local max_seconds=$(( MAX_WORKER_HOURS * 3600 ))
    if [ $elapsed -ge $max_seconds ]; then
        log "Worker ha arribat al límit de $MAX_WORKER_HOURS hores. Reiniciant..."
        return 1
    fi
    return 0
}

# ── Gestió de la cua ───────────────────────────────────────

# Obtenir la propera tasca (per prioritat, després FIFO)
get_next_task() {
    local best_file=""
    local best_priority=999

    for f in "$TASKS_DIR/pending/"*.json; do
        [ -f "$f" ] || continue
        local priority
        priority=$(python3 -c "import json; print(json.load(open('$f'))['priority'])" 2>/dev/null || echo 999)
        if [ "$priority" -lt "$best_priority" ]; then
            best_priority=$priority
            best_file=$f
        elif [ "$priority" -eq "$best_priority" ]; then
            # FIFO: el primer per timestamp (ja està al nom)
            if [ -z "$best_file" ] || [[ "$f" < "$best_file" ]]; then
                best_file=$f
            fi
        fi
    done

    echo "$best_file"
}

# Moure tasca entre directoris
move_task() {
    local file="$1"
    local dest="$2"
    local basename
    basename=$(basename "$file")
    mv "$file" "$TASKS_DIR/$dest/$basename"
    echo "$TASKS_DIR/$dest/$basename"
}

# Actualitzar camp d'una tasca
update_task() {
    local file="$1"
    local field="$2"
    local value="$3"
    python3 -c "
import json
with open('$file', 'r') as f:
    task = json.load(f)
task['$field'] = $value
with open('$file', 'w') as f:
    json.dump(task, f, indent=2, ensure_ascii=False)
" 2>/dev/null
}

# ── Construir instrucció per Opus ──────────────────────────

build_instruction() {
    local task_file="$1"
    local instruction_file="$2"

    python3 - "$task_file" "$instruction_file" << 'PYEOF'
import json
import sys

task_file = sys.argv[1]
output_file = sys.argv[2]

with open(task_file, 'r') as f:
    task = json.load(f)

task_type = task['type']
instruction = task.get('instruction', '')
params = task.get('params', {})

# Prefix segons tipus
prefixes = {
    'fix': 'URGENT FIX: ',
    'test': 'EXECUTAR TESTS: ',
    'code-review': 'REVISIÓ DE CODI: ',
    'translate': 'TRADUCCIÓ COMPLETA: ',
    'refactor': 'REFACTORING: ',
    'maintain': 'MANTENIMENT: ',
}

prefix = prefixes.get(task_type, '')

# Suffix comú
suffix = """

INSTRUCCIONS GENERALS:
- Treballa dins ~/biblioteca-universal-arion
- Si fas canvis a codi, executa els tests relacionats
- Si tot funciona, fes git add + git commit amb missatge descriptiu + git push
- Reporta el resultat final de forma concisa
- Si trobes un error que no pots resoldre, descriu-lo clarament
"""

# Suffix específic per traduccions
if task_type == 'translate':
    autor = params.get('autor', '')
    titol = params.get('titol', '')
    llengua = params.get('llengua', '')
    categoria = params.get('categoria', '')
    suffix = f"""

INSTRUCCIONS PER TRADUCCIÓ:
1. Busca el text original de "{titol}" de {autor} en {llengua}
   - Prova cercador_fonts.py o busca a les fonts (Perseus, Gutenberg, ctext.org, etc.)
   - Si no pots trobar-lo, reporta error i suggereix alternatives
2. Guarda l'original a obres/{categoria}/{autor.lower().replace(' ', '-')}/{titol.lower().replace(' ', '-')}/original.md
3. Executa el pipeline V2 per traduir
4. Executa post_traduccio.py per formatar
5. Executa build.py per generar web
6. git add + commit + push
7. Reporta: qualitat, paraules traduïdes, problemes trobats
"""

with open(output_file, 'w') as f:
    f.write(prefix + instruction + suffix)
PYEOF
}

# ── Executar tasca amb Claude Code ─────────────────────────

execute_task() {
    local task_file="$1"
    local task_id
    task_id=$(python3 -c "import json; print(json.load(open('$task_file'))['id'])")
    local task_type
    task_type=$(python3 -c "import json; print(json.load(open('$task_file'))['type'])")
    local max_minutes
    max_minutes=$(python3 -c "import json; print(json.load(open('$task_file')).get('max_duration_minutes', $MAX_TASK_MINUTES))")

    log "═══ Executant: $task_id ($task_type) ═══"
    set_status "RUNNING: $task_id"

    # Moure a running
    task_file=$(move_task "$task_file" "running")
    update_task "$task_file" "status" '"running"'
    update_task "$task_file" "started_at" "\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""

    # Construir instrucció (escriu a fitxer)
    local instruction_file="/tmp/claude-instruction-$$.txt"
    build_instruction "$task_file" "$instruction_file"

    # Executar Claude Code amb timeout
    local result_file="/tmp/claude-task-result-$$.txt"
    local exec_script="/tmp/claude-exec-$$.sh"
    local exit_code=0

    cat > "$exec_script" << 'EXECEOF'
#!/bin/bash
source ~/.nvm/nvm.sh 2>/dev/null
cd "$1"
claude -p "$(cat "$2")" \
    --max-turns 10 \
    --allowedTools "Edit" "Write" \
    "Bash(cat:*)" "Bash(grep:*)" "Bash(ls:*)" "Bash(find:*)" \
    "Bash(head:*)" "Bash(tail:*)" "Bash(wc:*)" "Bash(mkdir:*)" \
    "Bash(cp:*)" "Bash(mv:*)" "Bash(rm:*)" "Bash(touch:*)" \
    "Bash(chmod:*)" "Bash(python3:*)" "Bash(python:*)" "Bash(pip:*)" \
    "Bash(pip3:*)" "Bash(git add:*)" "Bash(git commit:*)" \
    "Bash(git push:*)" "Bash(git status:*)" "Bash(git diff:*)" \
    "Bash(git log:*)" "Bash(sed:*)" "Bash(awk:*)" "Bash(sort:*)" \
    "Bash(tee:*)" \
    --output-format text
EXECEOF
    chmod +x "$exec_script"

    timeout "${max_minutes}m" bash "$exec_script" "$PROJECT_DIR" "$instruction_file" > "$result_file" 2>&1 || exit_code=$?

    local result_text=""
    if [ -f "$result_file" ]; then
        result_text=$(cat "$result_file")
    fi

    # Processar resultat
    if [ $exit_code -eq 0 ] && [ -n "$result_text" ]; then
        # ÈXIT
        log "✅ Tasca $task_id completada"
        update_task "$task_file" "status" '"done"'
        update_task "$task_file" "completed_at" "\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
        # Guardar resultat (escapar per JSON)
        python3 -c "
import json
with open('$task_file', 'r') as f:
    task = json.load(f)
with open('$result_file', 'r') as f:
    task['result'] = f.read()[:5000]  # Max 5KB
with open('$task_file', 'w') as f:
    json.dump(task, f, indent=2, ensure_ascii=False)
"
        move_task "$task_file" "done"
        
        report "✅ [$task_type] $task_id — Completat"
        CONSECUTIVE_FAILS=0

        # Auto-commit si hi ha canvis pendents i no s'ha fet dins Opus
        auto_commit_if_needed "$task_id" "$task_type"

    elif [ $exit_code -eq 124 ]; then
        # TIMEOUT
        log "⏰ Tasca $task_id — TIMEOUT ($max_minutes min)"
        update_task "$task_file" "status" '"failed"'
        update_task "$task_file" "error" "\"TIMEOUT després de ${max_minutes} minuts\""
        move_task "$task_file" "failed"
        
        report "⏰ [$task_type] $task_id — Timeout"
        CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))

    else
        # ERROR
        local error_msg
        error_msg=$(echo "$result_text" | tail -5 | tr '\n' ' ' | head -c 200)
        log "❌ Tasca $task_id — ERROR (exit $exit_code): $error_msg"
        update_task "$task_file" "status" '"failed"'
        update_task "$task_file" "error" "\"Exit $exit_code: $(echo "$error_msg" | sed 's/"/\\"/g')\""
        
        local failed_file
        failed_file=$(move_task "$task_file" "failed")
        
        report "❌ [$task_type] $task_id — Error: $error_msg"
        CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))

        # Auto-generar tasca fix si és un error de codi
        maybe_generate_fix "$failed_file" "$error_msg"
    fi

    # Cleanup
    rm -f "$result_file" "$instruction_file" "$exec_script"
    
    TASKS_TODAY=$((TASKS_TODAY + 1))
}

# ── Auto-commit si Opus no ho ha fet ──────────────────────

auto_commit_if_needed() {
    local task_id="$1"
    local task_type="$2"
    
    cd "$PROJECT_DIR"
    
    # Comprovar si hi ha canvis no comesos
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        check_hourly_reset
        if [ $COMMITS_THIS_HOUR -ge $MAX_COMMITS_PER_HOUR ]; then
            log "WARN: Límit de commits/hora assolit ($MAX_COMMITS_PER_HOUR). Canvis pendents."
            return
        fi
        
        git add -A
        git commit -m "auto: [$task_type] $task_id — $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || true
        git push origin main 2>/dev/null || log "WARN: Push ha fallat"
        
        COMMITS_THIS_HOUR=$((COMMITS_THIS_HOUR + 1))
        log "📤 Auto-commit + push per $task_id"
    fi
}

# ── Auto-generar fix per errors ───────────────────────────

maybe_generate_fix() {
    local failed_file="$1"
    local error_msg="$2"
    
    local task_type
    task_type=$(python3 -c "import json; print(json.load(open('$failed_file'))['type'])" 2>/dev/null)
    local retry_count
    retry_count=$(python3 -c "import json; print(json.load(open('$failed_file')).get('retry_count', 0))" 2>/dev/null)
    local max_retries
    max_retries=$(python3 -c "import json; print(json.load(open('$failed_file')).get('max_retries', 2))" 2>/dev/null)

    # Si encara pot reintentar, reencuar la mateixa tasca
    if [ "$retry_count" -lt "$max_retries" ]; then
        log "🔄 Reintentant tasca (intent $((retry_count + 1))/$max_retries)"
        python3 -c "
import json
with open('$failed_file', 'r') as f:
    task = json.load(f)
task['retry_count'] = task.get('retry_count', 0) + 1
task['status'] = 'pending'
task['error'] = None
task['started_at'] = None
# Afegir l'error anterior a la instrucció
task['instruction'] += f\"\n\nNOTA: L'intent anterior va fallar amb: $error_msg\nSi us plau, intenta un enfocament diferent.\"
import shutil
shutil.move('$failed_file', '$TASKS_DIR/pending/' + task['id'] + '.json')
with open('$TASKS_DIR/pending/' + task['id'] + '.json', 'w') as f:
    json.dump(task, f, indent=2, ensure_ascii=False)
"
        return
    fi
    
    # Si la tasca no era ja un fix, generar un fix
    if [ "$task_type" != "fix" ]; then
        local fix_id="$(date +%s)_fix_auto-$(echo "$error_msg" | tr ' ' '-' | head -c 30)"
        
        python3 << PYEOF
import json
fix_task = {
    "id": "$fix_id",
    "type": "fix",
    "priority": 0,
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "pending",
    "params": {"source_task": "$(basename "$failed_file" .json)", "error": "$error_msg"},
    "instruction": "Una tasca automàtica ha fallat amb aquest error: $error_msg\n\nInvestiga el problema, arregla'l, i assegura't que els tests passen.",
    "max_duration_minutes": 30,
    "retry_count": 0,
    "max_retries": 1,
    "result": None,
    "error": None
}
with open("$TASKS_DIR/pending/$fix_id.json", 'w') as f:
    json.dump(fix_task, f, indent=2, ensure_ascii=False)
PYEOF
        log "🔧 Generada tasca fix automàtica: $fix_id"
    fi
}

# ── Rotar tasques completades ─────────────────────────────

rotate_done() {
    local count
    count=$(ls -1 "$TASKS_DIR/done/"*.json 2>/dev/null | wc -l)
    if [ "$count" -gt 50 ]; then
        local to_delete=$((count - 50))
        ls -1t "$TASKS_DIR/done/"*.json | tail -$to_delete | xargs rm -f
        log "🗑️ Rotades $to_delete tasques antigues"
    fi
}

# ── MAIN LOOP ─────────────────────────────────────────────

main() {
    # Setup
    source ~/.nvm/nvm.sh 2>/dev/null || true
    mkdir -p "$TASKS_DIR"/{pending,running,done,failed}
    check_lock

    log "═══════════════════════════════════════════"
    log "  Worker Arion iniciat (PID $$)"
    log "═══════════════════════════════════════════"
    set_status "IDLE"

    # Netejar running/ velles (crash anterior)
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] || continue
        log "WARN: Tasca orfana trobada, reencuant: $(basename "$f")"
        mv "$f" "$TASKS_DIR/pending/"
    done

    # Main loop
    while true; do
        # Check runtime limit
        if ! check_runtime; then
            break
        fi

        # Check safety limits
        if [ $TASKS_TODAY -ge $MAX_TASKS_PER_DAY ]; then
            log "⚠️ Límit diari de tasques assolit ($MAX_TASKS_PER_DAY). Esperant fins demà."
            set_status "DAILY_LIMIT"
            sleep 3600
            # Reset at midnight
            if [ "$(date +%H)" -eq 0 ]; then
                TASKS_TODAY=0
            fi
            continue
        fi

        if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
            log "🚨 $MAX_CONSECUTIVE_FAILS fails consecutius! Aturant worker. Cal intervenció."
            set_status "HALTED: $MAX_CONSECUTIVE_FAILS fails consecutius"
            report "🚨 WORKER ATURAT: $MAX_CONSECUTIVE_FAILS errors consecutius. Necessito ajuda!"
            break
        fi

        # Get next task
        local next_task
        next_task=$(get_next_task)

        if [ -z "$next_task" ]; then
            set_status "IDLE (cua buida)"
            sleep 60
            continue
        fi

        # Execute
        execute_task "$next_task"

        # Rotate old done tasks
        rotate_done

        # Cooldown
        log "⏸️ Cooldown ${COOLDOWN_SECONDS}s..."
        set_status "COOLDOWN"
        sleep $COOLDOWN_SECONDS
    done

    log "Worker finalitzat"
}

# ── Entry point ───────────────────────────────────────────

main "$@"
