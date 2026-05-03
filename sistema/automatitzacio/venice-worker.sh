#!/bin/bash
# =============================================================================
# venice-worker.sh — Worker autònom amb Venice AI (Selectorde Models Intel·ligent)
# =============================================================================
# Reemplaça claude-worker-mini.sh per funcionar amb Venice AI
# Selector de models segons tipus de tasca i gènere de l'obra
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

MAX_RETRIES=3                # Intents per tasca abans de marcar com a failed
MAX_CONSECUTIVE_FAILS=3      # Pausa llarga si N tasques seguides fallen
COOLDOWN_OK=30               # Segons entre tasques OK
COOLDOWN_FAIL=60            # Segons després d'un fail
COOLDOWN_EMERGENCY=600       # 10 min pausa si massa errors
CONSECUTIVE_ERRORS_FILE="/tmp/worker-consecutive-errors.txt"
TASK_TIMEOUT=1800            # 30 min timeout per tasca
DONE_RETENTION_DAYS=7        # Dies que es guarden les tasques completades
IDLE_POLL=60                 # Segons entre polls quan no hi ha tasques
MIN_DIEM=2.0                 # Mínim DIEM per operar (per sota = stop) - deixa marge per comunicació

# Model de Venice AI per defecte (per a tasques administratives)
DEFAULT_MODEL="zai-org-glm-5"

# ── Selector de models segons tipus de tasca ───────────────────────────────────
# MAI utilitzar deepseek per a traduccions! Només per a fetch.
# MAI utilitzar glm-5 per a traduccions! Només per a metadata/glossaris.
select_model() {
    local task_type="$1"
    local task_instruction="$2"
    local model_recomanat="$3"
    
    # Si la tasca té un model recomanat, usar-lo
    if [ -n "$model_recomanat" ] && [ "$model_recomanat" != "null" ]; then
        echo "$model_recomanat"
        return 0
    fi
    
    # Seleccionar segons tipus de tasca
    case "$task_type" in
        translate|translation|retranslate|fix-translate|fix-translation)
            # Detectar gènere per paraules clau
            if echo "$task_instruction" | grep -qiE "filosof[ií]a|poes[ií]a|teatre|cl[àa]ssic|grec|llat[ií]|plato|aristot|socrates|epicte|marc aureli|seneca"; then
                echo "claude-opus-4-7"
            elif echo "$task_instruction" | grep -qiE "novel·la|narrativa|assaig|contes|relat"; then
                echo "claude-sonnet-4-6"
            else
                # Per defecte per a traduccions: Opus per seguretat
                echo "claude-opus-4-7"
            fi
            ;;
        fetch|investigar)
            echo "deepseek-v3.2"
            ;;
        review|supervisio|validacio)
            echo "gemini-3-1-pro-preview"
            ;;
        glossari|metadata|web|test)
            echo "glm-5"
            ;;
        *)
            # Per defecte per a tasques desconegudes
            echo "$DEFAULT_MODEL"
            ;;
    esac
}

# ── Comprovació DIEM i stop global ────────────────────────────────────────────
check_diem_and_maybe_stop() {
    # Si ja existeix el fitxer de stop, sortir
    if [ -f "$DIEM_STOP" ]; then
        log "🛑 DIEM STOP actiu. Sortint..."
        exit 0
    fi
    
    # Consultar saldo DIEM
    local balance
    balance=$(python3 "$VENICE_CLI" balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    
    if [ -z "$balance" ]; then
        log "⚠️ No s'ha pogut consultar el saldo DIEM"
        return 0  # Continuar si no podem verificar
    fi
    
    # Comprovar si estem per sota del mínim
    local is_low
    is_low=$(python3 -c "print('yes' if float('$balance') < $MIN_DIEM else 'no')" 2>/dev/null)
    
    if [ "$is_low" = "yes" ]; then
        log "🚨 DIEM CRÍTIC ($balance < $MIN_DIEM). Creant stop global..."
        
        # Crear fitxer de stop
        mkdir -p "$(dirname "$DIEM_STOP")"
        echo "{\"timestamp\": \"$(date -Iseconds)\", \"balance\": $balance, \"reason\": \"DIEM below minimum\"}" > "$DIEM_STOP"
        
        # Notificar per Discord
        notify_discord_diem_stop "$balance"
        
        exit 0
    fi
    
    log "💰 DIEM: $balance (OK, mínim: $MIN_DIEM)"
    return 0
}

notify_discord_diem_stop() {
    local balance="$1"
    local message="🛑 **STOP GLOBAL ACTIVAT**

💰 Saldo DIEM: **$balance** (mínim: $MIN_DIEM)
⏰ Aturat: $(date '+%Y-%m-%d %H:%M:%S %Z')

El sistema romandrà aturat fins al reset de crèdits a les 00:00 UTC.
El worker es reactivarà automàticament."
    
    # Intentar enviar per Discord
    hermes chat --platform discord --chat-id "1469504522614476953" "$message" 2>/dev/null || true
}

# ── Executar tasca de traducció amb script dedicat ─────────────────────────────
run_translate_task() {
    local obra="$1"
    local model="$2"
    local continuar="$3"
    
    log "   📖 Executant traduir_venice.py per a: $obra"
    
    cd "$PROJECT_DIR"
    local cmd="python3 sistema/traduccio/traduir_venice.py --ruta \"$obra\" --model \"$model\""
    
    if [ "$continuar" = "true" ]; then
        cmd="$cmd --continuar"
    fi
    
    log "   🔧 Comanda: $cmd"
    
    local result
    result=$(eval "timeout $TASK_TIMEOUT $cmd" 2>&1)
    local exit_code=$?
    
    echo "$result"
    return $exit_code
}

# ── Executar tasca de fetch (descarregar URL) ─────────────────────────────────
run_fetch_task() {
    local url="$1"
    local output="$2"
    local source_type="${3:-auto}"
    
    log "   📥 Executant fetch_url.py per a: $url"
    
    cd "$PROJECT_DIR"
    
    # Si output és relatiu, fer-ho absolut respecte PROJECT_DIR
    if [[ "$output" != /* ]]; then
        output="$PROJECT_DIR/$output"
    fi
    
    local cmd="python3 sistema/traduccio/fetch_url.py --url \"$url\" --output \"$output\" --source $source_type --timeout 120"
    
    log "   🔧 Comanda: $cmd"
    
    local result
    result=$(eval "timeout 180 $cmd" 2>&1)
    local exit_code=$?
    
    echo "$result"
    return $exit_code
}

# ── Prefix anti-pla (s'afegeix a TOTES les instruccions) ─────────────────────
EXEC_PREFIX="IMPORTANT: Executa les accions directament. NO generis plans, llistes de passos, ni propostes. Crea els fitxers, escriu el contingut, i fes els canvis DIRECTAMENT. Si necessites crear un directori, crea'l. Si necessites escriure un fitxer, escriu-lo. MAI responguis amb 'El pla és...' o 'Els passos serien...'. ACTUA.

"

# ── Comptador persistent d'errors consecutius ────────────────────────────────
load_consecutive_errors() {
    if [ -f "$CONSECUTIVE_ERRORS_FILE" ]; then
        CONSECUTIVE_FAILS=$(cat "$CONSECUTIVE_ERRORS_FILE" 2>/dev/null || echo 0)
    else
        CONSECUTIVE_FAILS=0
    fi
}

save_consecutive_errors() {
    echo "$CONSECUTIVE_FAILS" > "$CONSECUTIVE_ERRORS_FILE"
}

reset_consecutive_errors() {
    CONSECUTIVE_FAILS=0
    echo 0 > "$CONSECUTIVE_ERRORS_FILE"
}

# ── Inicialització ────────────────────────────────────────────────────────────
source ~/.nvm/nvm.sh 2>/dev/null
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# Carregar comptador d'errors (funció ja definida)
load_consecutive_errors
TODAY=$(date '+%Y-%m-%d')

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

# ── Notificació Discord via heartbeat ────────────────────────────────────────
notify_discord_pause() {
    local errors="$1"
    local pause_secs="$2"
    local heartbeat_md="$PROJECT/sistema/state/HEARTBEAT.md"
    if [ -f "$heartbeat_md" ]; then
        local msg="⚠️ WORKER PAUSA: $errors errors consecutius detectats. Pausa de ${pause_secs}s activada a $(date '+%H:%M:%S')"
        echo -e "\n## Worker Alert ($(date '+%Y-%m-%d %H:%M:%S'))\n$msg" >> "$heartbeat_md"
        log "📢 Notificació de pausa escrita a HEARTBEAT.md per Discord"
    fi
}

# ── Lockfile: evitar workers duplicats ────────────────────────────────────────
acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log "⛔ Worker ja actiu (PID $OLD_PID). Sortint."
            exit 1
        else
            log "⚠️ Lockfile orfe trobat (PID $OLD_PID mort). Netejant."
            rm -f "$LOCKFILE"
        fi
    fi
    echo $$ > "$LOCKFILE"
}

release_lock() {
    rm -f "$LOCKFILE"
    # Tornar tasques running a pending (per si el worker mor a mitges)
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/" && log "♻️ Retornada a pending: $(basename "$f")"
    done
    log "🛑 Worker aturat (PID $$)"
}

trap release_lock EXIT INT TERM

# ── Rotació de done/ ──────────────────────────────────────────────────────────
rotate_done() {
    local count=0
    find "$TASKS_DIR/done/" -name "*.json" -mtime +${DONE_RETENTION_DAYS} -type f 2>/dev/null | while read -r old; do
        rm -f "$old"
        count=$((count + 1))
    done
    [ $count -gt 0 ] && log "🧹 Rotació: $count tasques antigues eliminades de done/"
}

# ── Resum diari ───────────────────────────────────────────────
daily_summary() {
    local new_day=$(date '+%Y-%m-%d')
    if [ "$new_day" != "$TODAY" ]; then
        local done_count=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$TODAY" -type f 2>/dev/null | wc -l)
        local fail_count=$(find "$TASKS_DIR/failed/" -name "*.json" -newermt "$TODAY" -type f 2>/dev/null | wc -l)
        log "📊 Resum dia $TODAY: $done_count completades, $fail_count fallides"
        TODAY="$new_day"
        reset_consecutive_errors
        rotate_done
    fi
}

# ── Llegir camp JSON (sense jq, compatible) ───────────────────────────────────
json_field() {
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$1" "$2" 2>/dev/null
}

# ── Comprovar si hi ha canvis reals al repositori ─────────────────────────────
check_real_changes() {
    cd "$PROJECT_DIR"
    # Comprovar fitxers nous o modificats (tracked + untracked)
    local changes=$(git diff --name-only 2>/dev/null | wc -l)
    local new_files=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l)
    local staged=$(git diff --cached --name-only 2>/dev/null | wc -l)
    local total=$((changes + new_files + staged))
    echo "$total"
}

# ── Detectar si l'output és només un pla sense execució ─────────────────────────
is_plan_only() {
    local output="$1"
    
    # Patrons que indiquen que s'ha generat un pla en lloc d'executar
    local plan_patterns=(
        "El pla és"
        "El pla proposa"
        "Els passos serien"
        "Els passos són"
        "Proposo els següents passos"
        "El meu pla"
        "Aquí tens el pla"
        "Plan:"
        "Steps:"
        "The plan is"
        "I would suggest"
        "Here's my plan"
        "Here is the plan"
        "I'll outline"
        "Let me outline"
        "Primer.*Segon.*Tercer"
        "Step 1.*Step 2.*Step 3"
        "1\. \*\*Crear"
        "1\. Crear.*2\. "
    )
    
    for pattern in "${plan_patterns[@]}"; do
        if echo "$output" | grep -qiE "$pattern"; then
            return 0  # És un pla
        fi
    done
    
    return 1  # No és un pla
}

# ── Validació específica per tipus de tasca ─────────────────────────────────────
validate_task_result() {
    local task_type="$1"
    local task_id="$2"
    local result="$3"
    local changes_count="$4"
    
    # Si hi ha canvis reals a git → vàlid sempre
    if [ "$changes_count" -gt 0 ]; then
        log "   ✓ Validació: $changes_count fitxers nous/modificats detectats"
        return 0
    fi
    
    # Si no hi ha canvis, comprovar si és un pla sense acció
    if is_plan_only "$result"; then
        log "   ✗ Validació: Output és un PLA sense execució real"
        return 1
    fi
    
    # Tasques de traducció: comprovar que el directori de l'obra existeix
    if [ "$task_type" = "translate" ] || [ "$task_type" = "retranslation" ]; then
        log "   ✗ Validació: Traducció sense fitxers nous creats"
        return 1
    fi

    # Tasques de fetch: comprovar que s'ha creat original.md
    if [ "$task_type" = "fetch" ]; then
        log "   ✗ Validació: Fetch sense fitxers nous creats (original.md no generat)"
        return 1
    fi

    # Tasques de fix: comprovar canvis
    if [ "$task_type" = "fix" ]; then
        log "   ✗ Validació: Fix sense canvis detectats"
        return 1
    fi
    
    # Per code-review, supervisió, etc. → acceptar text com a resultat vàlid
    if [ "$task_type" = "review" ] || [ "$task_type" = "supervision" ] || [ "$task_type" = "test" ]; then
        log "   ✓ Validació: Tasca de tipus '$task_type' — output textual acceptable"
        return 0
    fi
    
    # Per altres tipus: si no hi ha canvis però tampoc és un pla, acceptar amb warning
    log "   ⚠ Validació: Cap canvi detectat però output no sembla un pla. Acceptant amb warning."
    return 0
}

# ── Executar tasca amb Venice AI ────────────────────────────────────────────────
run_task() {
    local instruction="$1"
    local result=""
    local exit_code=1

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔧 DEBUG: Llançant Venice AI (model=$VENICE_MODEL, timeout=$TASK_TIMEOUT)" >> "$LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔧 DEBUG: Instrucció: ${instruction:0:120}..." >> "$LOG"

    # IMPORTANT: Afegir prefix anti-pla a la instrucció
    local full_instruction="${EXEC_PREFIX}${instruction}"

    # Fitxer per a l'output en temps real
    local LIVE_LOG="/tmp/venice-live.txt"
    echo "[$(date '+%H:%M:%S')] ── Tasca: ${instruction:0:80}..." > "$LIVE_LOG"

    # Crida a Venice AI amb el model seleccionat dinàmicament
    # Utilitzem el model adequat per a cada tipus de tasca
    result=$(cd "$PROJECT_DIR" && timeout "$TASK_TIMEOUT" python3 "$VENICE_CLI" chat \
        --model "$VENICE_MODEL" \
        --max-tokens 16000 \
        --temperature 0.7 \
        --stream \
        "$full_instruction" 2>&1 | tee -a "$LIVE_LOG")
    exit_code=$?

    # 124 = timeout va matar el procés
    if [ $exit_code -eq 124 ]; then
        log "⏰ TIMEOUT després de ${TASK_TIMEOUT}s"
    fi

    # Detectar errors d'API
    if echo "$result" | grep -qi "authentication_error\|API key\|invalid.*key\|unauthorized"; then
        log "🔑 AUTH ERROR: Clau API Venice invàlida o expirada!"
        echo "AUTH_ERROR"
        return 98
    fi

    # Detectar rate limit
    if echo "$result" | grep -qi "rate.limit\|too many requests\|please wait\|try again\|capacity"; then
        log "⚠️ RATE LIMIT detectat!"
        echo "RATE_LIMIT_HIT"
        return 99
    fi

    echo "$result"
    return $exit_code
}

# ── Auto-commit si hi ha canvis ───────────────────────────────────────────────
auto_commit() {
    local task_id="$1"
    cd "$PROJECT_DIR"
    if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        git add -A 2>/dev/null
        git commit -m "auto: $task_id" 2>/dev/null
        git push origin main 2>/dev/null && log "📤 Auto-commit + push: $task_id" || log "⚠️ Push fallit (continuant)"
        return 0
    fi
    return 1
}

# ── Actualitzar retry count al JSON ──────────────────────────────────────────
bump_retry() {
    local task_file="$1"
    python3 -c "
import json, sys
f = sys.argv[1]
with open(f) as fh: d = json.load(fh)
d['retries'] = d.get('retries', 0) + 1
with open(f, 'w') as fh: json.dump(d, fh, indent=2)
print(d['retries'])
" "$task_file" 2>/dev/null
}

# ── Reforçar instrucció quan es detecta un pla ─────────────────────────
reinforce_instruction() {
    local original="$1"
    local attempt="$2"
    
    cat <<EOF
ATENCIÓ: L'intent anterior (#$attempt) va generar un pla en lloc d'executar les accions. Això NO és acceptable.

REGLES ESTRICTES:
- NO escriguis plans, llistes de passos, ni propostes
- CREA els fitxers directament amb la tool Write
- ESCRIU el contingut complet dins dels fitxers  
- FES mkdir per crear directoris
- CADA acció s'ha de FER, no descriure

TASCA ORIGINAL (EXECUTA-LA ARA):
$original
EOF
}

# =============================================================================
# MAIN LOOP
# =============================================================================
acquire_lock
check_diem_and_maybe_stop  # Comprovar DIEM abans de processar
log "🚀 Venice Worker iniciat (PID $$) — Selectorde Models Intel·ligent"
log "   Config: retries=$MAX_RETRIES, max_fails=$MAX_CONSECUTIVE_FAILS, timeout=${TASK_TIMEOUT}s"
log "   Models: traduccions→claude-opus/sonnet, fetch→deepseek-v3.2, metadata→glm-5"
log "   Validació post-execució + detecció plans + instruccions reforçades"

while true; do
    daily_summary

    # ── Safety: massa errors consecutius (≥3) ─────────────────────────────
    if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
        log "🛡️ $CONSECUTIVE_FAILS errors consecutius (llindar=$MAX_CONSECUTIVE_FAILS). Pausa d'emergència ${COOLDOWN_EMERGENCY}s."
        notify_discord_pause "$CONSECUTIVE_FAILS" "$COOLDOWN_EMERGENCY"
        sleep $COOLDOWN_EMERGENCY
        reset_consecutive_errors
        continue
    fi

    # ── Agafar tasca amb prioritat més alta (número més baix) ─────────────
    TASK=$(python3 -c "
import json, glob, sys
tasks = []
for f in glob.glob(sys.argv[1] + '/pending/*.json'):
    try:
        with open(f) as fh: d = json.load(fh)
        # Acceptar ambdós formats: priority (anglès) o prioritat (català)
        priority = d.get('priority') or d.get('prioritat', 5)
        tasks.append((priority, f))
    except: pass
if tasks:
    tasks.sort(key=lambda x: x[0])
    print(tasks[0][1])
" "$TASKS_DIR" 2>/dev/null)

    if [ -z "$TASK" ]; then
        sleep $IDLE_POLL
        continue
    fi

# ── Llegir tasca ──────────────────────────────────────────────────────
    TASK_ID=$(json_field "$TASK" "id")
    # Acceptar ambdós formats: instruction (anglès) o instruccio (català)
    INSTRUCTION=$(json_field "$TASK" "instruction")
    if [ -z "$INSTRUCTION" ]; then
        INSTRUCTION=$(json_field "$TASK" "instruccio")
    fi
    # Acceptar ambdós formats: type (anglès) o tipus (català)
    TASK_TYPE=$(json_field "$TASK" "type")
    if [ -z "$TASK_TYPE" ]; then
        TASK_TYPE=$(json_field "$TASK" "tipus")
    fi
    # Llegir model recomanat (si existeix)
    MODEL_RECOMANAT=$(json_field "$TASK" "model_recomanat")
    # Llegir ruta de l'obra (per a tasques de traducció)
    OBRA=$(json_field "$TASK" "obra")
    RETRIES=$(json_field "$TASK" "retries")
    RETRIES=${RETRIES:-0}
    TASK_TYPE=${TASK_TYPE:-unknown}

    if [ -z "$TASK_ID" ] || [ -z "$INSTRUCTION" ]; then
        log "⚠️ Tasca malformada: $(basename "$TASK"). Movent a failed/"
        mv "$TASK" "$TASKS_DIR/failed/"
        continue
    fi

    # ── Seleccionar model segons tipus de tasca ──────────────────────────────
    VENICE_MODEL=$(select_model "$TASK_TYPE" "$INSTRUCTION" "$MODEL_RECOMANAT")
    log "📊 Model seleccionat: $VENICE_MODEL (tipus=$TASK_TYPE, recomanat=$MODEL_RECOMANAT)"

    TASK_BASENAME=$(basename "$TASK")
    log "═══════════════════════════════════════════════════════════════════════════"
    log "▶ Executant: $TASK_ID (tipus=$TASK_TYPE, model=$VENICE_MODEL, intent $((RETRIES + 1))/$MAX_RETRIES)"

    # Moviment atòmic: verificar que el fitxer encara existeix abans de moure
    # (evita race condition amb heartbeat que pot moure fitxers simultàniament)
    if [ ! -f "$TASK" ]; then
        log "⚠️ Tasca ja no existeix a pending/ (moguda per heartbeat?). Saltant."
        continue
    fi
    if ! mv -n "$TASK" "$TASKS_DIR/running/$TASK_BASENAME" 2>/dev/null; then
        log "⚠️ No s'ha pogut moure la tasca a running/ (race condition). Saltant."
        continue
    fi
    # Verificar que el mv ha funcionat
    if [ ! -f "$TASKS_DIR/running/$TASK_BASENAME" ]; then
        log "⚠️ Fitxer no trobat a running/ després de mv. Saltant."
        continue
    fi
    START_TIME=$(date +%s)
    
    # Snapshot de l'estat git ABANS d'executar
    cd "$PROJECT_DIR"
    GIT_BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")

    # ── Determinar instrucció (reforçada si és retry per pla) ─────────
    if [ "$RETRIES" -gt 0 ]; then
        # Comprovar si l'últim intent va ser un pla (guardem flag al JSON)
        WAS_PLAN=$(json_field "$TASKS_DIR/running/$TASK_BASENAME" "last_was_plan")
        if [ "$WAS_PLAN" = "true" ] || [ "$WAS_PLAN" = "True" ]; then
            EFFECTIVE_INSTRUCTION=$(reinforce_instruction "$INSTRUCTION" "$RETRIES")
            log "   📝 Instrucció reforçada (intent anterior va ser un pla)"
        else
            EFFECTIVE_INSTRUCTION="$INSTRUCTION"
        fi
    else
        EFFECTIVE_INSTRUCTION="$INSTRUCTION"
    fi

    # ── Executar ──────────────────────────────────────────────────────────
    # Detectar si és tasca de traducció per executar amb script dedicat
    if echo "$TASK_TYPE" | grep -qiE "translate|translation|retranslate|fix-translate|fix-translation"; then
        log "   📖 Tasca de traducció detectada. Usant traduir_venice.py"
        
        # Determinar si és "continuar"
        IS_CONTINUAR="false"
        if echo "$INSTRUCTION" | grep -qi "continuar\|reprendre\|reanudar"; then
            IS_CONTINUAR="true"
        fi
        
        # Verificar que tenim la ruta de l'obra
        if [ -z "$OBRA" ]; then
            log "   ⚠️ Error: Tasca de traducció sense camp 'obra'. Intentant extraure de la instrucció..."
            # Intentar extraure la ruta de la instrucció
            OBRA=$(echo "$INSTRUCTION" | grep -oE "obres/[^ ]+" | head -1)
        fi
        
        if [ -n "$OBRA" ]; then
            RESULT=$(run_translate_task "$OBRA" "$VENICE_MODEL" "$IS_CONTINUAR")
            EXIT=$?
        else
            log "   ❌ Error: No s'ha pogut determinar la ruta de l'obra. Cridant Venice directament..."
            RESULT=$(run_task "$EFFECTIVE_INSTRUCTION")
            EXIT=$?
        fi
    elif echo "$TASK_TYPE" | grep -qiE "fetch|fix-fetch"; then
        # ── Tasca de fetch: descarregar URL ──────────────────────────────
        log "   📥 Tasca de fetch detectada. Buscant URL..."
        
        # Extreure URL del JSON o de la instrucció
        FETCH_URL=$(json_field "$TASKS_DIR/running/$TASK_BASENAME" "url")
        FETCH_OUTPUT=$(json_field "$TASKS_DIR/running/$TASK_BASENAME" "output")
        
        # Si no hi ha URL al JSON, cercar a la instrucció
        if [ -z "$FETCH_URL" ]; then
            FETCH_URL=$(echo "$INSTRUCTION" | grep -oE 'https?://[^[:space:]"'"'"']+' | head -1)
        fi
        
        # Si no hi ha output, usar obrap.path/original.md
        if [ -z "$FETCH_OUTPUT" ] && [ -n "$OBRA" ]; then
            FETCH_OUTPUT="$OBRA/original.md"
        fi
        
        if [ -n "$FETCH_URL" ]; then
            log "   ✓ URL trobada: $FETCH_URL"
            log "   ✓ Output: $FETCH_OUTPUT"
            RESULT=$(run_fetch_task "$FETCH_URL" "$FETCH_OUTPUT")
            EXIT=$?
        else
            log "   ⚠️ No s'ha trobat URL a la tasca. Intentant amb Venice..."
            log "   ⚠️NOTA: Venice no pot descarregar URLs. La tasca probablement fallarà."
            RESULT=$(run_task "$EFFECTIVE_INSTRUCTION")
            EXIT=$?
        fi
    else
        # Tasca normal: cridar Venice directament
        RESULT=$(run_task "$EFFECTIVE_INSTRUCTION")
        EXIT=$?
    fi
    END_TIME=$(date +%s)
    DURATION=$(( END_TIME - START_TIME ))

    # ── Rate limit → pausar, tornar tasca a pending ──────────────────
    if [ $EXIT -eq 99 ] || echo "$RESULT" | grep -q "RATE_LIMIT_HIT"; then
        log "🛑 RATE LIMIT — Pausant 2 hores"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/" 2>/dev/null
        sleep 7200
        log "▶️ Reprenent després de rate limit"
        continue
    fi

    # ── Auth error → parar ───────────────────────────────────────────
    if [ $EXIT -eq 98 ]; then
        log "🔑 AUTH ERROR — Worker aturat. Comprova VENICE_API_KEY."
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/" 2>/dev/null
        exit 1
    fi

    # ── Max tokens (output truncat) → validar abans de completar ─────
    if echo "$RESULT" | grep -q "max.*token\|truncated\|cut off"; then
        CHANGES=$(check_real_changes)
        if [ "$CHANGES" -gt 0 ]; then
            log "🔄 Output truncat per $TASK_ID (${DURATION}s) — $CHANGES fitxers canviats → completant"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            reset_consecutive_errors
        else
            log "🔄 Output truncat per $TASK_ID (${DURATION}s) — SENSE canvis reals → failed"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_consecutive_errors
        fi
        sleep $COOLDOWN_OK
        continue
    fi

    if [ $EXIT -eq 0 ] && [ -n "$RESULT" ]; then
        # ── ÈXIT APARENT: Validar que s'ha fet feina real ─────────────
        CHANGES=$(check_real_changes)
        
        if validate_task_result "$TASK_TYPE" "$TASK_ID" "$RESULT" "$CHANGES"; then
            # ── ÈXIT CONFIRMAT ────────────────────────────────────────
            log "✅ $TASK_ID completat (${DURATION}s, $CHANGES fitxers canviats)"
            log "   Resultat: $(echo "$RESULT" | head -3 | tr '\n' ' ')"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
            auto_commit "$TASK_ID"
            reset_consecutive_errors
            sleep $COOLDOWN_OK
        else
            # ── PLA SENSE ACCIÓ: retry amb instrucció reforçada ───────
            log "⚠️ $TASK_ID: Venice va generar output però NO va executar res (${DURATION}s)"
            log "   Output (primeres 200 chars): $(echo "$RESULT" | head -5 | tr '\n' ' ' | cut -c1-200)"
            
            # Marcar al JSON que l'últim intent va ser un pla
            python3 -c "
import json, sys
f = sys.argv[1]
with open(f) as fh: d = json.load(fh)
d['last_was_plan'] = True
d['retries'] = d.get('retries', 0) + 1
with open(f, 'w') as fh: json.dump(d, fh, indent=2)
print(d['retries'])
" "$TASKS_DIR/running/$TASK_BASENAME" 2>/dev/null
            
            RETRIES_NOW=$(json_field "$TASKS_DIR/running/$TASK_BASENAME" "retries")
            
            if [ "${RETRIES_NOW:-0}" -lt "$MAX_RETRIES" ]; then
                BACKOFF=$(( COOLDOWN_FAIL * ${RETRIES_NOW:-1} ))
                log "   🔄 Retry $RETRIES_NOW/$MAX_RETRIES amb instrucció reforçada (espera ${BACKOFF}s)"
                mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
                sleep $BACKOFF
            else
                log "   ❌ $TASK_ID FALLIT definitiu: $MAX_RETRIES intents, tots plans sense acció"
                mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
                CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
                save_consecutive_errors
                sleep $COOLDOWN_FAIL
            fi
        fi

    else
        # ── FAIL: decidir retry o failed ──────────────────────────────
        RETRIES=$(bump_retry "$TASKS_DIR/running/$TASK_BASENAME")

        if [ "$RETRIES" -lt "$MAX_RETRIES" ]; then
            BACKOFF=$(( COOLDOWN_FAIL * RETRIES ))
            log "🔄 $TASK_ID fallit (intent $RETRIES/$MAX_RETRIES, exit=$EXIT, ${DURATION}s). Retry en ${BACKOFF}s"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
            sleep $BACKOFF
        else
            log "❌ $TASK_ID FALLIT definitiu ($MAX_RETRIES intents, exit=$EXIT, ${DURATION}s)"
            [ -n "$RESULT" ] && log "   Error: $(echo "$RESULT" | tail -3 | tr '\n' ' ')"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            save_consecutive_errors
            sleep $COOLDOWN_FAIL
        fi

    fi
done