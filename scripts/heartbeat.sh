#!/bin/bash
# =============================================================================
# heartbeat.sh v3 — Generador intel·ligent de tasques AMB SUPERVISIÓ
# =============================================================================
# Millores v3 sobre v2:
#   - Tasques de supervisió post-traducció (qualitat, format, web)
#   - Cicle complet: traducció → supervisió → correcció → publicació
#   - Detecció d'obres traduïdes sense validar
#   - Verificació que la web reflecteix les obres
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
TASK_MANAGER="$PROJECT/scripts/task-manager.sh"
QUEUE="$PROJECT/config/obra-queue.json"
LOG="$HOME/claude-worker.log"
MAX_PENDING=5
MIN_DIEM_RESERVE=2

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HEARTBEAT] $1" | tee -a "$LOG"; }

count_pending() {
    ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l
}

count_running() {
    ls -1 "$TASKS_DIR/running/"*.json 2>/dev/null | wc -l
}

task_exists() {
    local keyword="$1"
    grep -rl "$keyword" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null | head -1
}

add_task() {
    local type="$1"
    local instruction="$2"
    if [ "$(count_pending)" -ge "$MAX_PENDING" ]; then
        return 1
    fi
    bash "$TASK_MANAGER" add "$type" "$instruction" 2>/dev/null
    log "   ➕ [$type]: $(echo "$instruction" | head -c 80)..."
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
    log "📚 Analitzant obres pendents..."
    
    [ ! -f "$QUEUE" ] && return 0

    python3 -c "
import json, os

queue = json.load(open('$QUEUE'))
project = '$PROJECT'

for obra in queue.get('obres', []):
    status = obra.get('status', 'pending')
    if status in ('done', 'skip', 'validated'):
        continue
    
    autor = obra['autor']
    titol = obra['titol']
    llengua = obra.get('llengua', 'desconeguda')
    categoria = obra.get('categoria', 'filosofia')
    slug_autor = autor.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a')
    slug_titol = titol.lower().replace(' ', '_').replace('è', 'e').replace('à', 'a').replace('í', 'i')
    
    obra_dir = os.path.join(project, 'obres', categoria, slug_autor, slug_titol)
    
    has_translation = False
    has_dir = os.path.isdir(obra_dir)
    if has_dir:
        files = os.listdir(obra_dir)
        has_translation = any(
            f.endswith('.md') or f.endswith('.txt')
            for f in files if any(k in f.lower() for k in ['traduccio', 'traducció', 'catala', 'català'])
        )
    
    if not has_dir:
        print(f'NEW|{autor}|{titol}|{llengua}|{categoria}')
    elif not has_translation:
        print(f'CONTINUE|{autor}|{titol}|{llengua}|{categoria}')
" 2>/dev/null | while IFS='|' read -r action autor titol extra1 extra2; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        case "$action" in
            NEW)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "Tradueix '$titol' de $autor del $extra1 al català. Busca el text original a Perseus, Gutenberg o Wikisource. Guarda a obres/$extra2/. Inclou metadata.yml. Després executa 'python3 scripts/build.py' per actualitzar la web."
                fi
                ;;
            CONTINUE)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "Continua la traducció de '$titol' de $autor. Revisa obres/$extra2/ per veure què falta. Completa i verifica qualitat."
                fi
                ;;
        esac
    done
}

# ── 2. ⭐ SUPERVISIÓ: Traduccions sense validar ──────────────────────────────
check_supervision() {
    log "🔎 Supervisió de traduccions..."

    python3 -c "
import os
from pathlib import Path

project = Path('$PROJECT')
obres_dir = project / 'obres'
tasks_done = Path('$TASKS_DIR') / 'done'

if not obres_dir.exists():
    exit(0)

for categoria in obres_dir.iterdir():
    if not categoria.is_dir():
        continue
    for autor in categoria.iterdir():
        if not autor.is_dir():
            continue
        for obra in autor.iterdir():
            if not obra.is_dir():
                continue
            
            files = list(obra.iterdir())
            filenames = [f.name for f in files]
            
            has_translation = any(
                f.suffix in ('.md', '.txt') and any(k in f.name.lower() for k in ['traduccio', 'traducció', 'catala', 'català', 'chapter', 'capitol'])
                for f in files
            )
            
            if not has_translation:
                continue
            
            has_metadata = 'metadata.yml' in filenames or 'metadata.json' in filenames
            has_validated = '.validated' in filenames
            
            # Ja supervisada? Skip
            if has_validated:
                continue
            
            # Ja hi ha una supervisió recent a done?
            obra_name = obra.name
            has_recent_review = False
            if tasks_done.exists():
                for done_file in tasks_done.glob('*.json'):
                    try:
                        content = done_file.read_text()
                        if 'supervis' in content.lower() and obra_name in content.lower():
                            has_recent_review = True
                            break
                    except:
                        pass
            
            if has_recent_review:
                continue
            
            relpath = str(obra.relative_to(project))
            
            if not has_metadata:
                print(f'MISSING_META|{relpath}|{autor.name}|{obra.name}')
            else:
                print(f'NEEDS_REVIEW|{relpath}|{autor.name}|{obra.name}')
" 2>/dev/null | while IFS='|' read -r action relpath autor_name obra_name; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        case "$action" in
            MISSING_META)
                if ! task_exists "metadata.*$obra_name" > /dev/null 2>&1; then
                    add_task "supervision" "Falta metadata.yml a $relpath. Crea'l amb: title, author, source_language, category, date, status."
                fi
                ;;
            NEEDS_REVIEW)
                if ! task_exists "supervis.*$obra_name\|qualitat.*$obra_name" > /dev/null 2>&1; then
                    add_task "supervision" "SUPERVISIÓ QUALITAT de '$obra_name' a $relpath. Comprova: 1) Qualitat del català (gramàtica, naturalitat, estil). 2) Fidelitat al original (no omissions ni invencions). 3) Glossari consistent. 4) Format correcte (capítols, notes). 5) metadata.yml complet. PUNTUACIÓ: Si qualitat >= 7/10, crea fitxer .validated amb data i puntuació. Si < 7/10, crea fitxer .needs_fix amb llista de problemes concrets."
                fi
                ;;
        esac
    done
}

# ── 3. ⭐ SUPERVISIÓ: Web sincronitzada ──────────────────────────────────────
check_web_sync() {
    log "🌐 Comprovant web..."
    
    local docs_time=0
    local obres_time=0
    
    if [ -d "$PROJECT/docs" ]; then
        docs_time=$(find "$PROJECT/docs" -name "*.html" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
        docs_time=${docs_time:-0}
    fi
    
    if [ -d "$PROJECT/obres" ]; then
        obres_time=$(find "$PROJECT/obres" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)
        obres_time=${obres_time:-0}
    fi
    
    if [ "$obres_time" -gt "$docs_time" ] 2>/dev/null; then
        if ! task_exists "build.py\|regenera.*web\|actualitza.*web" > /dev/null 2>&1; then
            add_task "publish" "Web desactualitzada. Executa 'python3 scripts/build.py' per regenerar docs/. Verifica que les obres amb .validated apareixen. Commit i push."
            log "   🌐 Publicació web afegida"
        fi
    else
        log "   🌐 Web OK"
    fi
}

# ── 4. Code reviews ──────────────────────────────────────────────────────────
check_code_reviews() {
    log "🔍 Code reviews..."

    find "$PROJECT/agents" "$PROJECT/scripts" "$PROJECT/utils" -name "*.py" -mtime -7 -type f 2>/dev/null | while read -r pyfile; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        local relpath="${pyfile#$PROJECT/}"
        local basename=$(basename "$pyfile")
        
        local recent_review=$(find "$TASKS_DIR/done/" -name "*.json" -mtime -7 -type f 2>/dev/null | \
            xargs grep -l "$basename" 2>/dev/null | head -1)
        
        if [ -z "$recent_review" ] && ! task_exists "$basename" > /dev/null 2>&1; then
            add_task "code-review" "Revisa $relpath: imports, bugs, typing, error handling. Arregla directament si trobes problemes."
        fi
    done
}

# ── 5. Tests ──────────────────────────────────────────────────────────────────
check_tests() {
    log "🧪 Tests..."
    
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
        add_task "test" "Executa 'python3 -m pytest tests/ -v'. Si hi ha errors, arregla'ls."
    fi
}

# ── 6. Tasques fallides recuperables ──────────────────────────────────────────
check_failed() {
    log "♻️ Tasques fallides..."
    
    find "$TASKS_DIR/failed/" -name "*.json" -mmin +60 -type f 2>/dev/null | head -3 | while read -r failed; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        local retries=$(python3 -c "import json; print(json.load(open('$failed')).get('retries',0))" 2>/dev/null)
        retries=${retries:-0}
        
        if [ "$retries" -lt 2 ]; then
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
        fi
    done
}

# ── 7. Actualitzar obra-queue.json ────────────────────────────────────────────
update_queue_status() {
    log "📋 Actualitzant obra-queue.json..."
    
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
        has_validated = '.validated' in files
        
        if has_validated:
            new_status = 'validated'
        elif has_md and has_meta:
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

# ── 8. Manteniment setmanal ───────────────────────────────────────────────────
check_weekly_maintenance() {
    local day=$(date +%u)
    if [ "$day" -eq 7 ]; then
        local last_maint=$(find "$TASKS_DIR/done/" -name "*.json" -mtime -7 -type f 2>/dev/null | \
            xargs grep -l "manteniment\|maintenance" 2>/dev/null | head -1)
        if [ -z "$last_maint" ] && ! task_exists "manteniment\|maintenance" > /dev/null 2>&1; then
            add_task "maintenance" "Manteniment setmanal: 1) Neteja Zone.Identifier. 2) Verifica imports. 3) Git gc. 4) Espai disc. 5) Reporta estat."
        fi
    fi
}

# ── 9. Rotació done/ ─────────────────────────────────────────────────────────
rotate_done() {
    local count=$(find "$TASKS_DIR/done/" -name "*.json" -mtime +7 -type f 2>/dev/null | wc -l)
    find "$TASKS_DIR/done/" -name "*.json" -mtime +7 -type f -delete 2>/dev/null
    [ "$count" -gt 0 ] && log "   🧹 $count tasques antigues eliminades"
}

# =============================================================================
# MAIN
# =============================================================================
log "═══════════════════════════════════════════════════"
log "💓 HEARTBEAT v3 iniciat (amb supervisió)"

check_diem || exit 0
check_worker

PENDING=$(count_pending)
RUNNING=$(count_running)
DONE_TODAY=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
FAILED=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)

log "📊 Estat: $PENDING pendents, $RUNNING running, $DONE_TODAY done avui, $FAILED fallides"

if [ "$PENDING" -ge "$MAX_PENDING" ]; then
    log "✅ Cua plena ($PENDING). Res a fer."
else
    # Per ordre de PRIORITAT:
    update_queue_status      # 0. Actualitzar estat
    check_failed             # 1. Recuperar fallides
    bash "$PROJECT/scripts/fix-structure.sh"  # 1.5 Auto-correcció estructura
    check_supervision        # 2. ⭐ SUPERVISIÓ (NOU!)
    check_translations       # 3. Noves traduccions
    check_web_sync           # 4. Web sincronitzada
    check_code_reviews       # 5. Code reviews
    check_tests              # 6. Tests
    check_weekly_maintenance # 7. Manteniment
    rotate_done              # 8. Neteja
fi

PENDING_FINAL=$(count_pending)
log "💓 HEARTBEAT v3 completat. Cua: $PENDING → $PENDING_FINAL pendents"
log "═══════════════════════════════════════════════════"
