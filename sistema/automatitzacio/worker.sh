#!/bin/bash
# =============================================================================
# worker.sh — Worker unificat per Biblioteca Arion (venice/hermes/hybrid)
# =============================================================================
# Modes:
#   --mode=venice   → Venice AI per tot (traduccions + tasques)
#   --mode=hermes   → Hermes delegate_task per tot
#   --mode=hybrid   → Venice per traduccions/fetch, Hermes per fix/supervisió (DEFAULT)
# =============================================================================
set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT_DIR="$HOME/biblioteca-universal-arion"
TASKS_DIR="$PROJECT_DIR/sistema/tasks"
STATE_DIR="$PROJECT_DIR/sistema/state"
LOG="$PROJECT_DIR/sistema/logs/worker.log"
LOCKFILE="$TASKS_DIR/worker.lock"
DIEM_STOP="$STATE_DIR/diem_stop"
VENICE_CLI="$HOME/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py"
MODELS_CONF="$PROJECT_DIR/sistema/config/models.conf"

# Carregar variables d'entorn del .env (VENICE_API_KEY, etc.)
if [ -f "$PROJECT_DIR/.env" ]; then
    # shellcheck disable=SC1090
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

# ── Paràmetres per defecte ────────────────────────────────────────────────────
MODE="hybrid"
MAX_RETRIES=3
MAX_CONSECUTIVE_FAILS=3
COOLDOWN_OK=30
COOLDOWN_FAIL=60
COOLDOWN_EMERGENCY=600
CONSECUTIVE_ERRORS_FILE="/tmp/arion-worker-errors.txt"
MAX_RUNTIME=32400    # 9 hores
MIN_DIEM=2.0
WATCHDOG_INTERVAL=300  # 5 minuts
TASK_TIMEOUT_VENICE=900
TASK_TIMEOUT_VENICE_OPUS=1200
TASK_TIMEOUT_HERMES=1800

# ── Parsejar arguments ──────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --mode=*) MODE="${arg#--mode=}" ;;
        --max-retries=*) MAX_RETRIES="${arg#--max-retries=}" ;;
        --timeout=*) TASK_TIMEOUT_VENICE="${arg#--timeout=}"; TASK_TIMEOUT_HERMES="$TASK_TIMEOUT_VENICE" ;;
    esac
done

# ── Inicialització ──────────────────────────────────────────────────────────
mkdir -p "$TASKS_DIR"/{pending,running,done,failed,failed_permanent} "$STATE_DIR"

START_TIME=$(date +%s)
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WORKER:$MODE] $1" | tee -a "$LOG"; }

# ── Model error tracking (circuit breaker per model) ────────────────────────
MODEL_ERRORS_DIR="/tmp/arion-model-errors"
mkdir -p "$MODEL_ERRORS_DIR"

model_error_count() { local f="$MODEL_ERRORS_DIR/$1"; [ -f "$f" ] && cat "$f" || echo 0; }
model_error_incr() { local f="$MODEL_ERRORS_DIR/$1"; echo $(( $(model_error_count "$1") + 1 )) > "$f"; }
model_error_reset() { rm -f "$MODEL_ERRORS_DIR/$1"; }

# ── Selector de models ──────────────────────────────────────────────────────
lookup_model() {
    local group="$1" subtype="${2:-default}"
    [ -f "$MODELS_CONF" ] || return 1
    local model
    model=$(grep -E "^${group}:${subtype}[[:space:]]*=" "$MODELS_CONF" 2>/dev/null | head -1 | sed 's/^[^=]*=[[:space:]]*\([^[:space:]]*\).*/\1/')
    [ -z "$model" ] && [ "$subtype" != "default" ] && model=$(grep -E "^${group}:default[[:space:]]*=" "$MODELS_CONF" 2>/dev/null | head -1 | sed 's/^[^=]*=[[:space:]]*\([^[:space:]]*\).*/\1/')
    [ -n "$model" ] && echo "$model" && return 0
    return 1
}

lookup_timeout() {
    local group="$1" subtype="${2:-default}"
    [ -f "$MODELS_CONF" ] || return 1
    local timeout
    timeout=$(grep -E "^${group}:${subtype}[[:space:]]*=" "$MODELS_CONF" 2>/dev/null | head -1 | grep -oP 'timeout=\K\d+')
    [ -z "$timeout" ] && [ "$subtype" != "default" ] && timeout=$(grep -E "^${group}:default[[:space:]]*=" "$MODELS_CONF" 2>/dev/null | head -1 | grep -oP 'timeout=\K\d+')
    [ -n "$timeout" ] && echo "$timeout" && return 0
    return 1
}

detect_genre() {
    local text="$1"
    echo "$text" | grep -qiE "obres/poesia|poes[ií]a|sonets?|poema|versos" && echo "poesia" && return
    echo "$text" | grep -qiE "obres/teatre|teatre|drama|acte|escena" && echo "teatre" && return
    echo "$text" | grep -qiE "obres/filosofia|filosof[ií]a|plato|aristot|epicte|seneca|nietzsche|schopenhauer" && echo "filosofia" && return
    echo "$text" | grep -qiE "obres/oriental|oriental|s[aà]nscrit|xin[eè]s|rumi" && echo "oriental" && return
    echo "$text" | grep -qiE "obres/narrativa|novel·la|narrativa|contes|kipling|txekhov" && echo "narrativa" && return
    echo "default"
}

select_model() {
    local task_type="$1" instruction="$2" recommended="$3"
    [ -n "$recommended" ] && [ "$recommended" != "null" ] && echo "$recommended" && return 0
    
    local genre=$(detect_genre "$instruction")
    local model
    
    case "$task_type" in
        translate|translation) model=$(lookup_model "translate" "$genre") || model=$(lookup_model "translate" "default") ;;
        fetch) model=$(lookup_model "fetch" "default") ;;
        supervision|review|validacio) model=$(lookup_model "supervisio" "default") || model=$(lookup_model "review" "default") ;;
        fix|code-review) model=$(lookup_model "admin" "default") ;;
        *) model=$(lookup_model "translate" "$genre") || model=$(lookup_model "admin" "default") ;;
    esac
    
    # Fallbacks
    [ -z "$model" ] && model="zai-org-glm-5"
    echo "$model"
}

# ── Comprovació DIEM ─────────────────────────────────────────────────────────
check_diem() {
    local balance
    balance=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    if [ -n "$balance" ]; then
        local ok=$(python3 -c "print('yes' if float('$balance') >= $MIN_DIEM else 'no')" 2>/dev/null)
        if [ "$ok" = "no" ]; then
            log "⚠️ DIEM baix ($balance < $MIN_DIEM). Aturant worker."
            touch "$DIEM_STOP"
            return 1
        fi
        rm -f "$DIEM_STOP"
    fi
    return 0
}

# ── Watchdog ─────────────────────────────────────────────────────────────────
write_watchdog() {
    local current_task="${1:-none}"
    local diem_balance=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    local uptime=$(( $(date +%s) - START_TIME ))
    local done_count=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date -d "@$START_TIME" '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
    local fail_count=$(cat "$CONSECUTIVE_ERRORS_FILE" 2>/dev/null || echo 0)
    
    cat > "$STATE_DIR/worker_heartbeat.json" << EOF
{
    "pid": $$,
    "mode": "$MODE",
    "current_task": "$current_task",
    "diem_balance": "${diem_balance:-unknown}",
    "uptime_seconds": $uptime,
    "tasks_completed": $done_count,
    "tasks_failed": $fail_count,
    "last_heartbeat": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# ── Executar tasca ──────────────────────────────────────────────────────────
run_task() {
    local task_file="$1"
    local task_type=$(python3 -c "import json; print(json.load(open('$task_file')).get('type','unknown'))" 2>/dev/null)
    local instruction=$(python3 -c "import json; print(json.load(open('$task_file')).get('instruction',''))" 2>/dev/null)
    local recommended=$(python3 -c "import json; print(json.load(open('$task_file')).get('model',''))" 2>/dev/null)
    
    cd "$PROJECT_DIR"
    
    # Determinar com executar segons mode i tipus
    local use_hermes=false
    case "$MODE" in
        venice) use_hermes=false ;;
        hermes) use_hermes=true ;;
        hybrid)
            case "$task_type" in
                fix-metadata|fix-glossari|fix-portada|fix-translate|fix-fetch|supervision|code-review|maintenance) use_hermes=true ;;
                *) use_hermes=false ;;
            esac
            ;;
    esac
    
    if [ "$use_hermes" = true ]; then
        local timeout=$TASK_TIMEOUT_HERMES
        local executor="$PROJECT_DIR/sistema/automatitzacio/hermes_task_executor.py"
        if [ -f "$executor" ]; then
            log "   🔧 Hermes mode: $task_type"
            timeout "$timeout" python3 "$executor" "$task_file" 2>&1
            return $?
        else
            log "   ⚠️ Hermes executor no trobat, fallback a Venice"
            use_hermes=false
        fi
    fi
    
    # Venice AI
    local model=$(select_model "$task_type" "$instruction" "$recommended")
    local genre=$(detect_genre "$instruction")
    local timeout=$(lookup_timeout "translate" "$genre" 2>/dev/null)
    [ -z "$timeout" ] && timeout=$TASK_TIMEOUT_VENICE
    # Opus és més lent: doblar timeout
    [[ "$model" == *opus* ]] && [ "$timeout" -le "$TASK_TIMEOUT_VENICE" ] && timeout=$TASK_TIMEOUT_VENICE_OPUS
    
    # Circuit breaker: si aquest model ha fallat 3 vegades seguides, canvia
    local model_errors=$(model_error_count "$model")
    if [ "$model_errors" -ge 3 ]; then
        log "   🔄 Circuit breaker: $model ha fallat $model_errors vegades. Buscant fallback..."
        local fallback=$(lookup_model "admin" "default")
        [ "$fallback" != "$model" ] && model="$fallback" && timeout=$TASK_TIMEOUT_VENICE
    fi
    
    log "   🔧 Venice AI (model=$model, timeout=${timeout}s)"
    
    case "$task_type" in
        translate|translation)
            # Pre-supervisió: analitzar estat de l'obra ABANS de traduir
            local obra_ruta="$(echo "$instruction" | grep -oP 'obres/[a-z0-9/_-]+' | head -1)"
            if [ -n "$obra_ruta" ]; then
                local pre_result=$(python3 "$PROJECT_DIR/sistema/scripts/pre_supervisio.py" "$obra_ruta" --json 2>/dev/null)
                if [ -n "$pre_result" ]; then
                    local decisio=$(echo "$pre_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('decisio',{}).get('accio','TRADUIR_COMPLET'))" 2>/dev/null)
                    local motiu=$(echo "$pre_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('decisio',{}).get('motiu',''))" 2>/dev/null)
                    log "   📋 Pre-supervisió: $decisio — $motiu"
                    
                    case "$decisio" in
                        BLOQUEJAR)
                            log "   🛑 Obra bloquejada: $motiu"
                            echo "BLOQUEJAT: $motiu"
                            return 1
                            ;;
                        SUPERVISAR)
                            log "   ✅ Traducció completa — només supervisió necessària"
                            echo "JA_COMPLETAT: $motiu"
                            return 0
                            ;;
                        RETRADUIR)
                            # Eliminar traducció existent per recomençar net
                            log "   🔄 Retraducció: esborrant traduccio.md anterior"
                            rm -f "$PROJECT_DIR/$obra_ruta/traduccio.md"
                            rm -f "$PROJECT_DIR/$obra_ruta/.chunks_traduïts.json"
                            ;;
                        CONTINUAR)
                            # Continuar des de l'últim chunk
                            ;;
                        TRADUIR_COMPLET)
                            # Traducció nova des de zero
                            ;;
                    esac
                fi
            fi
            
            # --continuar: reprendre des de l'últim chunk si ja existeix traducció
            local continuar_flag=""
            if [ -f "$PROJECT_DIR/$obra_ruta/traduccio.md" ] && [ -s "$PROJECT_DIR/$obra_ruta/traduccio.md" ]; then
                continuar_flag="--continuar"
            fi
            timeout "$timeout" python3 "$PROJECT_DIR/sistema/traduccio/traduir_venice.py" --ruta "$obra_ruta" --model "$model" $continuar_flag 2>&1
            ;;
        fetch|fix-translate|fix-fetch)
            eval timeout "$timeout" bash -c "$instruction" 2>&1
            ;;
        *)
            # Per tasques administratives (fix-metadata, fix-glossari, etc.), usar Venice chat
            timeout "$timeout" python3 "$VENICE_CLI" chat --model "$model" --system "Ets un assistent per Biblioteca Arion. Executa la tasca demanada." "$instruction" 2>&1
            ;;
    esac
    return $?
}

# ── Auto-commit ──────────────────────────────────────────────────────────────
auto_commit() {
    local task_id="$1"
    cd "$PROJECT_DIR"
    if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        git add -A 2>/dev/null
        git commit -m "[worker] $task_id" 2>/dev/null
        git push origin main 2>/dev/null && log "   📤 Push OK: $task_id" || log "   ⚠️ Push fallit"
    fi
}

# ── Graceful shutdown ─────────────────────────────────────────────────────────
cleanup() {
    log "🛑 Senyal rebut. Graceful shutdown..."
    # Retornar tasca running a pending
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "   ↩️ Retornada: $(basename "$f")"
    done
    rm -f "$LOCKFILE"
    write_watchdog "shutdown"
    log "👋 Worker aturat netament"
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Lockfile ──────────────────────────────────────────────────────────────────
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "Worker ja actiu (PID $OLD_PID). Sortint."
        exit 1
    fi
    rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"

# ── Comptador errors consecutius ──────────────────────────────────────────────
load_errors() { CONSECUTIVE_FAILS=$(cat "$CONSECUTIVE_ERRORS_FILE" 2>/dev/null || echo 0); }
save_errors() { echo "$CONSECUTIVE_FAILS" > "$CONSECUTIVE_ERRORS_FILE"; }
reset_errors() { CONSECUTIVE_FAILS=0; echo 0 > "$CONSECUTIVE_ERRORS_FILE"; }

# =============================================================================
# MAIN LOOP
# =============================================================================
load_errors
log "🚀 Worker iniciat (PID $$, mode=$MODE)"
write_watchdog "starting"

LAST_WATCHDOG=$(date +%s)

while true; do
    # Timeout global
    now=$(date +%s)
    elapsed=$((now - START_TIME))
    if [ $elapsed -ge $MAX_RUNTIME ]; then
        log "⏰ Runtime màxim ($(($MAX_RUNTIME/3600))h) completat."
        break
    fi
    
    # Emergency: massa errors consecutius
    if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
        log "🛡️ $CONSECUTIVE_FAILS errors consecutius. Pausa ${COOLDOWN_EMERGENCY}s."
        sleep $COOLDOWN_EMERGENCY
        reset_errors
        continue
    fi
    
    # DIEM check
    check_diem || break
    
    # Watchdog heartbeat
    if [ $((now - LAST_WATCHDOG)) -ge $WATCHDOG_INTERVAL ]; then
        write_watchdog "idle"
        LAST_WATCHDOG=$now
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
        sleep 60
        continue
    fi
    
    # Llegir tasca
    TASK_ID=$(python3 -c "import json; print(json.load(open('$TASK')).get('id','unknown'))" 2>/dev/null)
    TASK_TYPE=$(python3 -c "import json; print(json.load(open('$TASK')).get('type','unknown'))" 2>/dev/null)
    RETRIES=$(python3 -c "import json; print(json.load(open('$TASK')).get('retries',0))" 2>/dev/null)
    INSTRUCTION=$(python3 -c "import json; print(json.load(open('$TASK')).get('instruction',''))" 2>/dev/null)
    
    TASK_BASENAME=$(basename "$TASK")
    log "═══════════════════════════════════════════"
    log "▶ $TASK_ID (tipus=$TASK_TYPE, intent $((RETRIES + 1))/$MAX_RETRIES)"
    log "   ${INSTRUCTION:0:100}..."
    
    # Moure a running
    mv -n "$TASK" "$TASKS_DIR/running/$TASK_BASENAME" 2>/dev/null || continue
    
    write_watchdog "$TASK_ID"
    TASK_START=$(date +%s)
    
    # Executar
    RESULT=$(run_task "$TASKS_DIR/running/$TASK_BASENAME")
    EXIT=$?
    TASK_END=$(date +%s)
    DURATION=$((TASK_END - TASK_START))
    
    if [ $EXIT -eq 0 ]; then
        # Verificar canvis
        CHANGES=$(cd "$PROJECT_DIR" && git diff --name-only 2>/dev/null | wc -l; git ls-files --others --exclude-standard 2>/dev/null | wc -l)
        
        if [ "$CHANGES" -gt 0 ]; then
            log "✅ $TASK_ID completat (${DURATION}s, $CHANGES canvis)"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            model_error_reset "$(select_model "$TASK_TYPE" "$INSTRUCTION" "")"
            reset_errors
            write_watchdog "idle"
            sleep $COOLDOWN_OK
        else
            log "⚠️ $TASK_ID sense canvis (${DURATION}s)"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1)); save_errors
            sleep $COOLDOWN_FAIL
        fi
    elif [ $EXIT -eq 124 ]; then
        log "⏱️ Timeout per $TASK_ID (${DURATION}s)"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        model_error_incr "$(select_model "$TASK_TYPE" "$INSTRUCTION" "")"
        sleep $COOLDOWN_FAIL
    else
        log "❌ $TASK_ID fallit (exit=$EXIT, ${DURATION}s)"
        RETRIES_NOW=$((RETRIES + 1))
        if [ $RETRIES_NOW -lt $MAX_RETRIES ]; then
            python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['retries']=$RETRIES_NOW; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        else
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1)); save_errors
        fi
        model_error_incr "$(select_model "$TASK_TYPE" "$INSTRUCTION" "")"
        sleep $COOLDOWN_FAIL
    fi
done

# ── Cleanup final ────────────────────────────────────────────────────────────
for f in "$TASKS_DIR/running/"*.json; do [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/"; done
rm -f "$LOCKFILE"
write_watchdog "stopped"
log "👋 Worker finalitzat"
