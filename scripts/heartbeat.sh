#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# heartbeat.sh — Generador automàtic de tasques per Arion
# S'executa via cron cada 2 hores
# ═══════════════════════════════════════════════════════════════

TASKS_DIR="$HOME/.openclaw/workspace/tasks"
PROJECT_DIR="$HOME/biblioteca-universal-arion"
TASK_MANAGER="$PROJECT_DIR/scripts/task-manager.sh"
OBRA_QUEUE="$PROJECT_DIR/config/obra-queue.json"
LOG="$HOME/claude-worker.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEARTBEAT: $1" >> "$LOG"
}

mkdir -p "$TASKS_DIR"/{pending,running,done,failed}

# ── Comptar tasques pendents ───────────────────────────────
pending_count=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
running_count=$(ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l)

# No generar si ja hi ha massa feina
if [ $pending_count -ge 10 ]; then
    log "Cua plena ($pending_count pending). No genero més tasques."
    exit 0
fi

HOUR=$(date +%H)
DAY_OF_WEEK=$(date +%u)  # 1=dilluns, 7=diumenge

log "═══ Heartbeat executat (H=$HOUR, DoW=$DAY_OF_WEEK, pending=$pending_count) ═══"

# ── 1. TESTS (cada 6 hores: 00, 06, 12, 18) ──────────────
if [ "$HOUR" -eq 0 ] || [ "$HOUR" -eq 6 ] || [ "$HOUR" -eq 12 ] || [ "$HOUR" -eq 18 ]; then
    # Comprovar si ja hi ha un test pendent
    if ! ls "$TASKS_DIR/pending/"*test* 2>/dev/null | grep -q .; then
        bash "$TASK_MANAGER" add test \
            "Executa tots els tests del projecte. Primer instal·la dependències si cal (pip install -r requirements.txt). Després executa: python -m pytest tests/ o python test_integrated_pipeline.py agents. Reporta quins tests passen i quins fallen."
        log "Generada tasca: test"
    fi
fi

# ── 2. CODE REVIEW (cada 12 hores: 02, 14) ────────────────
if [ "$HOUR" -eq 2 ] || [ "$HOUR" -eq 14 ]; then
    # Escollir un fitxer aleatori per revisar
    local_files=($(find "$PROJECT_DIR/agents" "$PROJECT_DIR/pipeline" "$PROJECT_DIR/scripts" -name "*.py" 2>/dev/null))
    if [ ${#local_files[@]} -gt 0 ]; then
        random_file=${local_files[$RANDOM % ${#local_files[@]}]}
        relative=$(echo "$random_file" | sed "s|$PROJECT_DIR/||")
        
        if ! ls "$TASKS_DIR/pending/"*code-review* 2>/dev/null | grep -q "$relative"; then
            bash "$TASK_MANAGER" add code-review \
                "Revisa el fitxer $relative: 1) Verifica que els imports funcionen. 2) Busca bugs o errors lògics. 3) Millora el typing (type hints). 4) Comprova que segueix les convencions del projecte. 5) Si trobes problemes, arregla'ls directament." \
                "{\"file\": \"$relative\"}"
            log "Generada tasca: code-review $relative"
        fi
    fi
fi

# ── 3. TRADUCCIÓ NOVA (cada dia a les 10h) ────────────────
if [ "$HOUR" -eq 10 ]; then
    # Llegir la propera obra de la cua
    if [ -f "$OBRA_QUEUE" ]; then
        next_obra=$(python3 -c "
import json
with open('$OBRA_QUEUE') as f:
    q = json.load(f)
obres = q.get('obres', [])
for o in obres:
    if o.get('status') == 'pending':
        print(json.dumps(o))
        break
" 2>/dev/null)
        
        if [ -n "$next_obra" ]; then
            autor=$(echo "$next_obra" | python3 -c "import json,sys; print(json.load(sys.stdin)['autor'])")
            titol=$(echo "$next_obra" | python3 -c "import json,sys; print(json.load(sys.stdin)['titol'])")
            llengua=$(echo "$next_obra" | python3 -c "import json,sys; print(json.load(sys.stdin)['llengua'])")
            categoria=$(echo "$next_obra" | python3 -c "import json,sys; print(json.load(sys.stdin)['categoria'])")
            
            # Comprovar que no hi ha ja una tasca per aquesta obra
            slug=$(echo "$titol" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
            if ! ls "$TASKS_DIR/pending/"*"$slug"* 2>/dev/null | grep -q .; then
                bash "$TASK_MANAGER" translate "$autor" "$titol" "$llengua" "$categoria"
                
                # Marcar com "in_progress" a la cua
                python3 -c "
import json
with open('$OBRA_QUEUE') as f:
    q = json.load(f)
for o in q['obres']:
    if o['titol'] == '$titol' and o['status'] == 'pending':
        o['status'] = 'in_progress'
        break
with open('$OBRA_QUEUE', 'w') as f:
    json.dump(q, f, indent=2, ensure_ascii=False)
"
                log "Generada tasca: translate $titol de $autor"
            fi
        else
            log "No hi ha obres pendents a la cua"
        fi
    fi
fi

# ── 4. MANTENIMENT (dilluns a les 04h) ────────────────────
if [ "$DAY_OF_WEEK" -eq 1 ] && [ "$HOUR" -eq 4 ]; then
    bash "$TASK_MANAGER" add maintain \
        "Manteniment setmanal: 1) Actualitza requirements.txt si cal. 2) Executa linting (si hi ha flake8/ruff). 3) Comprova que la web es genera correctament amb build.py. 4) Neteja fitxers temporals. 5) Verifica que git està net."
    log "Generada tasca: manteniment setmanal"
fi

# ── 5. REFACTOR (dijous a les 04h) ────────────────────────
if [ "$DAY_OF_WEEK" -eq 4 ] && [ "$HOUR" -eq 4 ]; then
    # Buscar el fitxer més gran (probable candidat per refactor)
    biggest=$(find "$PROJECT_DIR/agents" "$PROJECT_DIR/pipeline" -name "*.py" -exec wc -l {} + 2>/dev/null | sort -rn | head -2 | tail -1 | awk '{print $2}')
    if [ -n "$biggest" ]; then
        relative=$(echo "$biggest" | sed "s|$PROJECT_DIR/||")
        bash "$TASK_MANAGER" add refactor \
            "Refactoring de $relative (el fitxer més gran del projecte): 1) Identifica funcions massa llargues (>50 línies) i divideix-les. 2) Extreu constants. 3) Millora documentació. 4) No canviïs funcionalitat, només estructura." \
            "{\"file\": \"$relative\"}"
        log "Generada tasca: refactor $relative"
    fi
fi

# ── 6. VERIFICAR WEB (cada dia a les 20h) ────────────────
if [ "$HOUR" -eq 20 ]; then
    bash "$TASK_MANAGER" add test \
        "Verifica que la web funciona: 1) Executa python scripts/build.py 2) Comprova que docs/index.html existeix i conté les obres publicades. 3) Verifica que els links funcionen. 4) Si hi ha errors, arregla'ls."
    log "Generada tasca: verificar web"
fi

# ── 7. ASSEGURAR WORKER ACTIU ─────────────────────────────
WORKER_PID_FILE="$TASKS_DIR/worker.lock"
if [ -f "$WORKER_PID_FILE" ]; then
    pid=$(cat "$WORKER_PID_FILE")
    if ! kill -0 "$pid" 2>/dev/null; then
        log "⚠️ Worker mort! Reiniciant..."
        rm -f "$WORKER_PID_FILE"
        nohup bash "$PROJECT_DIR/scripts/claude-worker.sh" >> "$LOG" 2>&1 &
        log "Worker reiniciat amb PID $!"
    fi
else
    log "⚠️ Worker no actiu! Iniciant..."
    nohup bash "$PROJECT_DIR/scripts/claude-worker.sh" >> "$LOG" 2>&1 &
    log "Worker iniciat amb PID $!"
fi

log "Heartbeat completat"
