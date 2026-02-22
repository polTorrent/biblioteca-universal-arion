#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# task-manager.sh — Gestionar la cua de tasques d'Arion
# Ús: bash task-manager.sh [add|list|cancel|status|clear]
# ═══════════════════════════════════════════════════════════════

TASKS_DIR="$HOME/.openclaw/workspace/tasks"
mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# ── Colors ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Afegir tasca ───────────────────────────────────────────
cmd_add() {
    local type="$1"
    local instruction="$2"
    
    if [ -z "$type" ] || [ -z "$instruction" ]; then
        echo "Ús: task-manager.sh add <type> <instruction> [params_json]"
        echo "Tipus: fix | test | code-review | translate | refactor | maintain"
        echo ""
        echo "Exemples:"
        echo "  task-manager.sh add test 'Executa tots els tests del projecte'"
        echo "  task-manager.sh add translate 'Tradueix el Tao Te King' '{\"autor\":\"Laozi\",\"titol\":\"Tao Te King\",\"llengua\":\"xinès\",\"categoria\":\"oriental\"}'"
        echo "  task-manager.sh add code-review 'Revisa agents/cercador_fonts.py'"
        echo "  task-manager.sh add fix 'Arregla ImportError a pipeline_v2.py'"
        return 1
    fi
    
    local params="${3:-{}}"
    local timestamp=$(date +%s)
    local slug=$(echo "$instruction" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g' | head -c 40)
    local task_id="${timestamp}_${type}_${slug}"
    
    # Prioritats per defecte
    local priority=3
    local max_duration=60
    case "$type" in
        fix)         priority=0; max_duration=30 ;;
        test)        priority=1; max_duration=30 ;;
        code-review) priority=2; max_duration=45 ;;
        translate)   priority=3; max_duration=90 ;;
        refactor)    priority=4; max_duration=60 ;;
        maintain)    priority=5; max_duration=20 ;;
    esac

    local task_file="$TASKS_DIR/pending/${task_id}.json"
    
    python3 << PYEOF
import json
task = {
    "id": "$task_id",
    "type": "$type",
    "priority": $priority,
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "pending",
    "params": $params,
    "instruction": """$instruction""",
    "max_duration_minutes": $max_duration,
    "retry_count": 0,
    "max_retries": 2,
    "depends_on": None,
    "result": None,
    "error": None,
    "started_at": None,
    "completed_at": None
}
with open("$task_file", 'w') as f:
    json.dump(task, f, indent=2, ensure_ascii=False)
PYEOF

    echo -e "${GREEN}✅ Tasca creada: $task_id${NC}"
    echo -e "   Tipus: $type | Prioritat: $priority | Max: ${max_duration}min"
}

# ── Afegir traducció (shortcut) ────────────────────────────
cmd_translate() {
    local autor="$1"
    local titol="$2"
    local llengua="${3:-grec}"
    local categoria="${4:-filosofia}"

    if [ -z "$autor" ] || [ -z "$titol" ]; then
        echo "Ús: task-manager.sh translate <autor> <títol> [llengua] [categoria]"
        echo "Exemples:"
        echo "  task-manager.sh translate 'Epictetus' 'Enchiridion' 'grec' 'filosofia'"
        echo "  task-manager.sh translate 'Kafka' 'La metamorfosi' 'alemany' 'novel·la'"
        echo "  task-manager.sh translate 'Laozi' 'Tao Te King' 'xinès' 'oriental'"
        return 1
    fi

    local params="{\"autor\":\"$autor\",\"titol\":\"$titol\",\"llengua\":\"$llengua\",\"categoria\":\"$categoria\"}"
    cmd_add "translate" "Tradueix '$titol' de $autor ($llengua) al català. Busca la font original, executa el pipeline V2 complet, genera la web i publica." "$params"
}

# ── Llistar cua ────────────────────────────────────────────
cmd_list() {
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    echo -e "${CYAN}  CUA DE TASQUES — Biblioteca Arion${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    echo ""

    # Running
    local running_count=$(ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)
    echo -e "${YELLOW}▶ EN EXECUCIÓ ($running_count):${NC}"
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] || continue
        python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
print(f'  🔄 [{t[\"type\"]}] {t[\"id\"]}')
print(f'     Iniciat: {t.get(\"started_at\", \"?\")}')
"
    done
    [ $running_count -eq 0 ] && echo "  (cap)"
    echo ""

    # Pending
    local pending_count=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
    echo -e "${BLUE}⏳ PENDENTS ($pending_count):${NC}"
    for f in $(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | head -10); do
        python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
prio = '🔴' if t['priority'] <= 1 else '🟡' if t['priority'] <= 3 else '🟢'
print(f'  {prio} P{t[\"priority\"]} [{t[\"type\"]}] {t[\"id\"]}')
print(f'       {t[\"instruction\"][:80]}...')
"
    done
    [ $pending_count -eq 0 ] && echo "  (cap)"
    [ $pending_count -gt 10 ] && echo -e "  ... i $((pending_count - 10)) més"
    echo ""

    # Done (últimes 5)
    local done_count=$(ls -1 "$TASKS_DIR/done/"*.json 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ COMPLETADES (últimes 5 de $done_count):${NC}"
    for f in $(ls -1t "$TASKS_DIR/done/"*.json 2>/dev/null | head -5); do
        python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
print(f'  ✅ [{t[\"type\"]}] {t[\"id\"]}')
print(f'     Completat: {t.get(\"completed_at\", \"?\")}')
"
    done
    [ $done_count -eq 0 ] && echo "  (cap)"
    echo ""

    # Failed (últimes 5)
    local failed_count=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)
    echo -e "${RED}❌ FALLADES ($failed_count):${NC}"
    for f in $(ls -1t "$TASKS_DIR/failed/"*.json 2>/dev/null | head -5); do
        python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
err = (t.get('error') or 'desconegut')[:80]
print(f'  ❌ [{t[\"type\"]}] {t[\"id\"]}')
print(f'     Error: {err}')
"
    done
    [ $failed_count -eq 0 ] && echo "  (cap)"
}

# ── Cancel·lar tasca ───────────────────────────────────────
cmd_cancel() {
    local pattern="$1"
    if [ -z "$pattern" ]; then
        echo "Ús: task-manager.sh cancel <task_id_o_patró>"
        return 1
    fi

    local found=0
    for f in "$TASKS_DIR/pending/"*"$pattern"*.json; do
        [ -f "$f" ] || continue
        rm -f "$f"
        echo -e "${RED}🗑️ Eliminada: $(basename "$f" .json)${NC}"
        found=1
    done
    [ $found -eq 0 ] && echo "No s'ha trobat cap tasca amb '$pattern'"
}

# ── Status del worker ──────────────────────────────────────
cmd_status() {
    echo -e "${CYAN}═══ STATUS ═══${NC}"
    
    local status_file="/tmp/claude-worker-status.txt"
    if [ -f "$status_file" ]; then
        echo -e "Worker: ${GREEN}$(cat "$status_file")${NC}"
    else
        echo -e "Worker: ${RED}NO ACTIU${NC}"
    fi
    
    local lock_file="$TASKS_DIR/worker.lock"
    if [ -f "$lock_file" ]; then
        local pid=$(cat "$lock_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "PID: ${GREEN}$pid (actiu)${NC}"
        else
            echo -e "PID: ${RED}$pid (mort)${NC}"
        fi
    fi
    
    echo ""
    echo "Pending: $(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)"
    echo "Running: $(ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)"
    echo "Done:    $(ls -1 "$TASKS_DIR/done/"*.json 2>/dev/null | wc -l)"
    echo "Failed:  $(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)"
    
    echo ""
    local report="/tmp/claude-worker-report.txt"
    if [ -f "$report" ]; then
        echo -e "${CYAN}Últims reports:${NC}"
        tail -5 "$report"
    fi
}

# ── Netejar cua ────────────────────────────────────────────
cmd_clear() {
    local target="${1:-done}"
    case "$target" in
        done)
            rm -f "$TASKS_DIR/done/"*.json
            echo -e "${GREEN}Netejades tasques completades${NC}"
            ;;
        failed)
            rm -f "$TASKS_DIR/failed/"*.json
            echo -e "${GREEN}Netejades tasques fallades${NC}"
            ;;
        pending)
            rm -f "$TASKS_DIR/pending/"*.json
            echo -e "${GREEN}Netejades tasques pendents${NC}"
            ;;
        all)
            rm -f "$TASKS_DIR/pending/"*.json "$TASKS_DIR/done/"*.json "$TASKS_DIR/failed/"*.json
            echo -e "${GREEN}Tota la cua netejada${NC}"
            ;;
        *)
            echo "Ús: task-manager.sh clear [done|failed|pending|all]"
            ;;
    esac
}

# ── Batch: afegir múltiples tasques de revisió ─────────────
cmd_review_all() {
    echo -e "${CYAN}Generant tasques de code-review per tots els agents...${NC}"
    local project="$HOME/biblioteca-universal-arion"
    
    for f in "$project"/agents/*.py; do
        [ -f "$f" ] || continue
        local basename=$(basename "$f")
        cmd_add "code-review" "Revisa $basename: busca bugs, millora typing, verifica que els imports funcionen, i que segueixi les convencions del projecte." "{\"file\": \"agents/$basename\"}"
    done
    
    # Pipeline
    for f in "$project"/pipeline/*.py; do
        [ -f "$f" ] || continue
        local basename=$(basename "$f")
        cmd_add "code-review" "Revisa pipeline/$basename: verifica funcionalitat, imports, i integració amb la resta del sistema." "{\"file\": \"pipeline/$basename\"}"
    done
    
    # Scripts
    for f in "$project"/scripts/*.py; do
        [ -f "$f" ] || continue
        local basename=$(basename "$f")
        cmd_add "code-review" "Revisa scripts/$basename: verifica que funcioni correctament i que segueixi les convencions." "{\"file\": \"scripts/$basename\"}"
    done
    
    echo -e "${GREEN}✅ Tasques de revisió generades${NC}"
}

# ── Entry point ────────────────────────────────────────────
case "${1:-help}" in
    add)       shift; cmd_add "$@" ;;
    translate) shift; cmd_translate "$@" ;;
    list|ls)   cmd_list ;;
    cancel|rm) shift; cmd_cancel "$@" ;;
    status|st) cmd_status ;;
    clear)     shift; cmd_clear "$@" ;;
    review-all) cmd_review_all ;;
    help|*)
        echo "task-manager.sh — Gestió de la cua de tasques Arion"
        echo ""
        echo "Comandes:"
        echo "  add <type> <instruction> [params]  Afegir tasca"
        echo "  translate <autor> <títol> [ll] [cat] Afegir traducció"
        echo "  list / ls                           Llistar cua"
        echo "  status / st                         Estat del worker"
        echo "  cancel <patró>                      Cancel·lar tasca"
        echo "  clear [done|failed|pending|all]     Netejar cua"
        echo "  review-all                          Generar revisió de tot el codi"
        echo "  help                                Aquesta ajuda"
        ;;
esac
