#!/usr/bin/env bash
# =============================================================================
# MIGRACIÓ REPOSITORI BIBLIOTECA UNIVERSAL ARION
# =============================================================================
# Reorganitza l'estructura del repo en 3 zones:
#   obres/    → La biblioteca (contingut)
#   sistema/  → La maquinària (codi)
#   estat/    → Estat runtime (JSONs, mètriques, logs)
#
# ÚS:
#   bash migrar-repo.sh [--dry-run] [--fase N]
#
# FASES:
#   1 → Normalitzar obres/ (categoria/autor/obra, guions, minúscules)
#   2 → Crear sistema/ i moure scripts
#   3 → Crear estat/ i centralitzar JSONs + actualitzar referències
#
# IMPORTANT: Executar des de l'arrel del repositori
# =============================================================================

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
DRY_RUN=false
FASE_UNICA=""
LOG_FILE="${REPO_ROOT}/migració.log"
BACKUP_DIR="${REPO_ROOT}/.migració-backup-$(date +%Y%m%d_%H%M%S)"

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# ─── Parsejar arguments ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --fase)    FASE_UNICA="$2"; shift 2 ;;
        --help)
            echo "Ús: bash migrar-repo.sh [--dry-run] [--fase N]"
            echo "  --dry-run   Mostra què faria sense tocar res"
            echo "  --fase N    Executa només la fase N (1, 2 o 3)"
            exit 0
            ;;
        *) echo "Argument desconegut: $1"; exit 1 ;;
    esac
done

# ─── Funcions utilitat ───────────────────────────────────────────────────────
log() {
    local msg="[$(date '+%H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE"
}

info()    { log "${BLUE}ℹ️  $1${NC}"; }
ok()      { log "${GREEN}✅ $1${NC}"; }
warn()    { log "${YELLOW}⚠️  $1${NC}"; }
error()   { log "${RED}❌ $1${NC}"; }
phase()   { log "${PURPLE}═══════════════════════════════════════${NC}"; log "${PURPLE}  $1${NC}"; log "${PURPLE}═══════════════════════════════════════${NC}"; }

run() {
    # Executa comanda o mostra-la en dry-run
    if $DRY_RUN; then
        log "  ${YELLOW}[DRY-RUN]${NC} $*"
    else
        "$@"
    fi
}

safe_mv() {
    local src="$1" dst="$2"
    if [[ ! -e "$src" ]]; then
        warn "No existeix: $src (saltat)"
        return 0
    fi
    if [[ -e "$dst" ]]; then
        warn "Ja existeix destí: $dst (saltat)"
        return 0
    fi
    local dst_dir
    dst_dir=$(dirname "$dst")
    run mkdir -p "$dst_dir"
    run mv "$src" "$dst"
    ok "Mogut: $(basename "$src") → ${dst#$REPO_ROOT/}"
}

# ─── Verificacions prèvies ──────────────────────────────────────────────────
cd "$REPO_ROOT"

if [[ ! -f "README.md" ]] || [[ ! -d "obres" ]]; then
    error "No sembla l'arrel del repositori biblioteca-universal-arion"
    error "Executa des del directori arrel del repo"
    exit 1
fi

# Verificar que no hi ha canvis sense commit
if ! $DRY_RUN; then
    if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
        warn "Hi ha canvis sense commit. Es recomana fer commit primer."
        read -p "Continuar igualment? (s/N) " -n 1 -r
        echo
        [[ $REPLY =~ ^[Ss]$ ]] || exit 0
    fi
fi

echo ""
phase "MIGRACIÓ REPOSITORI BIBLIOTECA UNIVERSAL ARION"
info "Repo: $REPO_ROOT"
info "Dry-run: $DRY_RUN"
info "Backup: $BACKUP_DIR"
info "Log: $LOG_FILE"
echo ""

# ─── Backup ──────────────────────────────────────────────────────────────────
if ! $DRY_RUN; then
    info "Creant backup de fitxers crítics..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup estructura actual
    find . -maxdepth 4 -not -path './.git/*' -not -path './docs/*' -not -path './node_modules/*' | sort > "$BACKUP_DIR/estructura_original.txt"
    
    # Backup JSONs d'estat
    for f in config/obra-queue.json config/roadmap.json metrics/evolution.json metrics/openclaw-health.json; do
        if [[ -f "$f" ]]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$f")"
            cp "$f" "$BACKUP_DIR/$f"
        fi
    done
    
    # Backup scripts
    if [[ -d "scripts" ]]; then
        cp -r scripts "$BACKUP_DIR/scripts"
    fi
    
    ok "Backup creat a $BACKUP_DIR"
fi

# =============================================================================
# FASE 1: Normalitzar obres/
# =============================================================================
fase1_normalitzar_obres() {
    phase "FASE 1: Normalitzar obres/"
    
    # ── Mapa autor → categoria ───────────────────────────────────────────
    declare -A AUTOR_CATEGORIA=(
        # Filosofia
        ["plato"]="filosofia"
        ["socrates"]="filosofia"
        ["aristotil"]="filosofia"
        ["epictet"]="filosofia"
        ["epictetus"]="filosofia"
        ["seneca"]="filosofia"
        ["marc-aureli"]="filosofia"
        ["marc_aureli"]="filosofia"
        ["heraclit"]="filosofia"
        ["nietzsche"]="filosofia"
        ["schopenhauer"]="filosofia"
        ["montaigne"]="filosofia"
        ["cicero"]="filosofia"
        
        # Narrativa
        ["kafka"]="narrativa"
        ["dostoievski"]="narrativa"
        ["txekhov"]="narrativa"
        ["garxin"]="narrativa"
        ["akutagawa"]="narrativa"
        ["poe"]="narrativa"
        ["edgar-allan-poe"]="narrativa"
        ["melville"]="narrativa"
        ["bronte"]="narrativa"
        
        # Poesia
        ["shakespeare"]="poesia"
        ["baudelaire"]="poesia"
        ["leopardi"]="poesia"
        ["omar-khayyam"]="poesia"
        ["basho"]="poesia"
        
        # Teatre
        ["sofocles"]="teatre"
        ["strindberg"]="teatre"
        ["esquil"]="teatre"
        ["euripides"]="teatre"
        
        # Oriental
        ["laozi"]="oriental"
        ["lao-tse"]="oriental"
        ["confuci"]="oriental"
        ["buda"]="oriental"
        ["sutra"]="oriental"
        
        # Assaig
        ["montaigne-assaig"]="assaig"
    )
    
    # Categories vàlides
    CATEGORIES_VALIDES=("filosofia" "narrativa" "poesia" "teatre" "oriental" "assaig")
    
    # ── Funció slugify ───────────────────────────────────────────────────
    slugify() {
        echo "$1" | \
            sed 's/[_]/-/g' | \
            tr '[:upper:]' '[:lower:]' | \
            sed 's/[^a-z0-9àèéíòóúïü-]/-/g' | \
            sed 's/--*/-/g' | \
            sed 's/^-//;s/-$//'
    }
    
    # ── Detectar obres sense categoria ───────────────────────────────────
    info "Analitzant estructura actual d'obres/..."
    
    local obres_mogudes=0
    local obres_renombrades=0
    local obres_ok=0
    
    # Primer pas: detectar obres directament a obres/autor/ (sense categoria)
    for autor_dir in obres/*/; do
        [[ -d "$autor_dir" ]] || continue
        local autor_name
        autor_name=$(basename "$autor_dir")
        
        # Si el directori és una categoria vàlida, saltar
        local es_categoria=false
        for cat in "${CATEGORIES_VALIDES[@]}"; do
            if [[ "$autor_name" == "$cat" ]]; then
                es_categoria=true
                break
            fi
        done
        
        if $es_categoria; then
            # Processar obres dins la categoria per normalitzar noms
            for obra_autor_dir in "obres/${autor_name}/"*/; do
                [[ -d "$obra_autor_dir" ]] || continue
                for obra_dir in "${obra_autor_dir}"*/; do
                    [[ -d "$obra_dir" ]] || continue
                    # Només verificar si conté metadata.yml o traduccio.md
                    if [[ -f "${obra_dir}metadata.yml" ]] || [[ -f "${obra_dir}traduccio.md" ]]; then
                        local slug_autor slug_obra
                        slug_autor=$(slugify "$(basename "$(dirname "$obra_dir")")")
                        slug_obra=$(slugify "$(basename "$obra_dir")")
                        local expected="obres/${autor_name}/${slug_autor}/${slug_obra}/"
                        
                        if [[ "$obra_dir" != "$expected" ]]; then
                            info "Renombrant: ${obra_dir} → ${expected}"
                            run mkdir -p "$(dirname "$expected")"
                            run mv "$obra_dir" "$expected"
                            ((obres_renombrades++)) || true
                        else
                            ((obres_ok++)) || true
                        fi
                    fi
                done
            done
            continue
        fi
        
        # L'autor està directament a obres/ sense categoria
        local slug_autor
        slug_autor=$(slugify "$autor_name")
        
        # Buscar la categoria
        local categoria=""
        for key in "${!AUTOR_CATEGORIA[@]}"; do
            if [[ "$slug_autor" == *"$key"* ]] || [[ "$key" == *"$slug_autor"* ]]; then
                categoria="${AUTOR_CATEGORIA[$key]}"
                break
            fi
        done
        
        if [[ -z "$categoria" ]]; then
            warn "No sé la categoria de '$autor_name'. Saltant."
            warn "  Afegeix-lo al mapa AUTOR_CATEGORIA dins la fase 1"
            continue
        fi
        
        # Moure cada obra dins la categoria correcta
        for obra_dir in "${autor_dir}"*/; do
            [[ -d "$obra_dir" ]] || continue
            if [[ -f "${obra_dir}metadata.yml" ]] || [[ -f "${obra_dir}traduccio.md" ]] || [[ -f "${obra_dir}original.md" ]]; then
                local slug_obra
                slug_obra=$(slugify "$(basename "$obra_dir")")
                local dest="obres/${categoria}/${slug_autor}/${slug_obra}"

                if [[ -d "$dest" ]]; then
                    warn "Destí ja existeix: $dest (saltant duplicat)"
                    continue
                fi

                info "Movent: ${obra_dir} → ${dest}/"
                run mkdir -p "$(dirname "$dest")"
                run mv "$obra_dir" "$dest"
                ((obres_mogudes++)) || true
            fi
        done
        
        # Eliminar directori buit de l'autor si ha quedat buit
        if ! $DRY_RUN && [[ -d "$autor_dir" ]]; then
            rmdir "$autor_dir" 2>/dev/null || true
        fi
    done
    
    # ── Normalitzar noms existents dins categories ───────────────────────
    info "Normalitzant noms de carpetes (underscores → guions, minúscules)..."
    
    for categoria in "${CATEGORIES_VALIDES[@]}"; do
        [[ -d "obres/$categoria" ]] || continue
        
        for autor_dir in "obres/$categoria/"*/; do
            [[ -d "$autor_dir" ]] || continue
            local autor_name autor_slug
            autor_name=$(basename "$autor_dir")
            autor_slug=$(slugify "$autor_name")
            
            # Renombrar autor si cal
            if [[ "$autor_name" != "$autor_slug" ]]; then
                local new_autor_dir="obres/$categoria/$autor_slug"
                if [[ ! -d "$new_autor_dir" ]]; then
                    info "Renombrant autor: $autor_name → $autor_slug"
                    run mv "$autor_dir" "$new_autor_dir"
                    autor_dir="$new_autor_dir"
                fi
            fi
            
            # Renombrar obres dins l'autor
            for obra_dir in "${autor_dir}"*/; do
                [[ -d "$obra_dir" ]] || continue
                local obra_name obra_slug
                obra_name=$(basename "$obra_dir")
                obra_slug=$(slugify "$obra_name")
                
                if [[ "$obra_name" != "$obra_slug" ]]; then
                    local new_obra_dir="${autor_dir}${obra_slug}"
                    if [[ ! -d "$new_obra_dir" ]]; then
                        info "Renombrant obra: $obra_name → $obra_slug"
                        run mv "$obra_dir" "$new_obra_dir"
                        ((obres_renombrades++)) || true
                    fi
                fi
            done
        done
    done
    
    echo ""
    ok "Fase 1 completada:"
    info "  Obres mogudes a categoria: $obres_mogudes"
    info "  Obres renombrades: $obres_renombrades"
    info "  Obres ja correctes: $obres_ok"
}

# =============================================================================
# FASE 2: Crear sistema/ i moure scripts + agents + pipeline
# =============================================================================
fase2_crear_sistema() {
    phase "FASE 2: Crear sistema/ i moure codi"
    
    # ── Crear estructura ─────────────────────────────────────────────────
    info "Creant estructura sistema/..."
    run mkdir -p sistema/automatitzacio
    run mkdir -p sistema/traduccio
    run mkdir -p sistema/web
    
    # ── Moure scripts d'automatització ───────────────────────────────────
    info "Movent scripts d'automatització..."
    
    local auto_scripts=(
        "heartbeat.sh"
        "system-brain.sh"
        "claude-worker-mini.sh"
        "start-worker.sh"
        "worker-watchdog.sh"
        "worker-status.sh"
        "task-manager.sh"
        "consell-editorial.sh"
        "improve-openclaw.sh"
        "millora-continua.sh"
        "fix-structure.sh"
    )
    
    for script in "${auto_scripts[@]}"; do
        if [[ -f "scripts/$script" ]]; then
            safe_mv "scripts/$script" "sistema/automatitzacio/$script"
        fi
    done
    
    # ── Moure scripts de traducció ───────────────────────────────────────
    info "Movent scripts de traducció..."
    
    local trad_scripts=(
        "traduir_pipeline.py"
        "cercador_fonts_v2.py"
        "cercador_fonts.py"
    )
    
    for script in "${trad_scripts[@]}"; do
        if [[ -f "scripts/$script" ]]; then
            safe_mv "scripts/$script" "sistema/traduccio/$script"
        fi
    done
    
    # Moure agents/ i pipeline/
    if [[ -d "agents" ]]; then
        safe_mv "agents" "sistema/traduccio/agents"
    fi
    if [[ -d "pipeline" ]]; then
        safe_mv "pipeline" "sistema/traduccio/pipeline"
    fi
    
    # ── Moure web ────────────────────────────────────────────────────────
    info "Movent fitxers web..."
    
    if [[ -f "scripts/build.py" ]]; then
        safe_mv "scripts/build.py" "sistema/web/build.py"
    fi
    if [[ -f "scripts/dashboard_server.py" ]]; then
        safe_mv "scripts/dashboard_server.py" "sistema/web/dashboard_server.py"
    fi
    
    # Moure web/ frontend (css, js, templates)
    if [[ -d "web" ]]; then
        for subdir in css js templates assets; do
            if [[ -d "web/$subdir" ]]; then
                safe_mv "web/$subdir" "sistema/web/$subdir"
            fi
        done
        # Moure fitxers solts de web/
        for f in web/*; do
            [[ -f "$f" ]] && safe_mv "$f" "sistema/web/$(basename "$f")"
        done
        # Eliminar web/ buit
        $DRY_RUN || rmdir web 2>/dev/null || true
    fi
    
    # ── Moure scripts restants ───────────────────────────────────────────
    info "Movent scripts restants..."
    if [[ -d "scripts" ]]; then
        for f in scripts/*; do
            [[ -f "$f" ]] || continue
            local fname
            fname=$(basename "$f")
            # Backups i logs no es mouen
            [[ "$fname" == *.bak* ]] && continue
            [[ "$fname" == *.log ]] && continue
            
            # Decidir on va
            if [[ "$fname" == *.py ]]; then
                safe_mv "$f" "sistema/traduccio/$fname"
            else
                safe_mv "$f" "sistema/automatitzacio/$fname"
            fi
        done
        # Eliminar scripts/ buit
        $DRY_RUN || rmdir scripts 2>/dev/null || true
    fi
    
    # ── Crear symlinks de compatibilitat ─────────────────────────────────
    info "Creant symlinks de compatibilitat (scripts/ → sistema/)..."
    
    if ! $DRY_RUN; then
        # Symlink principal perquè el cron i HEARTBEAT.md segueixin funcionant
        if [[ ! -e "scripts" ]]; then
            mkdir -p scripts
            
            # Symlinks per cada script d'automatització
            for script in "${auto_scripts[@]}"; do
                if [[ -f "sistema/automatitzacio/$script" ]]; then
                    ln -sf "../sistema/automatitzacio/$script" "scripts/$script"
                fi
            done
            
            # Symlinks per scripts de traducció
            for script in "${trad_scripts[@]}"; do
                if [[ -f "sistema/traduccio/$script" ]]; then
                    ln -sf "../sistema/traduccio/$script" "scripts/$script"
                fi
            done
            
            # Symlinks web
            for script in build.py dashboard_server.py; do
                if [[ -f "sistema/web/$script" ]]; then
                    ln -sf "../sistema/web/$script" "scripts/$script"
                fi
            done
            
            ok "Symlinks creats a scripts/ (compatibilitat temporal)"
        fi
    fi
    
    echo ""
    ok "Fase 2 completada: codi organitzat a sistema/"
}

# =============================================================================
# FASE 3: Crear estat/, centralitzar JSONs, actualitzar referències
# =============================================================================
fase3_crear_estat_i_actualitzar() {
    phase "FASE 3: Centralitzar estat + actualitzar referències"
    
    # ── Crear estructura estat/ ──────────────────────────────────────────
    info "Creant estructura estat/..."
    run mkdir -p estat/metrics
    run mkdir -p estat/logs
    
    # ── Moure JSONs d'estat ──────────────────────────────────────────────
    info "Movent fitxers d'estat..."
    
    # config/ → estat/
    if [[ -d "config" ]]; then
        for f in config/*.json; do
            [[ -f "$f" ]] && safe_mv "$f" "estat/$(basename "$f")"
        done
        $DRY_RUN || rmdir config 2>/dev/null || true
    fi
    
    # metrics/ → estat/metrics/
    if [[ -d "metrics" ]]; then
        for f in metrics/*; do
            [[ -f "$f" ]] && safe_mv "$f" "estat/metrics/$(basename "$f")"
        done
        $DRY_RUN || rmdir metrics 2>/dev/null || true
    fi
    
    # data/ → mantenir (conté originals i glossaris, no és estat)
    # Però moure JSONs generats
    if [[ -d "data" ]]; then
        for f in data/propostes.json data/usuaris.json; do
            [[ -f "$f" ]] && safe_mv "$f" "estat/$(basename "$f")"
        done
    fi
    
    # ── Actualitzar referències als scripts ───────────────────────────────
    info "Actualitzant paths dins els scripts..."
    
    # Mapa de substitucions (old_path → new_path)
    declare -A PATH_MAP=(
        ["scripts/heartbeat.sh"]="sistema/automatitzacio/heartbeat.sh"
        ["scripts/system-brain.sh"]="sistema/automatitzacio/system-brain.sh"
        ["scripts/claude-worker-mini.sh"]="sistema/automatitzacio/claude-worker-mini.sh"
        ["scripts/start-worker.sh"]="sistema/automatitzacio/start-worker.sh"
        ["scripts/worker-watchdog.sh"]="sistema/automatitzacio/worker-watchdog.sh"
        ["scripts/task-manager.sh"]="sistema/automatitzacio/task-manager.sh"
        ["scripts/consell-editorial.sh"]="sistema/automatitzacio/consell-editorial.sh"
        ["scripts/improve-openclaw.sh"]="sistema/automatitzacio/improve-openclaw.sh"
        ["scripts/millora-continua.sh"]="sistema/automatitzacio/millora-continua.sh"
        ["scripts/fix-structure.sh"]="sistema/automatitzacio/fix-structure.sh"
        ["scripts/traduir_pipeline.py"]="sistema/traduccio/traduir_pipeline.py"
        ["scripts/cercador_fonts_v2.py"]="sistema/traduccio/cercador_fonts_v2.py"
        ["scripts/build.py"]="sistema/web/build.py"
        ["scripts/dashboard_server.py"]="sistema/web/dashboard_server.py"
        ["config/obra-queue.json"]="estat/obra-queue.json"
        ["config/roadmap.json"]="estat/roadmap.json"
        ["metrics/evolution.json"]="estat/metrics/evolution.json"
        ["metrics/openclaw-health.json"]="estat/metrics/openclaw-health.json"
    )
    
    if ! $DRY_RUN; then
        # Buscar tots els fitxers .sh, .py, .md a sistema/ i actualitzar paths
        local files_to_update
        files_to_update=$(find sistema/ -type f \( -name "*.sh" -o -name "*.py" -o -name "*.md" \) 2>/dev/null || true)
        
        # També actualitzar CLAUDE.md a l'arrel
        if [[ -f "CLAUDE.md" ]]; then
            files_to_update="$files_to_update
CLAUDE.md"
        fi
        
        local updates=0
        for file in $files_to_update; do
            [[ -f "$file" ]] || continue
            local changed=false
            
            for old_path in "${!PATH_MAP[@]}"; do
                local new_path="${PATH_MAP[$old_path]}"
                if grep -q "$old_path" "$file" 2>/dev/null; then
                    sed -i "s|${old_path}|${new_path}|g" "$file"
                    changed=true
                fi
            done
            
            if $changed; then
                ((updates++))
                ok "Actualitzat: $file"
            fi
        done
        
        info "  $updates fitxers actualitzats amb nous paths"
    else
        info "[DRY-RUN] S'actualitzarien els paths dins sistema/ i CLAUDE.md"
    fi
    
    # ── Actualitzar obra-queue.json amb paths normalitzats ───────────────
    info "Actualitzant obra-queue.json amb paths normalitzats..."
    
    local queue_file="estat/obra-queue.json"
    if [[ ! -f "$queue_file" ]] && [[ -f "config/obra-queue.json" ]]; then
        queue_file="config/obra-queue.json"
    fi
    
    if [[ -f "$queue_file" ]] && ! $DRY_RUN; then
        # Normalitzar paths dins el JSON (underscores → guions)
        python3 -c "
import json, re, sys

with open('$queue_file', 'r') as f:
    data = json.load(f)

def slugify(s):
    s = s.replace('_', '-').lower()
    s = re.sub(r'[^a-z0-9àèéíòóúïü/-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s

if isinstance(data, list):
    for obra in data:
        if 'obra_dir' in obra:
            parts = obra['obra_dir'].split('/')
            obra['obra_dir'] = '/'.join(slugify(p) for p in parts)
        if 'obra_path' in obra:
            parts = obra['obra_path'].split('/')
            obra['obra_path'] = '/'.join(slugify(p) for p in parts)
elif isinstance(data, dict) and 'obres' in data:
    for obra in data['obres']:
        if 'obra_dir' in obra:
            parts = obra['obra_dir'].split('/')
            obra['obra_dir'] = '/'.join(slugify(p) for p in parts)

with open('$queue_file', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('obra-queue.json actualitzat')
" 2>/dev/null && ok "obra-queue.json normalitzat" || warn "No s'ha pogut actualitzar obra-queue.json"
    fi
    
    # ── Actualitzar CLAUDE.md amb l'estructura nova ──────────────────────
    info "Actualitzant CLAUDE.md..."
    
    if [[ -f "CLAUDE.md" ]] && ! $DRY_RUN; then
        # Afegir secció d'estructura al principi de CLAUDE.md
        local temp_claude
        temp_claude=$(mktemp)
        cat > "$temp_claude" << 'CLAUDE_HEADER'
# Estructura del Repositori

El repositori està organitzat en 3 zones:

## Zones principals
- `obres/` — La biblioteca. Traduccions organitzades per categoria/autor/obra
- `sistema/` — La maquinària. Tot el codi del sistema autònom
  - `sistema/automatitzacio/` — heartbeat, brain, worker, watchdog
  - `sistema/traduccio/` — pipeline, agents, cercador de fonts
  - `sistema/web/` — build.py, dashboard, CSS/JS/templates
- `estat/` — Estat runtime. JSONs de cua, mètriques, logs

## Paths importants
- Cua d'obres: `estat/obra-queue.json`
- Heartbeat: `sistema/automatitzacio/heartbeat.sh`
- Brain: `sistema/automatitzacio/system-brain.sh`
- Worker: `sistema/automatitzacio/claude-worker-mini.sh`
- Pipeline: `sistema/traduccio/traduir_pipeline.py`
- Build web: `sistema/web/build.py`
- Mètriques: `estat/metrics/`

## Compatibilitat
Existeix un directori `scripts/` amb symlinks als nous paths per compatibilitat
temporal amb cron i HEARTBEAT.md. Es pot eliminar quan tots els scripts
estiguin actualitzats.

---

CLAUDE_HEADER
        
        # Afegir contingut original de CLAUDE.md
        cat "CLAUDE.md" >> "$temp_claude"
        mv "$temp_claude" "CLAUDE.md"
        ok "CLAUDE.md actualitzat amb nova estructura"
    fi
    
    # ── Actualitzar .gitignore ───────────────────────────────────────────
    info "Actualitzant .gitignore..."
    
    if [[ -f ".gitignore" ]] && ! $DRY_RUN; then
        cat >> ".gitignore" << 'GITIGNORE_ADDITIONS'

# Migració
.migració-backup-*
migració.log

# Estat runtime (opcionalment ignorar logs)
estat/logs/*.log

# Symlinks de compatibilitat (temporal)
# scripts/  ← directori de symlinks
GITIGNORE_ADDITIONS
        ok ".gitignore actualitzat"
    fi
    
    echo ""
    ok "Fase 3 completada: estat centralitzat, referències actualitzades"
}

# =============================================================================
# RESUM FINAL
# =============================================================================
resum_final() {
    phase "RESUM DE LA MIGRACIÓ"
    
    echo ""
    info "Estructura resultant:"
    echo ""
    
    if ! $DRY_RUN; then
        # Mostrar estructura nova
        echo "biblioteca-universal-arion/"
        for dir in obres sistema estat community docs data .github; do
            if [[ -d "$dir" ]]; then
                echo "├── $dir/"
                # Primer nivell
                for subdir in "$dir"/*/; do
                    [[ -d "$subdir" ]] || continue
                    echo "│   ├── $(basename "$subdir")/"
                done
                # Fitxers al primer nivell
                for f in "$dir"/*; do
                    [[ -f "$f" ]] && echo "│   ├── $(basename "$f")"
                done
            fi
        done
        for f in CLAUDE.md README.md .env .gitignore; do
            [[ -f "$f" ]] && echo "├── $f"
        done
    fi
    
    echo ""
    ok "═══════════════════════════════════════"
    ok "  Migració completada!"
    ok "═══════════════════════════════════════"
    echo ""
    info "Pròxims passos:"
    info "  1. Revisa l'estructura: ls -la obres/ sistema/ estat/"
    info "  2. Verifica que el heartbeat funciona: bash sistema/automatitzacio/heartbeat.sh"
    info "  3. Si tot OK, fes commit: git add -A && git commit -m 'refactor: reorganitzar repositori en 3 zones'"
    info "  4. Quan tot funcioni, elimina scripts/ (symlinks): rm -rf scripts/"
    info "  5. Actualitza HEARTBEAT.md a OpenClaw amb els nous paths"
    echo ""
    warn "IMPORTANT: Actualitza el crontab si referencia scripts/heartbeat.sh"
    warn "  crontab -e → canviar 'scripts/heartbeat.sh' per 'sistema/automatitzacio/heartbeat.sh'"
    echo ""
}

# =============================================================================
# EXECUCIÓ
# =============================================================================

if [[ -n "$FASE_UNICA" ]]; then
    case "$FASE_UNICA" in
        1) fase1_normalitzar_obres ;;
        2) fase2_crear_sistema ;;
        3) fase3_crear_estat_i_actualitzar ;;
        *) error "Fase desconeguda: $FASE_UNICA (usa 1, 2 o 3)"; exit 1 ;;
    esac
else
    fase1_normalitzar_obres
    echo ""
    fase2_crear_sistema
    echo ""
    fase3_crear_estat_i_actualitzar
    echo ""
    resum_final
fi
