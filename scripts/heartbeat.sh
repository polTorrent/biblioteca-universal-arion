#!/bin/bash
# =============================================================================
# heartbeat.sh v2 — Generador intel·ligent de tasques
# =============================================================================
# Analitza l'estat REAL del projecte i genera tasques basant-se en:
#   1. Obres pendents de traducció (obra-queue.json)
#   2. Traduccions sense revisar (obres/ sense review)
#   3. Codi Python sense code-review recent
#   4. Web desactualitzada (docs/ vs obres/)
#   5. Tests que fallen o no existeixen
#   6. Tasques fallides que es poden reintentar
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
TASK_MANAGER="$PROJECT/scripts/task-manager.sh"
QUEUE="$PROJECT/config/obra-queue.json"
LOG="$HOME/claude-worker.log"
MAX_PENDING=5          # No afegir més si ja hi ha 5 pendents
MIN_DIEM_RESERVE=2     # Reserva mínima de DIEM

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HEARTBEAT] $1" | tee -a "$LOG"; }

count_pending() {
    ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l
}

count_running() {
    ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l
}

task_exists() {
    # Comprova si ja existeix una tasca pendent/running amb paraula clau
    local keyword="$1"
    grep -rl "$keyword" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null | head -1
}

add_task() {
    local type="$1"
    local instruction="$2"
    if [ "$(count_pending)" -ge "$MAX_PENDING" ]; then
        log "   ⏸️ Cua plena ($MAX_PENDING pendents). No s'afegeix."
        return 1
    fi
    bash "$TASK_MANAGER" add "$type" "$instruction" 2>/dev/null
    log "   ➕ Tasca afegida [$type]: $(echo "$instruction" | head -c 80)..."
    return 0
}

# ── Comprovació DIEM ──────────────────────────────────────────────────────────
check_diem() {
    local balance
    balance=$(python3 ~/.openclaw/workspace/skills/venice-ai/scripts/venice.py balance 2>/dev/null | grep -oP '[\d.]+' | head -1)
    if [ -n "$balance" ]; then
        local ok=$(python3 -c "print('yes' if float('$balance') >= $MIN_DIEM_RESERVE else 'no')" 2>/dev/null)
        if [ "$ok" = "no" ]; then
            log "⚠️ DIEM baix ($balance). No es generen tasques."
            return 1
        fi
        log "💰 DIEM: $balance (OK)"
    fi
    return 0
}

# ── Comprovació Worker ────────────────────────────────────────────────────────
check_worker() {
    if ! pgrep -f "claude-worker-mini" > /dev/null 2>&1; then
        log "⚠️ Worker NO actiu. Reiniciant..."
        cd "$PROJECT"
        rm -f "$TASKS_DIR/worker.lock"
        # Tornar running a pending
        for f in "$TASKS_DIR/running/"*.json; do
            [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/"
        done
        tmux kill-session -t worker 2>/dev/null
        tmux new-session -d -s worker "cd $PROJECT && bash scripts/claude-worker-mini.sh"
        log "✅ Worker reiniciat"
    else
        log "✅ Worker actiu"
    fi
}

# =============================================================================
# ANALITZADORS D'ESTAT
# =============================================================================

# ── 1. Obres pendents de traducció ───────────────────────────────────────────
check_translations() {
    log "📚 Analitzant obres pendents de traducció..."
    local added=0

    if [ ! -f "$QUEUE" ]; then
        log "   ⚠️ obra-queue.json no trobat"
        return 0
    fi

    # Llegir obres amb status "pending" o "in_progress"
    python3 -c "
import json, sys, os

queue = json.load(open('$QUEUE'))
project = '$PROJECT'

for obra in queue.get('obres', []):
    status = obra.get('status', 'pending')
    if status in ('done', 'skip'):
        continue
    
    autor = obra['autor']
    titol = obra['titol']
    llengua = obra.get('llengua', 'desconeguda')
    categoria = obra.get('categoria', 'filosofia')
    slug_autor = autor.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a')
    slug_titol = titol.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a').replace('í', 'i')
    
    # Comprovar si ja existeix la traducció
    obra_dir = os.path.join(project, 'obres', categoria, slug_autor, slug_titol)
    has_translation = os.path.isdir(obra_dir) and any(
        f.endswith('.md') or f.endswith('.txt') 
        for f in os.listdir(obra_dir) if 'traduccio' in f.lower() or 'traducció' in f.lower() or 'catala' in f.lower()
    ) if os.path.isdir(obra_dir) else False
    
    # Comprovar si ja existeix alguna cosa a obres/
    has_dir = os.path.isdir(obra_dir)
    has_files = len(os.listdir(obra_dir)) > 0 if has_dir else False
    
    if has_translation:
        # Ja traduïda — comprovar si cal review
        print(f'REVIEW|{autor}|{titol}|{categoria}|{obra_dir}')
    elif has_files:
        # Començada però no acabada
        print(f'CONTINUE|{autor}|{titol}|{llengua}|{categoria}')
    else:
        # No començada
        print(f'NEW|{autor}|{titol}|{llengua}|{categoria}')
" 2>/dev/null | while IFS='|' read -r action autor titol extra1 extra2; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        case "$action" in
            NEW)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "Tradueix '$titol' de $autor del $extra1 al català. Busca el text original a Perseus, Gutenberg o Wikisource. Guarda a obres/$extra2/. Inclou metadata.yml amb autor, títol, llengua original, i data."
                    added=$((added + 1))
                fi
                ;;
            CONTINUE)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "Continua la traducció de '$titol' de $autor. Revisa obres/$extra2/ per veure què falta. Completa la traducció i verifica qualitat."
                    added=$((added + 1))
                fi
                ;;
            REVIEW)
                if ! task_exists "Revisa.*$titol" > /dev/null 2>&1; then
                    add_task "review" "Revisa la traducció de '$titol' de $autor a $extra2. Comprova: fidelitat al text original, qualitat del català, consistència del glossari, format correcte. Reporta puntuació i suggeriments."
                    added=$((added + 1))
                fi
                ;;
        esac
    done

    log "   📚 $added tasques de traducció generades"
}

# ── 2. Code reviews pendents ─────────────────────────────────────────────────
check_code_reviews() {
    log "🔍 Analitzant codi sense revisar..."
    local added=0

    # Buscar fitxers Python modificats recentment (últims 7 dies) sense review
    find "$PROJECT/agents" "$PROJECT/scripts" "$PROJECT/utils" -name "*.py" -mtime -7 -type f 2>/dev/null | while read -r pyfile; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        local relpath="${pyfile#$PROJECT/}"
        local basename=$(basename "$pyfile")
        
        # Comprovar si ja hi ha una review recent (done en últims 7 dies)
        local recent_review=$(find "$TASKS_DIR/done/" -name "*.json" -mtime -7 -type f 2>/dev/null | \
            xargs grep -l "$basename" 2>/dev/null | head -1)
        
        if [ -z "$recent_review" ] && ! task_exists "$basename" > /dev/null 2>&1; then
            add_task "code-review" "Revisa $relpath: verifica imports, busca bugs, millora typing i error handling. Si trobes problemes, arregla'ls directament."
            added=$((added + 1))
        fi
    done

    log "   🔍 $added code-reviews generades"
}

# ── 3. Web desactualitzada ────────────────────────────────────────────────────
check_web() {
    log "🌐 Comprovant si la web necessita regenerar..."
    
    local docs_time=0
    local obres_time=0
    
    # Última modificació de docs/
    if [ -d "$PROJECT/docs" ]; then
        docs_time=$(find "$PROJECT/docs" -name "*.html" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
        docs_time=${docs_time:-0}
    fi
    
    # Última modificació d'obres/
    if [ -d "$PROJECT/obres" ]; then
        obres_time=$(find "$PROJECT/obres" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
        obres_time=${obres_time:-0}
    fi
    
    if [ "$obres_time" -gt "$docs_time" ] 2>/dev/null; then
        if ! task_exists "build.py\|regenera.*web\|actualitza.*web" > /dev/null 2>&1; then
            add_task "maintenance" "La web està desactualitzada. Executa 'python3 scripts/build.py' per regenerar docs/ amb les últimes traduccions. Fes commit i push."
            log "   🌐 Tasca de regeneració web afegida"
        fi
    else
        log "   🌐 Web actualitzada (OK)"
    fi
}

# ── 4. Tests ──────────────────────────────────────────────────────────────────
check_tests() {
    log "🧪 Comprovant tests..."
    
    # Si fa més de 3 dies que no s'han passat tests
    local last_test=$(find "$TASKS_DIR/done/" -name "*.json" -type f 2>/dev/null | \
        xargs grep -l "pytest\|test" 2>/dev/null | \
        xargs ls -1t 2>/dev/null | head -1)
    
    local needs_test=false
    if [ -z "$last_test" ]; then
        needs_test=true
    else
        local test_age=$(( ($(date +%s) - $(stat -c %Y "$last_test" 2>/dev/null || echo 0)) / 86400 ))
        [ "$test_age" -gt 3 ] && needs_test=true
    fi
    
    if $needs_test && ! task_exists "pytest" > /dev/null 2>&1; then
        add_task "test" "Executa 'python3 -m pytest tests/ -v' i reporta resultats. Si hi ha errors, intenta arreglar-los. Si falten dependències, instal·la-les amb pip3."
        log "   🧪 Tasca de tests afegida"
    else
        log "   🧪 Tests recents (OK)"
    fi
}

# ── 5. Tasques fallides recuperables ──────────────────────────────────────────
check_failed() {
    log "♻️ Comprovant tasques fallides recuperables..."
    local recovered=0
    
    # Buscar tasques amb menys de MAX_RETRIES que van fallar fa >1h
    find "$TASKS_DIR/failed/" -name "*.json" -mmin +60 -type f 2>/dev/null | head -3 | while read -r failed; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        local retries=$(python3 -c "import json; print(json.load(open('$failed')).get('retries',0))" 2>/dev/null)
        retries=${retries:-0}
        
        # Només recuperar si va fallar menys de 2 vegades (potser era un error temporal)
        if [ "$retries" -lt 2 ]; then
            # Reset retries i tornar a pending
            python3 -c "
import json
f = '$failed'
with open(f) as fh: d = json.load(fh)
d['retries'] = 0
d['recovered'] = True
with open(f, 'w') as fh: json.dump(d, fh, indent=2)
" 2>/dev/null
            mv "$failed" "$TASKS_DIR/pending/"
            log "   ♻️ Recuperada: $(basename "$failed")"
            recovered=$((recovered + 1))
        fi
    done
    
    log "   ♻️ $recovered tasques recuperades"
}

# ── 6. Actualitzar obra-queue.json ────────────────────────────────────────────
update_queue_status() {
    log "📋 Actualitzant estat obra-queue.json..."
    
    python3 -c "
import json, os

queue_path = '$QUEUE'
project = '$PROJECT'

with open(queue_path) as f:
    queue = json.load(f)

updated = 0
for obra in queue.get('obres', []):
    autor = obra['autor']
    titol = obra['titol']
    categoria = obra.get('categoria', 'filosofia')
    slug_autor = autor.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a')
    slug_titol = titol.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a').replace('í', 'i')
    
    obra_dir = os.path.join(project, 'obres', categoria, slug_autor, slug_titol)
    
    if os.path.isdir(obra_dir):
        files = os.listdir(obra_dir)
        has_md = any(f.endswith('.md') for f in files)
        has_meta = 'metadata.yml' in files or 'metadata.json' in files
        
        if has_md and has_meta:
            new_status = 'done'
        elif has_md or len(files) > 0:
            new_status = 'in_progress'
        else:
            new_status = 'pending'
    else:
        new_status = 'pending'
    
    if obra.get('status') != new_status:
        obra['status'] = new_status
        updated += 1

if updated > 0:
    queue['updated_at'] = '$(date +%Y-%m-%d)'
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    print(f'{updated} obres actualitzades')
else:
    print('Cap canvi')
" 2>/dev/null | while read -r msg; do
        log "   📋 $msg"
    done
}

# ── 7. Manteniment setmanal ───────────────────────────────────────────────────
check_weekly_maintenance() {
    local day=$(date +%u)  # 1=dilluns, 7=diumenge
    
    # Només diumenges
    if [ "$day" -eq 7 ]; then
        if ! task_exists "manteniment.*setmanal\|weekly.*maintenance" > /dev/null 2>&1; then
            local last_maint=$(find "$TASKS_DIR/done/" -name "*.json" -mtime -7 -type f 2>/dev/null | \
                xargs grep -l "manteniment\|maintenance" 2>/dev/null | head -1)
            
            if [ -z "$last_maint" ]; then
                add_task "maintenance" "Manteniment setmanal: 1) Neteja fitxers Zone.Identifier. 2) Verifica que tots els imports funcionen: python3 -c 'import agents'. 3) Comprova espai en disc. 4) Git gc. 5) Reporta estat general del projecte."
                log "   🔧 Manteniment setmanal afegit"
            fi
        fi
    fi
}

# =============================================================================
# MAIN — Executar heartbeat complet
# =============================================================================
log "═══════════════════════════════════════════════════"
log "💓 HEARTBEAT v2 iniciat"

# Prerequisits
check_diem || exit 0
check_worker

# Estat actual
PENDING=$(count_pending)
RUNNING=$(count_running)
DONE_TODAY=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
FAILED=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)

log "📊 Estat: $PENDING pendents, $RUNNING running, $DONE_TODAY completades avui, $FAILED fallides"

# Si la cua ja està plena, només reportar
if [ "$PENDING" -ge "$MAX_PENDING" ]; then
    log "✅ Cua plena ($PENDING pendents). Res a fer."
else
    # Analitzar i generar tasques (per prioritat)
    update_queue_status
    check_failed           # 1r: recuperar fallides
    check_translations     # 2n: obres per traduir (core del projecte)
    check_code_reviews     # 3r: code reviews
    check_web              # 4t: web actualitzada
    check_tests            # 5è: tests
    check_weekly_maintenance  # 6è: manteniment
fi

# Resum final
PENDING_FINAL=$(count_pending)
log "💓 HEARTBEAT completat. Cua: $PENDING → $PENDING_FINAL pendents"
log "═══════════════════════════════════════════════════"