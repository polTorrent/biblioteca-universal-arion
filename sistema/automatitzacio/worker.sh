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
MIN_DIEM=1.0
DIEM_RESERVE=0.5    # Marge de seguretat: sempre es reserva mig DIEM
DIEM_COSTS_CONF="$PROJECT_DIR/sistema/config/diem_costs.conf"
WATCHDOG_INTERVAL=300  # 5 minuts
TASK_TIMEOUT_VENICE=600
TASK_TIMEOUT_VENICE_OPUS=900
TASK_TIMEOUT_HERMES=300
LARGE_OBRA_THRESHOLD=100000  # Obres > 100K chars es tracten per sessions

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
        translate|translation|fix-translate) model=$(lookup_model "translate" "$genre") || model=$(lookup_model "translate" "default") ;;
        fetch) model=$(lookup_model "fetch" "default") ;;
        supervision|review|validacio) model=$(lookup_model "supervisio" "default") || model=$(lookup_model "review" "default") ;;
        fix|code-review) model=$(lookup_model "admin" "default") ;;
        *) model=$(lookup_model "translate" "$genre") || model=$(lookup_model "admin" "default") ;;
    esac
    
    # Fallbacks
    [ -z "$model" ] && model="claude-opus-4-7"
    echo "$model"
}

# ── Estimació de cost per tasca ───────────────────────────────────────────────
# Detecta si una obra és "gran" (> LARGE_OBRA_THRESHOLD caràcters)
# Retorna la mida en caràcters si és gran, buit si no
is_large_obra() {
    local obra_path="$1"
    local original="$PROJECT_DIR/$obra_path/original.md"
    if [ -f "$original" ]; then
        local chars
        chars=$(wc -c < "$original")
        if [ "$chars" -gt "$LARGE_OBRA_THRESHOLD" ]; then
            echo "$chars"
            return 0
        fi
    fi
    return 1
}

# Extreu la ruta de l'obra d'una instrucció de tasca
# Busca el patró obres/{cat}/{autor}/{obra} (evita /original.md al final)
extract_obra_path() {
    local instruction="$1"
    local path
    path=$(echo "$instruction" | grep -oP 'obres/[a-z0-9_-]+/[a-z0-9_-]+/[a-z0-9_-]+' | head -1)
    [ -z "$path" ] && path=$(echo "$instruction" | grep -oP '--ruta\s+"?\Kobres/[a-z0-9/_-]+' | head -1)
    echo "$path"
}

# Compta chunks d'una obra (original.md / 1000)
count_obra_chunks() {
    local obra_path="$1"
    local original="$PROJECT_DIR/$obra_path/original.md"
    if [ -f "$original" ]; then
        local chars
        chars=$(wc -c < "$original")
        echo $(( (chars / 1000) + 1 ))
    else
        echo "0"
    fi
}

estimate_task_cost() {
    local task_type="$1"
    local instruction="$2"
    local cost=0

    # 1. Mirar si tenim cost directe al config
    if [ -f "$DIEM_COSTS_CONF" ]; then
        cost=$(grep -E "^${task_type}[[:space:]]*=" "$DIEM_COSTS_CONF" 2>/dev/null | head -1 | awk -F'= *' '{print $2}' | tr -d ' ')
    fi

    # 2. Fallback per tipus genèric
    if [ -z "$cost" ] || [ "$cost" = "0" ]; then
        case "$task_type" in
            translate*)  cost=1.5 ;;
            fix-translate|fix-complex) cost=1.5 ;;
            fix-*) cost=0.5 ;;
            review|supervisio|validacio) cost=0.4 ;;
            fetch|audit|publish) cost=0.2 ;;
            *) cost=0.3 ;;
        esac
    fi

    # 3. Ajustar segons mida de la instrucció (indicador de complexitat)
    local instr_len=${#instruction}
    if [ "$instr_len" -gt 500 ]; then
        cost=$(python3 -c "print(round(float('$cost') * 1.3, 2))" 2>/dev/null || echo "$cost")
    elif [ "$instr_len" -gt 1000 ]; then
        cost=$(python3 -c "print(round(float('$cost') * 1.5, 2))" 2>/dev/null || echo "$cost")
    fi

    echo "$cost"
}

# ── Comprovació DIEM amb estimació de cost ────────────────────────────────────
# check_diem [cost_estimat]
# Sense argument: comprova DIEM >= MIN_DIEM (check bàsic)
# Amb argument: comprova que DIEM - DIEM_RESERVE >= cost_estimat
check_diem() {
    local estimated_cost="${1:-}"
    local balance
    balance=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    
    if [ -z "$balance" ]; then
        log "⚠️ No s'ha pogut obtenir el saldo DIEM. Continuant amb precaució."
        return 0
    fi

    if [ -n "$estimated_cost" ]; then
        # Check amb cost estimat: DIEM - RESERVE >= cost
        local available
        available=$(python3 -c "print(round(float('$balance') - $DIEM_RESERVE, 4))" 2>/dev/null)
        local can_afford=$(python3 -c "print('yes' if float('$available') >= float('$estimated_cost') else 'no')" 2>/dev/null)
        
        if [ "$can_afford" = "no" ]; then
            log "💰 DIEM: $balance | Disponible (sense marge): $available | Cost estimat: $estimated_cost"
            log "🛑 Aturant worker: cost de la tasca excedeix el pressupost disponible."
            touch "$DIEM_STOP"
            # Generar informe d'aturada
            bash "$PROJECT_DIR/sistema/automatitzacio/modules/11-shutdown-report.sh" "$balance" "$available" "$estimated_cost" 2>/dev/null || true
            return 1
        fi
        
        log "💰 DIEM: $balance (disponible: $available, cost: $estimated_cost) ✓"
    else
        # Check bàsic sense estimació
        local ok=$(python3 -c "print('yes' if float('$balance') >= $MIN_DIEM else 'no')" 2>/dev/null)
        if [ "$ok" = "no" ]; then
            log "⚠️ DIEM baix ($balance < $MIN_DIEM). Aturant worker."
            touch "$DIEM_STOP"
            bash "$PROJECT_DIR/sistema/automatitzacio/modules/11-shutdown-report.sh" "$balance" "0" "0" 2>/dev/null || true
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
                fix-metadata|fix-glossari|fix-portada|fix-fetch|supervision|code-review|maintenance) use_hermes=true ;;
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
        # Fallback intel·ligent: no usar el mateix model
        if [[ "$model" == *"opus"* ]]; then
            fallback="claude-sonnet-4-6"
        elif [[ "$model" == *"sonnet"* ]]; then
            fallback="claude-opus-4-7"
        else
            fallback=$(lookup_model "admin" "default")
        fi
        [ "$fallback" != "$model" ] && { model="$fallback"; timeout=$TASK_TIMEOUT_VENICE; log "   ↔️ Fallback a: $model"; }
    fi
    
    log "   🔧 Venice AI (model=$model, timeout=${timeout}s)"
    
    case "$task_type" in
        fix-translate|translate)
            # ── FIX: Obres grans → mode sessió amb --continuar ──
            local fix_obra_ruta=$(extract_obra_path "$instruction")
            
            # Assegurar que original.md existeix (la instrucció original pot fer fetch)
            local fix_original="$PROJECT_DIR/$fix_obra_ruta/original.md"
            if [ -n "$fix_obra_ruta" ] && [ ! -s "$fix_original" ]; then
                log "   ⬇️ Executant fetch de l'original..."
                timeout 180 bash -c "
                    cd $PROJECT_DIR
                    $(echo "$instruction" | grep -oP 'python3 sistema/traduccio/cercador_fonts_v2\.py[^;]*')
                " 2>&1
            fi

            local fix_obra_chars=$(is_large_obra "$fix_obra_ruta")

            if [ -n "$fix_obra_chars" ] && [ -n "$fix_obra_ruta" ]; then
                local fix_chunks=$(count_obra_chunks "$fix_obra_ruta")
                log "   📏 Obra gran detectada: ${fix_obra_chars} chars (~${fix_chunks} chunks) → mode sessió"

                if [ -s "$fix_original" ]; then
                    # Sempre usar --continuar per reprendre des de l'últim chunk
                    timeout "$timeout" python3 "$PROJECT_DIR/sistema/traduccio/traduir_venice.py" \
                        --ruta "$fix_obra_ruta" --model "$model" --continuar 2>&1
                else
                    log "   ❌ No s'ha pogut obtenir original.md per $fix_obra_ruta"
                    return 1
                fi
            else
                # Obra petita: executar instrucció normal o traducció estàndard directa
                if [ "$task_type" = "translate" ]; then
                    # Si és translate estàndard (obra petita), respectar la lògica original:
                    local continuar_flag=""
                    if [ -f "$PROJECT_DIR/$fix_obra_ruta/traduccio.md" ] && [ -s "$PROJECT_DIR/$fix_obra_ruta/traduccio.md" ]; then
                        continuar_flag="--continuar"
                    fi
                    timeout "$timeout" python3 "$PROJECT_DIR/sistema/traduccio/traduir_venice.py" --ruta "$fix_obra_ruta" --model "$model" $continuar_flag 2>&1
                else
                    log "   📏 Obra petita ($(is_large_obra "$fix_obra_ruta" || echo "${#instruction} chars instrucció")) → execució directa"
                    timeout "$timeout" bash -c "$instruction" 2>&1
                fi
            fi
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
    
    # DIEM check bàsic (sense estimació de cost)
    check_diem || break
    
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
    
    # Estimar cost d'aquesta tasca i comprovar DIEM
    TASK_COST=$(estimate_task_cost "$TASK_TYPE" "$INSTRUCTION")
    if ! check_diem "$TASK_COST"; then
        log "🛑 Tasca $TASK_ID ($TASK_TYPE) requeriria ~${TASK_COST} DIEM. Aturant cicle."
        break
    fi
    
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
        # Verificar canvis reals (exclou fitxers d'infraestructura: tasques i heartbeat)
        diff_count=$(cd "$PROJECT_DIR" && git diff --name-only 2>/dev/null | grep -vE '^sistema/(tasks|state)' | wc -l)
        untracked_count=$(cd "$PROJECT_DIR" && git ls-files --others --exclude-standard 2>/dev/null | grep -vE '^sistema/(tasks|state)' | wc -l)
        CHANGES=$((diff_count + untracked_count))
        
        # Només supervision/review/validacio poden completar-se sense canvis al repo
        is_fix=0
        case "$TASK_TYPE" in
            supervision|review|validacio) is_fix=1 ;;
        esac
        
        if [ "$CHANGES" -gt 0 ] || [ "$is_fix" -eq 1 ]; then
            log "✅ $TASK_ID completat (${DURATION}s, $CHANGES canvis)"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            model_error_reset "$(select_model "$TASK_TYPE" "$INSTRUCTION" "")"
            reset_errors
            write_watchdog "idle"
            sleep $COOLDOWN_OK
        else
            log "⚠️ $TASK_ID sense canvis (${DURATION}s)"
            python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['last_error']='No changes detected'; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1)); save_errors
            sleep $COOLDOWN_FAIL
        fi
    elif [ $EXIT -eq 124 ]; then
        log "⏱️ Timeout per $TASK_ID (${DURATION}s)"

        # ── FIX: Obres grans — mode sessió: si hi ha progrés, tornar a pending amb retries=0 ──
        local is_session=false
        local obra_for_check=$(extract_obra_path "$INSTRUCTION")
        if [ -n "$obra_for_check" ] && { [ "$TASK_TYPE" = "fix-translate" ] || [ "$TASK_TYPE" = "translate" ]; }; then
            local traduccio_file="$PROJECT_DIR/$obra_for_check/traduccio.md"
            if [ -f "$traduccio_file" ] && [ -s "$traduccio_file" ]; then
                is_session=true
            fi
        fi

        if [ "$is_session" = true ]; then
            # Obra gran amb progrés: commit parcial, resetejar retries, tornar a pending
            log "   📝 Progrés parcial detectat → commit i reprèn propera sessió"
            cd "$PROJECT_DIR"
            git add -A "$obra_for_check/" 2>/dev/null
            git commit -m "[worker] sessió parcial: $TASK_ID" 2>/dev/null
            git push origin main 2>/dev/null && log "   📤 Push parcial OK" || log "   ⚠️ Push parcial fallit"

            # Resetear retries a 0 perquè la propera sessió tingui 3 oportunitats
            python3 -c "
import json
f='$TASKS_DIR/running/$TASK_BASENAME'
d=json.load(open(f))
d['retries']=0
d['last_error']='timeout after ${DURATION}s (sessió parcial, progrés guardat)'
json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
            # No incrementar consecutive_errors — és progrés, no fallada
            log "   ↩️ $TASK_ID tornada a pending (retries=0) per continuar sessió"
            sleep 10  # Pausa curta, no COOLDOWN_FAIL
        else
            RETRIES_NOW=$((RETRIES + 1))
            if [ $RETRIES_NOW -lt $MAX_RETRIES ]; then
                python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['retries']=$RETRIES_NOW; d['last_error']='timeout after ${DURATION}s'; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
                mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
            else
                log "⏱️ $TASK_ID: $MAX_RETRIES timeouts consecutius. Marcant com failed."
                python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['last_error']='timeout after $MAX_RETRIES retries (${DURATION}s each)'; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
                mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
                CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1)); save_errors
            fi
            model_error_incr "$(select_model "$TASK_TYPE" "$INSTRUCTION" "")"
            sleep $COOLDOWN_FAIL
        fi
    else
        log "❌ $TASK_ID fallit (exit=$EXIT, ${DURATION}s)"
        RETRIES_NOW=$((RETRIES + 1))
        if [ $RETRIES_NOW -lt $MAX_RETRIES ]; then
            python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['retries']=$RETRIES_NOW; d['last_error']='exit code $EXIT'; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
        else
            python3 -c "import json; f='$TASKS_DIR/running/$TASK_BASENAME'; d=json.load(open(f)); d['last_error']='exit code $EXIT after $RETRIES_NOW retries'; json.dump(d,open(f,'w'),indent=2)" 2>/dev/null
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
