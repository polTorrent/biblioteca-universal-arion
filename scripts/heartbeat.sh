#!/bin/bash
# =============================================================================
# heartbeat.sh v5 — Generador intel·ligent de tasques AMB SUPERVISIÓ + BRAIN
# =============================================================================
# Millores v5 sobre v4:
#   - Integració amb system-brain.sh (cervell intel·ligent)
#   - Deduplicació de tasques via brain_check_duplicate
#   - Propostes intel·ligents, evolució, web health, roadmap (diaris)
# Millores v3-v4:
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

# ── Carregar System Brain (deduplicació + funcions intel·ligents) ────────────
BRAIN_SCRIPT="$PROJECT/scripts/system-brain.sh"
if [ -f "$BRAIN_SCRIPT" ]; then
    # Exportar variables perquè el brain les hereti
    export PROJECT TASKS_DIR TASK_MANAGER QUEUE LOG
    source "$BRAIN_SCRIPT"
    BRAIN_LOADED=true
else
    BRAIN_LOADED=false
fi

# ── Control del bot OpenClaw ─────────────────────────────────────────────────
# El gateway corre com a systemd user service.
# Parem abans de tocar ~/.openclaw/, reiniciem després.
# Si brain està carregat, reutilitzem les seves funcions.
# Si no, en tenim de pròpies.
OPENCLAW_SERVICE="openclaw-gateway.service"
HEARTBEAT_STOPPED_OPENCLAW=false

_heartbeat_stop_openclaw() {
    # Si el brain ja l'ha parat, no repetir
    if [ "$BRAIN_LOADED" = true ] && [ "$BRAIN_STOPPED_OPENCLAW" = true ]; then
        return
    fi
    if [ "$HEARTBEAT_STOPPED_OPENCLAW" = true ]; then
        return
    fi
    if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
        log "🛑 Parant OpenClaw abans de tocar ~/.openclaw/..."
        systemctl --user stop "$OPENCLAW_SERVICE" 2>/dev/null
        local tries=0
        while systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            log "   ⚠️ Servei encara actiu després de 10s. Forçant kill..."
            systemctl --user kill "$OPENCLAW_SERVICE" 2>/dev/null
            sleep 2
        fi
        HEARTBEAT_STOPPED_OPENCLAW=true
        log "   ✅ OpenClaw aturat"
    else
        log "   ℹ️ OpenClaw ja estava aturat"
    fi
}

_heartbeat_start_openclaw() {
    if [ "$HEARTBEAT_STOPPED_OPENCLAW" = true ]; then
        log "🚀 Reiniciant OpenClaw..."
        systemctl --user start "$OPENCLAW_SERVICE" 2>/dev/null
        local tries=0
        while ! systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null && [ "$tries" -lt 10 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if systemctl --user is-active --quiet "$OPENCLAW_SERVICE" 2>/dev/null; then
            log "   ✅ OpenClaw reiniciat correctament"
        else
            log "   ❌ ERROR: OpenClaw no ha arrencat! Comprova amb: systemctl --user status $OPENCLAW_SERVICE"
        fi
        HEARTBEAT_STOPPED_OPENCLAW=false
    fi
}

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
    # Deduplicació via brain (si disponible)
    if [ "$BRAIN_LOADED" = true ]; then
        # Extreure objecte de la instrucció (primer argument significatiu)
        local object
        object=$(echo "$instruction" | grep -oP "(?<='|')[^'\"]+(?='|')" | head -1)
        [ -z "$object" ] && object=$(echo "$instruction" | head -c 60 | tr ' ' '-')
        if ! brain_check_duplicate "$type" "$object"; then
            return 1
        fi
        local key
        key=$(_task_key "$type" "$object")
        _record_task "$key" "created"
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
    if pgrep -f "claude-worker-mini" > /dev/null 2>&1; then
        log "✅ Worker actiu"
        return
    fi
    log "⚠️ Worker NO actiu. Reiniciant (lleuger)..."
    # Netejar lockfile orfe
    if [ -f "$TASKS_DIR/worker.lock" ]; then
        local old_pid
        old_pid=$(cat "$TASKS_DIR/worker.lock" 2>/dev/null)
        if ! kill -0 "$old_pid" 2>/dev/null; then
            rm -f "$TASKS_DIR/worker.lock"
        fi
    fi
    # Retornar tasques running a pending
    for f in "$TASKS_DIR/running/"*.json; do
        [ -f "$f" ] && mv "$f" "$TASKS_DIR/pending/"
    done
    # Reiniciar amb nohup (independent de tmux)
    nohup bash "$PROJECT/scripts/claude-worker-mini.sh" >> "$LOG" 2>&1 &
    disown
    log "✅ Worker reiniciat (PID $!)"
}

# =============================================================================
# ANALITZADORS D'ESTAT
# =============================================================================

# ── 1. Obres pendents de traducció ───────────────────────────────────────────
check_translations() {
    log "📚 Analitzant obres pendents..."

    [ ! -f "$QUEUE" ] && return 0

    python3 -c "
import json, os, unicodedata, re

queue = json.load(open('$QUEUE'))
project = '$PROJECT'
tasks_dir = '$TASKS_DIR'

def slugify(text):
    \"\"\"Genera slug normalitzat: minúscules, sense accents, guions.\"\"\"
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def task_exists_in_dir(titol, directory):
    \"\"\"Comprova si ja existeix una tasca amb aquest títol a un directori.\"\"\"
    if not os.path.isdir(directory):
        return False
    for f in os.listdir(directory):
        if f.endswith('.json'):
            try:
                with open(os.path.join(directory, f)) as fh:
                    content = fh.read()
                if titol.lower() in content.lower():
                    return True
            except:
                pass
    return False

for obra in queue.get('obres', []):
    status = obra.get('status', 'pending')
    if status in ('done', 'skip', 'validated'):
        continue

    autor = obra['autor']
    titol = obra['titol']
    llengua = obra.get('llengua', 'desconeguda')
    categoria = obra.get('categoria', 'filosofia')

    # Usar obra_dir explícit si existeix al JSON, sinó calcular slug
    obra_dir_rel = obra.get('obra_dir', '')
    if obra_dir_rel:
        obra_dir = os.path.join(project, obra_dir_rel)
    else:
        obra_dir = os.path.join(project, 'obres', categoria, slugify(autor), slugify(titol))

    has_original = os.path.isfile(os.path.join(obra_dir, 'original.md'))
    has_translation = False
    has_dir = os.path.isdir(obra_dir)
    if has_dir:
        files = os.listdir(obra_dir)
        has_translation = any(
            f.endswith('.md') and any(k in f.lower() for k in ['traduccio', 'traducció', 'catala', 'català', 'chapter', 'capitol'])
            for f in files
        )

    # Comprovar dedup: no crear tasca si ja n'hi ha a pending o running (NO failed)
    if task_exists_in_dir(titol, os.path.join(tasks_dir, 'pending')):
        continue
    if task_exists_in_dir(titol, os.path.join(tasks_dir, 'running')):
        continue

    obra_dir_rel = obra_dir_rel or os.path.relpath(obra_dir, project)

    if has_translation:
        # Ja té traducció — no generar tasca (supervisió s'encarrega)
        continue
    elif has_original:
        # Té original però no traducció → traduir directament
        print(f'TRANSLATE|{autor}|{titol}|{llengua}|{obra_dir_rel}|{categoria}')
    else:
        # No té original → primer obtenir el text font
        print(f'FETCH|{autor}|{titol}|{llengua}|{obra_dir_rel}|{categoria}')
" 2>/dev/null | while IFS='|' read -r action autor titol lingua obra_path categoria; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break

        case "$action" in
            FETCH)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "fetch" "mkdir -p $obra_path && python3 scripts/cercador_fonts_v2.py \"$autor\" \"$titol\" \"$lingua\" \"$obra_path\" && if [ ! -s $obra_path/original.md ]; then echo 'ERROR: No s.ha pogut obtenir original.md' && exit 1; fi && git add -A && git commit -m \"font: $titol de $autor\" && git push"
                    log "   📥 Fetch: $titol de $autor ($lingua)"
                fi
                ;;
            TRANSLATE)
                if ! task_exists "$titol" > /dev/null 2>&1; then
                    add_task "translate" "python3 scripts/traduir_pipeline.py $obra_path/"
                    log "   📝 Translate: $titol de $autor"
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
# ── 2b. ⭐ AUTO-FIX: Detecta .needs_fix i crea tasques correctores ─────────
check_needs_fix() {
    log "🔧 Comprovant obres amb .needs_fix..."
    
    find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | while read -r needs_fix_file; do
        obra_dir=$(dirname "$needs_fix_file")
        obra_name=$(basename "$obra_dir")
        relpath=$(python3 -c "import os; print(os.path.relpath('$obra_dir', '$PROJECT'))")
        
        # Ja hi ha un .fixing? (tasca en curs)
        [ -f "$obra_dir/.fixing" ] && continue
        
        # Comprovar que no hi ha ja una tasca pending/running per aquesta obra
        if ls "$TASKS_DIR/pending/"*"$obra_name"* "$TASKS_DIR/running/"*"$obra_name"* 2>/dev/null | grep -q .; then
            continue
        fi
        
        # Llegir puntuació del .needs_fix
        score=$(grep -oP '\d+\.?\d*/10' "$needs_fix_file" | head -1 | cut -d/ -f1)
        score_int=${score%%.*}  # Part entera
        
        # Llegir problemes concrets
        problems=$(grep -A1 "\[.*\]" "$needs_fix_file" | head -20 | tr '\n' ' ' | cut -c1-500)
        
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        
        if [ "${score_int:-0}" -eq 0 ]; then
            # PUNTUACIÓ 0 → Traducció corrupta, cal retraduir de zero
            log "   🔴 $obra_name: puntuació 0/10 — RETRADUCCIÓ"
            add_task "translation" "Executa el pipeline V2 per retraduir: python3 scripts/traduir_pipeline.py $relpath. Si el pipeline falla, tradueix manualment: 1) Llegeix original.md a $relpath. 2) Tradueix TOTS els capítols al català. 3) Afegeix notes i glossari. 4) Sobreescriu traduccio.md. 5) Elimina .needs_fix/.fixing. 6) Commit+push."
        else
            # PUNTUACIÓ 1-6 → Cal corregir problemes específics
            log "   🟡 $obra_name: puntuació ${score}/10 — CORRECCIONS"
            add_task "fix" "CORREGEIX l'\'obra a $relpath (puntuació ${score}/10). Llegeix el fitxer .needs_fix per veure els problemes concrets. Corregeix TOTS els problemes llistats a .needs_fix. Quan acabis: 1) Elimina .needs_fix. 2) NO crees .validated (la supervisió ho farà). 3) Commit+push."
        fi
        
        # Marcar com a fixing
        mv "$needs_fix_file" "$obra_dir/.fixing"
        log "   📋 Creat tasca per $obra_name, marcat .fixing"
    done
    
    # Comprovar .fixing amb tasca completada → tornar a supervisar
    find "$PROJECT/obres" -name ".fixing" 2>/dev/null | while read -r fixing_file; do
        obra_dir=$(dirname "$fixing_file")
        obra_name=$(basename "$obra_dir")

        # Si ja no hi ha tasca pending/running → el fix s'ha completat
        if ! ls "$TASKS_DIR/pending/"*"$obra_name"* "$TASKS_DIR/running/"*"$obra_name"* 2>/dev/null | grep -q .; then
            # Comprovar que hi ha una tasca a done/ MES NOVA que el .fixing
            # (evita confondre tasques antigues amb el fix actual)
            local fixing_time
            fixing_time=$(stat -c %Y "$fixing_file" 2>/dev/null || echo 0)
            local found_newer=false
            for done_file in "$TASKS_DIR/done/"*"$obra_name"*.json; do
                [ -f "$done_file" ] || continue
                local done_time
                done_time=$(stat -c %Y "$done_file" 2>/dev/null || echo 0)
                if [ "$done_time" -gt "$fixing_time" ]; then
                    found_newer=true
                    break
                fi
            done
            if [ "$found_newer" = true ]; then
                log "   ✅ $obra_name: fix completat, eliminant .fixing per re-supervisar"
                rm -f "$fixing_file"
            fi
        fi
    done
}


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

    # Crear directori failed_permanent/ si no existeix
    mkdir -p "$TASKS_DIR/failed_permanent"

    find "$TASKS_DIR/failed/" -name "*.json" -mmin +60 -type f 2>/dev/null | head -5 | while read -r failed; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break

        # Llegir dades de la tasca
        local task_info
        task_info=$(python3 -c "
import json
with open('$failed') as fh:
    d = json.load(fh)
retries = d.get('retries', d.get('retry_count', 0))
instruction = d.get('instruction', '')
task_type = d.get('type', 'unknown')
regen_count = d.get('regen_count', 0)
total_failures = d.get('total_failures', retries + regen_count * 3)
print(f'{retries}|{len(instruction)}|{task_type}|{regen_count}|{total_failures}|{instruction[:200]}')
" 2>/dev/null)

        local retries inst_len task_type regen_count total_failures inst_preview
        IFS='|' read -r retries inst_len task_type regen_count total_failures inst_preview <<< "$task_info"
        retries=${retries:-0}
        inst_len=${inst_len:-0}
        regen_count=${regen_count:-0}
        total_failures=${total_failures:-0}

        # Si el total d'intents acumulats (regens * retries) >= 9 → abandonar definitivament
        if [ "$total_failures" -ge 9 ]; then
            mv "$failed" "$TASKS_DIR/failed_permanent/"
            log "   ⛔ Abandonada ($total_failures intents totals): $(basename "$failed")"
            continue
        fi

        # Si ja s'ha reintentat 3+ vegades amb el MATEIX format → abandonar
        if [ "$regen_count" -ge 3 ]; then
            mv "$failed" "$TASKS_DIR/failed_permanent/"
            log "   ⛔ Abandonada (3+ regens): $(basename "$failed")"
            continue
        fi

        # Si la instrucció era massa llarga (>200 chars) → regenerar simplificada
        if [ "$inst_len" -gt 200 ]; then
            log "   🔄 Instrucció massa llarga ($inst_len chars), regenerant simplificada..."
            python3 -c "
import json, re, os

with open('$failed') as fh:
    d = json.load(fh)

instruction = d.get('instruction', '')
task_type = d.get('type', 'unknown')

# Intentar extreure obra_path de la instrucció original
obra_path = ''
m = re.search(r'obres/[a-z0-9/_-]+', instruction)
if m:
    obra_path = m.group(0).rstrip('/')

project = os.path.expanduser('~/biblioteca-universal-arion')
new_instruction = instruction  # fallback

if obra_path:
    full_path = os.path.join(project, obra_path)
    has_original = os.path.isfile(os.path.join(full_path, 'original.md'))

    if task_type in ('translate', 'fetch', 'translation'):
        if has_original:
            new_instruction = f'python3 scripts/traduir_pipeline.py {obra_path}/'
            task_type = 'translate'
        else:
            # Extreure autor/titol/llengua de la instrucció
            autor = re.search(r\"de ([A-Z][\\w\\s]+?)(?= del| al| \\.)\", instruction)
            autor = autor.group(1).strip() if autor else 'desconegut'
            llengua = re.search(r'del (\\w+)', instruction)
            llengua = llengua.group(1) if llengua else 'desconeguda'
            titol = re.search(r\"['\\\"]([^'\\\"]+)['\\\"]\", instruction)
            titol = titol.group(1) if titol else os.path.basename(obra_path)
            new_instruction = f'mkdir -p {obra_path} && python3 scripts/cercador_fonts_v2.py \\\"{autor}\\\" \\\"{titol}\\\" \\\"{llengua}\\\" \\\"{obra_path}\\\" && if [ ! -s {obra_path}/original.md ]; then echo ERROR && exit 1; fi && git add -A && git commit -m \\\"font: {titol}\\\" && git push'
            task_type = 'fetch'

d['instruction'] = new_instruction
d['type'] = task_type
d['total_failures'] = d.get('total_failures', d.get('retries', 0) + d.get('regen_count', 0) * 3) + d.get('retries', 0)
d['retries'] = 0
d['retry_count'] = 0
d['recovered'] = True
d['regen_count'] = d.get('regen_count', 0) + 1

with open('$failed', 'w') as fh:
    json.dump(d, fh, indent=2, ensure_ascii=False)
" 2>/dev/null
            mv "$failed" "$TASKS_DIR/pending/"
            log "   ♻️ Regenerada (simplificada): $(basename "$failed")"
        else
            # Instrucció curta, reintentar tal qual si retries < max_retries
            if [ "$retries" -lt 2 ]; then
                python3 -c "
import json
with open('$failed') as fh:
    d = json.load(fh)
d['total_failures'] = d.get('total_failures', d.get('retries', 0) + d.get('regen_count', 0) * 3) + d.get('retries', 0)
d['retries'] = 0
d['retry_count'] = 0
d['recovered'] = True
d['regen_count'] = d.get('regen_count', 0) + 1
with open('$failed', 'w') as fh:
    json.dump(d, fh, indent=2, ensure_ascii=False)
" 2>/dev/null
                mv "$failed" "$TASKS_DIR/pending/"
                log "   ♻️ Recuperada: $(basename "$failed")"
            else
                mv "$failed" "$TASKS_DIR/failed_permanent/"
                log "   ⛔ Abandonada (max retries): $(basename "$failed")"
            fi
        fi
    done
}

# ── 7. Actualitzar obra-queue.json ────────────────────────────────────────────
update_queue_status() {
    log "📋 Actualitzant obra-queue.json..."
    
    python3 -c "
import json, os, unicodedata, re

queue_path = '$QUEUE'
project = '$PROJECT'

def slugify(text):
    \"\"\"Genera slug normalitzat: minúscules, sense accents, guions.\"\"\"
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

with open(queue_path) as f:
    queue = json.load(f)

updated = 0
for obra in queue.get('obres', []):
    autor = obra['autor']
    titol = obra['titol']
    categoria = obra.get('categoria', 'filosofia')

    # Usar obra_dir explícit si existeix al JSON, sinó calcular slug
    obra_dir_rel = obra.get('obra_dir', '')
    if obra_dir_rel:
        obra_dir = os.path.join(project, obra_dir_rel)
    else:
        obra_dir = os.path.join(project, 'obres', categoria, slugify(autor), slugify(titol))
    
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


# ── 10b. Processar notificacions pendents d'usuaris ──────────────────────────
process_pending_notifications() {
    local NOTIF_FILE="$HOME/.openclaw/workspace/pending_notification.txt"
    
    if [ ! -f "$NOTIF_FILE" ]; then
        return
    fi
    
    log "📨 Processant notificacions pendents..."
    
    # Llegir dades de la notificació
    local channel user message timestamp
    channel=$(grep "^channel:" "$NOTIF_FILE" | cut -d: -f2-)
    user=$(grep "^user:" "$NOTIF_FILE" | cut -d: -f2-)
    message=$(grep "^message:" "$NOTIF_FILE" | cut -d: -f2-)
    timestamp=$(grep "^timestamp:" "$NOTIF_FILE" | cut -d: -f2-)
    
    # Enviar via OpenClaw (scriure a fitxer que el gateway llegirà)
    local NOTIF_OUT="$HOME/.openclaw/workspace/outgoing_notification.json"
    cat > "$NOTIF_OUT" << EOF
{
  "action": "send",
  "channel": "discord",
  "channelId": "${channel:-1479504522614476953}",
  "message": "${message}",
  "timestamp": "$(date -Iseconds)"
}
EOF
    
    log "   ✅ Notificació preparada per a ${user}"
    rm -f "$NOTIF_FILE"
}

# ── 10b. Regenerar botó de propostes ──────────────────────────────────────────
regenerate_proposals_button() {
    if [ -f "$PROJECT/scripts/boto_propostes_watchdog.sh" ]; then
        log "🔄 Regenerant botó de propostes..."
        bash "$PROJECT/scripts/boto_propostes_watchdog.sh" 2>/dev/null || true
    fi
}

# ── 10. Generar report per Discord ────────────────────────────────────────────
generate_report() {
    local REPORT_FILE="$HOME/.openclaw/workspace/last_heartbeat_report.md"
    
    # Generar informe detallat amb el script Python
    if [ -f "$PROJECT/scripts/informe_detallat.py" ]; then
        python3 "$PROJECT/scripts/informe_detallat.py" > "$REPORT_FILE" 2>/dev/null
        log "📋 Report detallat generat a $REPORT_FILE"
    else
        # Fallback a l'informe simple
        local validated=$(find "$PROJECT/obres" -name ".validated" 2>/dev/null | wc -l)
        local needs_fix=$(find "$PROJECT/obres" -name ".needs_fix" 2>/dev/null | wc -l)
        local total_trad=$(find "$PROJECT/obres" -name "traduccio.md" 2>/dev/null | wc -l)
        local pending=$(count_pending)
        local done_today=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
        
        local worker_status="❌ INACTIU"
        if tmux has-session -t worker 2>/dev/null; then
            worker_status="✅ ACTIU"
        fi
        
        cat > "$REPORT_FILE" << REPORT
💓 **Heartbeat Arion** — $(date '+%H:%M %d/%m')

📊 **Traduccions:** $total_trad total | $validated validades | $needs_fix pendents fix
⚙️ **Worker:** $worker_status | $done_today tasques avui | $pending cua
REPORT
        log "📋 Report simple generat"
    fi
}

# ── 9b. ⭐ Comprovació ràpida d'obres validades (sense tasques Claude) ────────
check_quick_issues() {
    log "🔍 Comprovació ràpida d'obres validades..."

    local ok_count=0
    local problem_count=0
    local rebuilt_web=false

    while IFS= read -r validated_file; do
        local obra_dir
        obra_dir=$(dirname "$validated_file")
        local obra_name
        obra_name=$(basename "$obra_dir")

        # Comprovar presència a la web
        if [ -f "$PROJECT/docs/index.html" ] && ! grep -q "$obra_name" "$PROJECT/docs/index.html" 2>/dev/null; then
            if [ "$rebuilt_web" = false ]; then
                log "   🌐 Obra validada '$obra_name' no apareix a la web. Executant build.py..."
                python3 "$PROJECT/scripts/build.py" 2>/dev/null && rebuilt_web=true
                if [ "$rebuilt_web" = true ]; then
                    log "   ✅ Web regenerada"
                fi
            fi
            problem_count=$((problem_count + 1))
            continue
        fi

        # Comprovar portada (només log, improve ho arreglarà)
        if [ ! -f "$obra_dir/portada.png" ]; then
            log "   ⚠️ $obra_name: falta portada.png"
            problem_count=$((problem_count + 1))
            continue
        fi

        ok_count=$((ok_count + 1))
    done < <(find "$PROJECT/obres" -name ".validated" 2>/dev/null)

    log "   Resum ràpid: $ok_count obres OK, $problem_count amb problemes menors"
}

# ── 10. ⭐ Salut OpenClaw (diari) ─────────────────────────────────────────────
check_openclaw_health() {
    log "🔧 Salut OpenClaw..."

    local IMPROVE_SCRIPT="$PROJECT/scripts/improve-openclaw.sh"
    [ ! -f "$IMPROVE_SCRIPT" ] && { log "   improve-openclaw.sh no trobat"; return; }

    # Guardar timestamp de l'última execució
    local LAST_RUN_FILE="$TASKS_DIR/.improve-openclaw-last-run"

    # Comprovar si ja s'ha executat avui
    if [ -f "$LAST_RUN_FILE" ]; then
        local last_run_date
        last_run_date=$(cat "$LAST_RUN_FILE" 2>/dev/null)
        local today
        today=$(date +%Y-%m-%d)
        if [ "$last_run_date" = "$today" ]; then
            log "   Ja executat avui ($today). Saltant."
            return
        fi
    fi

    # Comprovar que no hi hagi ja massa tasques improve-openclaw pendents
    local improve_pending
    improve_pending=$(grep -rl "improve-openclaw" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null | wc -l)
    if [ "$improve_pending" -ge 2 ]; then
        log "   Ja hi ha $improve_pending tasques improve-openclaw pendents. Saltant."
        return
    fi

    # Executar l'anàlisi
    bash "$IMPROVE_SCRIPT" 2>/dev/null
    date +%Y-%m-%d > "$LAST_RUN_FILE"
    log "   Anàlisi OpenClaw completada"
}

# =============================================================================
# MAIN
# =============================================================================
log "═══════════════════════════════════════════════════"
log "💓 HEARTBEAT v5 iniciat (amb supervisió + brain)"
[ "$BRAIN_LOADED" = true ] && log "🧠 System Brain carregat" || log "⚠️ System Brain NO disponible"

# ── Comprovació de pausa ───────────────────────────────────────────────────
PAUSE_FILE="$PROJECT/PAUSE"
if [ -f "$PAUSE_FILE" ]; then
    PAUSED_UNTIL=$(grep "PAUSED_UNTIL=" "$PAUSE_FILE" 2>/dev/null | cut -d'=' -f2)
    PAUSED_BY=$(grep "PAUSED_BY=" "$PAUSE_FILE" 2>/dev/null | cut -d'=' -f2)
    REASON=$(grep "REASON=" "$PAUSE_FILE" 2>/dev/null | cut -d'=' -f2)
    TODAY=$(date '+%Y-%m-%d')
    if [ -n "$PAUSED_UNTIL" ] && [[ "$TODAY" < "$PAUSED_UNTIL" ]]; then
        log "⏸️ PAUSA ACTIVA fins $PAUSED_UNTIL"
        log "   Motiu: $REASON"
        log "   Per: $PAUSED_BY"
        log "💓 HEARTBEAT v5 completat (en pausa)"
        log "═══════════════════════════════════════════════════"
        exit 0
    fi
fi

check_diem || exit 0
check_worker  # Reactivat: comprovació lleugera amb pgrep + nohup

PENDING=$(count_pending)
RUNNING=$(count_running)
DONE_TODAY=$(find "$TASKS_DIR/done/" -name "*.json" -newermt "$(date '+%Y-%m-%d')" -type f 2>/dev/null | wc -l)
FAILED=$(ls -1 "$TASKS_DIR/failed/"*.json 2>/dev/null | wc -l)

log "📊 Estat: $PENDING pendents, $RUNNING running, $DONE_TODAY done avui, $FAILED fallides"

# ── Fase 0: Lectura (no toca ~/.openclaw/) ──────────────────────────────────
update_queue_status          # 0. Actualitzar obra-queue.json (dins $PROJECT)
bash "$PROJECT/scripts/fix-structure.sh"  # 0.5 Auto-correcció estructura (dins $PROJECT)

# ── Fase 1: Escriptura a ~/.openclaw/ — parar bot ──────────────────────────
_heartbeat_stop_openclaw
trap '_heartbeat_start_openclaw' EXIT

check_failed                 # 1. Recuperar fallides (mou fitxers dins tasks/)
check_needs_fix              # 2b. ⭐ AUTO-FIX (.needs_fix → tasca) — SEMPRE corre

# ═══ MODE CONSOLIDACIÓ: auditoria i reparació ═══
echo "[$(date)] 🔧 Mode consolidació: auditant catàleg..."
AUDIT_LAST="$PROJECT/config/.last_audit"
AUDIT_INTERVAL=43200  # cada 12 hores (🛑 CONSOLIDACIÓ: reduït de 4h)

should_audit=false
if [ ! -f "$AUDIT_LAST" ]; then
    should_audit=true
else
    last=$(cat "$AUDIT_LAST")
    now=$(date +%s)
    if [ $((now - last)) -gt $AUDIT_INTERVAL ]; then
        should_audit=true
    fi
fi

if [ "$should_audit" = true ]; then
    bash "$PROJECT/scripts/auditar-cataleg.sh" --fix
    date +%s > "$AUDIT_LAST"
    echo "[$(date)] ✅ Auditoria completada, tasques generades"
fi

if [ "$PENDING" -ge "$MAX_PENDING" ]; then
    log "✅ Cua plena ($PENDING). Saltant tasques noves."
else
    # Només si hi ha espai a la cua:
    # 🛑 CONSOLIDACIÓ: pausat per estalviar DIEM
    # check_supervision        # 2. ⭐ SUPERVISIÓ
    # 🛑 CONSOLIDACIÓ: desactivat — no crear fetch/translate per obres noves
    # check_translations       # 3. Noves traduccions
    check_web_sync           # 4. Web sincronitzada
    check_quick_issues       # 4b. Comprovació ràpida obres validades
    # 🛑 CONSOLIDACIÓ: pausat per estalviar DIEM
    # check_code_reviews       # 5. Code reviews
    check_tests              # 6. Tests
    check_weekly_maintenance # 7. Manteniment
    check_openclaw_health    # 8. Salut OpenClaw (ja no cal stop/start intern)
    # 9. System Brain — funcions diàries (ja no cal stop/start intern)
    if [ "$BRAIN_LOADED" = true ]; then
        run_daily
    fi
    rotate_done              # 10. Neteja
fi

PENDING_FINAL=$(count_pending)
generate_report              # Escriu last_heartbeat_report.md a ~/.openclaw/

# ── Fase 2.5: Processar propostes Discord ───────────────────────────────────
if [ -f "$PROJECT/scripts/processar-propostes.sh" ]; then
    log "📋 Processant propostes Discord..."
    bash "$PROJECT/scripts/processar-propostes.sh" 2>/dev/null || true
fi

# ── Fase 2.6: Processar notificacions pendents ───────────────────────────────
process_pending_notifications

# ── Fase 3: Reiniciar bot ──────────────────────────────────────────────────
_heartbeat_start_openclaw
trap - EXIT

log "💓 HEARTBEAT v5 completat. Cua: $PENDING → $PENDING_FINAL pendents"
log "═══════════════════════════════════════════════════"
