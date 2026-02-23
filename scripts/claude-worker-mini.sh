#!/bin/bash
# =============================================================================
# claude-worker-mini.sh v2 — Worker autònom amb safety limits
# =============================================================================
# Millores sobre v1:
#   - Retry amb backoff (fins a 3 intents per tasca)
#   - Safety limits (max errors consecutius, max tasques/dia)
#   - Rotació automàtica de done/ (neteja >7 dies)
#   - Logging millorat (durada, resum diari)
#   - Health check amb timeout per tasca
#   - Lockfile robust (evita workers duplicats)
# =============================================================================

set -euo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
LOG="$HOME/claude-worker.log"
LOCKFILE="$TASKS_DIR/worker.lock"

MAX_RETRIES=3                # Intents per tasca abans de marcar com failed
MAX_CONSECUTIVE_FAILS=5      # Pausa llarga si N tasques seguides fallen
MAX_TASKS_PER_DAY=50         # Límit diari de tasques
COOLDOWN_OK=30               # Segons entre tasques OK
COOLDOWN_FAIL=60             # Segons després d'un fail
COOLDOWN_EMERGENCY=600       # 10 min pausa si massa errors
TASK_TIMEOUT=1200            # 20 min timeout per tasca (kill si supera)
DONE_RETENTION_DAYS=7        # Dies que es guarden les tasques completades
IDLE_POLL=60                 # Segons entre polls quan no hi ha tasques

# ── Inicialització ────────────────────────────────────────────────────────────
source ~/.nvm/nvm.sh 2>/dev/null
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# Comptadors
CONSECUTIVE_FAILS=0
TODAY=$(date '+%Y-%m-%d')
TASKS_TODAY=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

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

# ── Resum diari ───────────────────────────────────────────────────────────────
daily_summary() {
    local new_day=$(date '+%Y-%m-%d')
    if [ "$new_day" != "$TODAY" ]; then
        local done_count=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$TODAY" -type f 2>/dev/null | wc -l)
        local fail_count=$(find "$TASKS_DIR/failed/" -name "*.json" -newermt "$TODAY" -type f 2>/dev/null | wc -l)
        log "📊 Resum dia $TODAY: $done_count completades, $fail_count fallides"
        TODAY="$new_day"
        TASKS_TODAY=0
        CONSECUTIVE_FAILS=0
        rotate_done
    fi
}

# ── Llegir camp JSON (sense jq, compatible) ───────────────────────────────────
json_field() {
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$1" "$2" 2>/dev/null
}

# ── Executar tasca amb timeout ────────────────────────────────────────────────
run_task() {
    local instruction="$1"
    local result=""
    local exit_code=1

    # timeout mata el procés si supera TASK_TIMEOUT
      result=$(cd "$PROJECT_DIR" && unset CLAUDECODE && timeout "$TASK_TIMEOUT" claude -p "$instruction" \
        --max-turns 10 \
        --allowedTools "Edit" "Write" \
        "Bash(cat:*)" "Bash(grep:*)" "Bash(ls:*)" "Bash(find:*)" \
        "Bash(python3:*)" "Bash(python:*)" "Bash(pip:*)" "Bash(pip3:*)" \
        "Bash(git add:*)" "Bash(git commit:*)" "Bash(git push:*)" \
        "Bash(head:*)" "Bash(tail:*)" "Bash(wc:*)" "Bash(mkdir:*)" \
        "Bash(sed:*)" "Bash(cp:*)" "Bash(mv:*)" "Bash(rm:*)" \
        --output-format text 2>&1) && exit_code=0 || exit_code=$?

    # 124 = timeout va matar el procés
    if [ $exit_code -eq 124 ]; then
        log "⏰ TIMEOUT després de ${TASK_TIMEOUT}s"
    fi

    # Detectar rate limit
    if echo "$result" | grep -qi "rate.limit\|too many requests\|usage.limit\|please wait\|capacity\|try again in\|exceeded.*limit\|limit.*exceeded"; then
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

# =============================================================================
# MAIN LOOP
# =============================================================================
acquire_lock
log "🚀 Worker mini v2 iniciat (PID $$)"
log "   Config: retries=$MAX_RETRIES, max_fails=$MAX_CONSECUTIVE_FAILS, max_day=$MAX_TASKS_PER_DAY, timeout=${TASK_TIMEOUT}s"

while true; do
    daily_summary

    # ── Safety: límit diari ───────────────────────────────────────────────
    if [ $TASKS_TODAY -ge $MAX_TASKS_PER_DAY ]; then
        log "🛡️ Límit diari assolit ($MAX_TASKS_PER_DAY). Esperant fins demà."
        sleep 3600
        continue
    fi

    # ── Safety: massa errors consecutius ──────────────────────────────────
    if [ $CONSECUTIVE_FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
        log "🛡️ $CONSECUTIVE_FAILS errors consecutius. Pausa d'emergència ${COOLDOWN_EMERGENCY}s."
        sleep $COOLDOWN_EMERGENCY
        CONSECUTIVE_FAILS=0
        continue
    fi

    # ── Agafar primera tasca ──────────────────────────────────────────────
    TASK=$(ls -1t "$TASKS_DIR/pending/"*.json 2>/dev/null | head -1)

    if [ -z "$TASK" ]; then
        sleep $IDLE_POLL
        continue
    fi

    # ── Llegir tasca ──────────────────────────────────────────────────────
    TASK_ID=$(json_field "$TASK" "id")
    INSTRUCTION=$(json_field "$TASK" "instruction")
    RETRIES=$(json_field "$TASK" "retries")
    RETRIES=${RETRIES:-0}

    if [ -z "$TASK_ID" ] || [ -z "$INSTRUCTION" ]; then
        log "⚠️ Tasca malformada: $(basename "$TASK"). Movent a failed/"
        mv "$TASK" "$TASKS_DIR/failed/"
        continue
    fi

    TASK_BASENAME=$(basename "$TASK")
    log "═══════════════════════════════════════════════════"
    log "▶ Executant: $TASK_ID (intent $((RETRIES + 1))/$MAX_RETRIES)"
    mv "$TASK" "$TASKS_DIR/running/"
    START_TIME=$(date +%s)

    # ── Executar ──────────────────────────────────────────────────────────
    RESULT=$(run_task "$INSTRUCTION")
    EXIT=$?
    END_TIME=$(date +%s)
    DURATION=$(( END_TIME - START_TIME ))

    # ── Rate limit → pausar, tornar tasca a pending ──────────────────
    if [ $EXIT -eq 99 ] || echo "$RESULT" | grep -q "RATE_LIMIT_HIT"; then
        log "🛑 RATE LIMIT — Pausant 30 minuts"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/" 2>/dev/null
        sleep 1800
        log "▶️ Reprenent després de rate limit"
        continue
    fi

    # ── Max turns → completar (Claude va fer feina) ──────────────────
    if echo "$RESULT" | grep -q "Reached max turns"; then
        log "🔄 Max turns per $TASK_ID (${DURATION}s) — completant"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
        auto_commit "$TASK_ID"
        CONSECUTIVE_FAILS=0
        TASKS_TODAY=$((TASKS_TODAY + 1))
        sleep $COOLDOWN_OK
        continue
    fi

    if [ $EXIT -eq 0 ] && [ -n "$RESULT" ]; then
        # ── ÈXIT ──────────────────────────────────────────────────────
        log "✅ $TASK_ID completat (${DURATION}s)"
        log "   Resultat: $(echo "$RESULT" | head -3 | tr '\n' ' ')"
        mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/done/"
        auto_commit "$TASK_ID"
        CONSECUTIVE_FAILS=0
        TASKS_TODAY=$((TASKS_TODAY + 1))
        sleep $COOLDOWN_OK

    else
        # ── FAIL: decidir retry o failed ──────────────────────────────
        RETRIES=$(bump_retry "$TASKS_DIR/running/$TASK_BASENAME")

        if [ "$RETRIES" -lt "$MAX_RETRIES" ]; then
            # Retry: tornar a pending amb backoff
            BACKOFF=$(( COOLDOWN_FAIL * RETRIES ))
            log "🔄 $TASK_ID fallit (intent $RETRIES/$MAX_RETRIES, exit=$EXIT, ${DURATION}s). Retry en ${BACKOFF}s"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/pending/"
            sleep $BACKOFF
        else
            # Exhaurit retries: marcar com failed definitivament
            log "❌ $TASK_ID FALLIT definitiu ($MAX_RETRIES intents, exit=$EXIT, ${DURATION}s)"
            [ -n "$RESULT" ] && log "   Error: $(echo "$RESULT" | tail -3 | tr '\n' ' ')"
            mv "$TASKS_DIR/running/$TASK_BASENAME" "$TASKS_DIR/failed/"
            CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
            sleep $COOLDOWN_FAIL
        fi

        TASKS_TODAY=$((TASKS_TODAY + 1))
    fi
done
