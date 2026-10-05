#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# dev-worker.sh — Desenvolupament autònom d'Arion amb Claude Code
# ═══════════════════════════════════════════════════════════════════════════
# Quan la subscripció Claude (Pro) té quota lliure, agafa la següent tasca
# del backlog i la resol amb Claude Code. S'atura sol quan s'esgota el límit
# de la subscripció, quan s'acaba el backlog o quan hi ha massa errors.
#
# Treballa SEMPRE en una branca de desenvolupament (per defecte `auto/dev`),
# mai fa push. La fusió a `main` la decideix una persona.
#
# Ús:
#   bash dev-worker.sh            # una passada completa (fins a MAX_TASKS)
#   bash dev-worker.sh --once     # només una tasca
#   bash dev-worker.sh --dry-run  # mostra què faria, sense executar Claude
#   bash dev-worker.sh --status   # estat del sistema
#
# Variables d'entorn:
#   DEV_MODEL (opus|sonnet|haiku)   DEV_MAX_TASKS    DEV_MAX_TASK_SECS
#   DEV_MAX_TURNS                   DEV_BRANCH       DEV_COOLDOWN
#   DEV_MAX_CONSEC_FAILS            ARION_DIR
# ═══════════════════════════════════════════════════════════════════════════
set -uo pipefail

DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${ARION_DIR:-$HOME/biblioteca-universal-arion}"
BL="$DEV_DIR/backlog"
ST="$DEV_DIR/state"
LOG="$DEV_DIR/dev-worker.log"
LOCK="$ST/dev-worker.lock"
LAST_JSON="$ST/last-task.json"
LAST_ERR="$ST/last-task.err"
SETTINGS="$DEV_DIR/claude-dev-settings.json"
PROMPT_EXTRA="$DEV_DIR/PROMPT.md"
NODE_BIN="$HOME/.nvm/versions/node/v24.13.0/bin"
CLAUDE_BIN="$NODE_BIN/claude"

export PATH="$NODE_BIN:$PATH"
unset CLAUDECODE

BRANCH="${DEV_BRANCH:-auto/dev}"
MODEL="${DEV_MODEL:-opus}"
MAX_TURNS="${DEV_MAX_TURNS:-40}"
MAX_TASKS="${DEV_MAX_TASKS:-6}"
MAX_TASK_SECS="${DEV_MAX_TASK_SECS:-1800}"
MAX_CONSEC_FAILS="${DEV_MAX_CONSEC_FAILS:-3}"
COOLDOWN="${DEV_COOLDOWN:-20}"

DRY_RUN=0
ONCE=0

mkdir -p "$BL/pending" "$BL/running" "$BL/done" "$BL/failed" "$ST"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

notify() {
    local f="$PROJECT_DIR/sistema/automatitzacio/notificar.sh"
    if [ -f "$f" ]; then
        ( source "$f" >/dev/null 2>&1; command -v notify_info >/dev/null && notify_info "$1" "$2" ) 2>/dev/null || true
    fi
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --once)    ONCE=1 ;;
        --status)  exec bash "$DEV_DIR/status.sh" ;;
    esac
done

# ── Pany ──────────────────────────────────────────────────────────────────
if [ -f "$LOCK" ]; then
    OLD="$(cat "$LOCK" 2>/dev/null || echo "")"
    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
        log "Ja hi ha un dev-worker corrent (PID $OLD). Sortint."
        exit 0
    fi
    rm -f "$LOCK"
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# ── Quota ─────────────────────────────────────────────────────────────────
probe_status() {
    python3 "$DEV_DIR/quota-probe.py" >/dev/null 2>&1
    local rc=$?
    case $rc in
        0)  echo "FREE" ;;
        10) echo "LIMIT" ;;
        *)  echo "ERROR" ;;
    esac
}

# ── Branca ────────────────────────────────────────────────────────────────
ensure_branch() {
    cd "$PROJECT_DIR" || return 1
    if ! git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
        if ! git checkout -q -b "$BRANCH" 2>>"$LOG"; then
            log "ERROR: no s'ha pogut crear la branca $BRANCH"; return 1
        fi
        if [ -n "$(git status --porcelain)" ]; then
            git add -A 2>>"$LOG" && \
                git commit -q -m "[auto-dev] baseline: estat previ a l'automatització" 2>>"$LOG" || true
            log "Baseline commitejat a $BRANCH."
        fi
    else
        if ! git checkout -q "$BRANCH" 2>>"$LOG"; then
            log "ERROR: no s'ha pogut canviar a la branca $BRANCH (arbre brut?)"; return 1
        fi
    fi
    return 0
}

# ── Cua ───────────────────────────────────────────────────────────────────
# Tria la tasca pendent amb prioritat més baixa (1 = més urgent), saltant les
# que requereixen vistiplau humà.
next_task() {
    python3 - "$BL/pending" <<'PY'
import os, re, sys
d = sys.argv[1]
best = None
try:
    files = sorted(os.listdir(d))
except FileNotFoundError:
    files = []
for f in files:
    if not f.endswith(".md"):
        continue
    try:
        head = open(os.path.join(d, f), encoding="utf-8", errors="replace").read(600)
    except Exception:
        head = ""
    if re.search(r"requereix_vistiplau:\s*true", head, re.I):
        continue
    m = re.search(r"prioritat:\s*(\d+)", head)
    prio = int(m.group(1)) if m else 5
    key = (prio, f)
    if best is None or key < best[0]:
        best = (key, f)
if best:
    print(best[1])
PY
}

count_vistiplau() {
    grep -l -i 'requereix_vistiplau:[[:space:]]*true' "$BL/pending"/*.md 2>/dev/null | wc -l | tr -d ' '
}

jq_field() { # fitxer clau defecte
    python3 -c 'import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get(sys.argv[2], sys.argv[3]))
except Exception:
    print(sys.argv[3])' "$1" "$2" "${3:-}" 2>/dev/null
}

# ── Executar una tasca ────────────────────────────────────────────────────
# Retorna: 0 èxit · 1 error · 2 quota esgotada · 3 dry-run
run_task() {
    local task="$1" name="${1%.md}"
    local prompt before_head after_head rc

    log "▶ Tasca: $name"
    mv "$BL/pending/$task" "$BL/running/$task"

    prompt="$(cat "$PROMPT_EXTRA" 2>/dev/null)
────────────────────────────────────────────
$(cat "$BL/running/$task")"

    if [ "$DRY_RUN" = "1" ]; then
        log "[dry-run] Prompt preparat (${#prompt} caràcters). No s'executa Claude."
        mv "$BL/running/$task" "$BL/pending/$task"
        return 3
    fi

    before_head="$(git -C "$PROJECT_DIR" rev-parse HEAD)"

    timeout "$MAX_TASK_SECS" "$CLAUDE_BIN" -p "$prompt" \
        --model "$MODEL" \
        --max-turns "$MAX_TURNS" \
        --dangerously-skip-permissions \
        --settings "$SETTINGS" \
        --output-format json \
        --no-session-persistence \
        > "$LAST_JSON" 2>"$LAST_ERR"
    rc=$?

    local is_err subtype res cost
    is_err="$(jq_field "$LAST_JSON" is_error "")"
    subtype="$(jq_field "$LAST_JSON" subtype "")"
    res="$(jq_field "$LAST_JSON" result "" | head -c 500)"
    cost="$(jq_field "$LAST_JSON" total_cost_usd "")"

    # Límit de subscripció assolit dins la tasca → retorna a pending i atura.
    if printf '%s %s %s' "$res" "$subtype" "$is_err" | grep -qiE 'limit|429|quota|rate'; then
        log "⏸ Límit de subscripció detectat durant la tasca. Retorn a pending."
        mv "$BL/running/$task" "$BL/pending/$task"
        return 2
    fi

    # Commit dels canvis (si n'hi ha)
    after_head="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
    if [ -n "$(git -C "$PROJECT_DIR" status --porcelain)" ]; then
        git -C "$PROJECT_DIR" add -A 2>>"$LOG"
        git -C "$PROJECT_DIR" commit -q -m "[auto-dev] $name" 2>>"$LOG" || true
        log "  commit: $(git -C "$PROJECT_DIR" rev-parse --short HEAD) ($name)"
    fi

    if [ "$rc" = "0" ] && [ "$is_err" != "True" ] && [ "$is_err" != "true" ]; then
        echo "$res" > "$BL/done/$name.result.txt" 2>/dev/null || true
        mv "$BL/running/$task" "$BL/done/$task"
        log "  ✔ Feta (cost informatiu: $cost)"
        return 0
    fi

    mv "$BL/running/$task" "$BL/failed/$task"
    log "  ✘ Fallida (rc=$rc subtype=$subtype): $(echo "$res" | head -c 160)"
    return 1
}

# ── Bucle principal ───────────────────────────────────────────────────────
log "═══ dev-worker inici (branca=$BRANCH model=$MODEL) ═══"
if [ "$DRY_RUN" = "1" ]; then
    log "[dry-run] No es toca la branca ni es fa cap commit."
else
    ensure_branch || { log "Aturat: no s'ha pogut preparar la branca."; exit 1; }
fi

QUOTA_EXHAUSTED=0
CONSEC_FAILS=0
N=0

while :; do
    [ "$QUOTA_EXHAUSTED" = "1" ] && break
    if [ "$ONCE" = "0" ] && [ "$N" -ge "$MAX_TASKS" ]; then
        log "Assolit el màxim de tasques per passada ($MAX_TASKS)."
        break
    fi

    task="$(next_task)"
    if [ -z "$task" ]; then
        NV="$(count_vistiplau)"
        if [ "${NV:-0}" -gt 0 ]; then
            log "Backlog: cap tasca executable. $NV tasca(es) requereixen vistiplau humà."
        else
            log "Backlog buit. Res a fer."
        fi
        break
    fi

    st="$(probe_status)"
    if [ "$st" != "FREE" ]; then
        log "Quota de la subscripció: $st. No es treballa ara."
        [ "$st" = "LIMIT" ] && notify "Arion Dev — límit" "Quota Claude esgotada. Aturat fins al reset."
        break
    fi

    run_task "$task"
    r=$?
    case $r in
        0) CONSEC_FAILS=0; N=$((N+1)) ;;
        2) QUOTA_EXHAUSTED=1 ;;
        3) break ;;
        *) CONSEC_FAILS=$((CONSEC_FAILS+1)); N=$((N+1))
           if [ "$CONSEC_FAILS" -ge "$MAX_CONSEC_FAILS" ]; then
               log "⛔ $MAX_CONSEC_FAILS errors consecutius. Aturant."
               notify "Arion Dev — errors" "$MAX_CONSEC_FAILS errors seguits. Revisa els logs."
               break
           fi ;;
    esac

    [ "$ONCE" = "1" ] && break
    sleep "$COOLDOWN"
done

log "═══ dev-worker fi (tasques=$N, errors_seguits=$CONSEC_FAILS) ═══"
