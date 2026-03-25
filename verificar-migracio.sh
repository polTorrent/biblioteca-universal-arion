#!/usr/bin/env bash
# =============================================================================
# VERIFICACIÓ POST-MIGRACIÓ
# =============================================================================
# Comprova que la migració ha estat correcta:
#   - Estructura de directoris
#   - Obres ben categoritzades
#   - Referències internes vàlides
#   - Symlinks funcionals
#   - obra-queue.json consistent
#
# ÚS: bash verificar-migració.sh
# =============================================================================

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(pwd)}"
ERRORS=0
WARNINGS=0
OK=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; ((OK++)) || true; }
check_fail() { echo -e "${RED}  ❌ $1${NC}"; ((ERRORS++)) || true; }
check_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; ((WARNINGS++)) || true; }

echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  VERIFICACIÓ POST-MIGRACIÓ${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

cd "$REPO_ROOT"

# ─── 1. Estructura de directoris ─────────────────────────────────────────────
echo -e "${BLUE}1. Estructura de directoris${NC}"

for dir in obres sistema sistema/automatitzacio sistema/traduccio sistema/web estat community; do
    if [[ -d "$dir" ]]; then
        check_ok "$dir/ existeix"
    else
        check_fail "$dir/ NO existeix"
    fi
done

# ─── 2. Scripts al lloc correcte ─────────────────────────────────────────────
echo ""
echo -e "${BLUE}2. Scripts d'automatització${NC}"

critical_scripts=(
    "sistema/automatitzacio/heartbeat.sh"
    "sistema/automatitzacio/system-brain.sh"
    "sistema/automatitzacio/claude-worker-mini.sh"
    "sistema/automatitzacio/task-manager.sh"
)

for script in "${critical_scripts[@]}"; do
    if [[ -f "$script" ]]; then
        check_ok "$(basename "$script") al seu lloc"
    else
        check_fail "FALTA: $script"
    fi
done

echo ""
echo -e "${BLUE}3. Scripts de traducció${NC}"

trad_files=(
    "sistema/traduccio/traduir_pipeline.py"
    "sistema/traduccio/agents"
    "sistema/traduccio/pipeline"
)

for item in "${trad_files[@]}"; do
    if [[ -e "$item" ]]; then
        check_ok "$(basename "$item") al seu lloc"
    else
        check_warn "No trobat: $item (pot ser que no existís)"
    fi
done

# ─── 3. Obres ben categoritzades ────────────────────────────────────────────
echo ""
echo -e "${BLUE}4. Obres categoritzades correctament${NC}"

categories_valides=("filosofia" "narrativa" "poesia" "teatre" "oriental" "assaig")
obres_ok=0
obres_mal=0

# Comprovar que no hi ha autors directament a obres/ (sense categoria)
for item in obres/*/; do
    [[ -d "$item" ]] || continue
    dir_name=$(basename "$item")
    
    is_category=false
    for cat in "${categories_valides[@]}"; do
        [[ "$dir_name" == "$cat" ]] && is_category=true && break
    done
    
    if ! $is_category; then
        check_fail "Autor sense categoria: obres/$dir_name/ (hauria d'estar dins una categoria)"
        ((obres_mal++)) || true
    fi
done

# Comprovar noms amb underscores
while IFS= read -r -d '' dir; do
    dirname_base=$(basename "$dir")
    if [[ "$dirname_base" == *"_"* ]]; then
        check_warn "Nom amb underscore: $dir (hauria de ser amb guions)"
    fi
done < <(find obres -mindepth 2 -maxdepth 4 -type d -print0 2>/dev/null)

# Comptar obres per categoria
for cat in "${categories_valides[@]}"; do
    if [[ -d "obres/$cat" ]]; then
        count=$(find "obres/$cat" -name "metadata.yml" -o -name "traduccio.md" | wc -l)
        check_ok "$cat: $count obres/fitxers"
    fi
done

# ─── 4. Estat centralitzat ──────────────────────────────────────────────────
echo ""
echo -e "${BLUE}5. Estat centralitzat${NC}"

if [[ -f "estat/obra-queue.json" ]]; then
    check_ok "obra-queue.json a estat/"
    
    # Verificar que els paths dins el JSON apunten a llocs reals
    python3 -c "
import json, sys, os

with open('estat/obra-queue.json', 'r') as f:
    data = json.load(f)

items = data if isinstance(data, list) else data.get('obres', [])
broken = 0
total = 0

for obra in items:
    path = obra.get('obra_dir') or obra.get('obra_path', '')
    if path:
        total += 1
        full_path = os.path.join('obres', path) if not path.startswith('obres') else path
        if not os.path.isdir(full_path):
            print(f'  ⚠️  Path no existeix: {full_path}')
            broken += 1

if broken > 0:
    print(f'  {broken}/{total} paths trencats a obra-queue.json')
    sys.exit(1)
else:
    print(f'  ✅ Tots {total} paths vàlids a obra-queue.json')
" 2>/dev/null && ((OK++)) || ((WARNINGS++))

else
    check_fail "obra-queue.json NO trobat a estat/"
fi

# Comprovar que no queden JSONs d'estat al lloc vell
for old_path in "config/obra-queue.json" "config/roadmap.json" "metrics/evolution.json"; do
    if [[ -f "$old_path" ]]; then
        check_warn "JSON d'estat encara al lloc vell: $old_path"
    fi
done

# ─── 5. Symlinks de compatibilitat ──────────────────────────────────────────
echo ""
echo -e "${BLUE}6. Symlinks de compatibilitat${NC}"

if [[ -d "scripts" ]]; then
    broken_links=0
    total_links=0
    
    for link in scripts/*; do
        [[ -L "$link" ]] || continue
        ((total_links++)) || true
        if [[ ! -e "$link" ]]; then
            check_fail "Symlink trencat: $link → $(readlink "$link")"
            ((broken_links++)) || true
        fi
    done
    
    if [[ $total_links -gt 0 ]]; then
        if [[ $broken_links -eq 0 ]]; then
            check_ok "$total_links symlinks funcionals a scripts/"
        fi
    else
        check_warn "scripts/ existeix però no conté symlinks"
    fi
else
    check_warn "scripts/ no existeix (els symlinks de compatibilitat no s'han creat)"
fi

# ─── 6. Referències internes ─────────────────────────────────────────────────
echo ""
echo -e "${BLUE}7. Referències internes als scripts${NC}"

# Buscar referències al path vell que haurien d'estar actualitzades
old_refs=0
if [[ -d "sistema" ]]; then
    while IFS= read -r file; do
        # Buscar "scripts/" que no sigui un symlink
        matches=$(grep -n 'scripts/' "$file" 2>/dev/null | grep -v '^#' | grep -v 'symlink' | head -5 || true)
        if [[ -n "$matches" ]]; then
            check_warn "Referència antiga a scripts/ dins: $file"
            echo "$matches" | head -3 | while read -r line; do
                echo -e "    ${YELLOW}$line${NC}"
            done
            ((old_refs++)) || true
        fi
    done < <(find sistema/ -type f \( -name "*.sh" -o -name "*.py" \) 2>/dev/null)
fi

if [[ $old_refs -eq 0 ]]; then
    check_ok "Cap referència antiga a scripts/ dins sistema/"
fi

# ─── 7. No queden fitxers orfes ──────────────────────────────────────────────
echo ""
echo -e "${BLUE}8. Fitxers orfes${NC}"

# Scripts que haurien d'haver-se mogut
orphan_scripts=$(find . -maxdepth 1 \( -name "*.sh" -o -name "*.py" \) 2>/dev/null | grep -v './migrar' | grep -v './verificar' || true)
if [[ -n "$orphan_scripts" ]]; then
    check_warn "Scripts a l'arrel del repo (haurien d'estar a sistema/):"
    echo "$orphan_scripts" | while read -r f; do echo -e "    ${YELLOW}$f${NC}"; done
fi

# Directoris buits
for dir in config metrics web scripts; do
    if [[ -d "$dir" ]] && [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]; then
        check_warn "Directori buit: $dir/ (es pot eliminar)"
    fi
done

# ─── RESUM ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  RESUM VERIFICACIÓ${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}✅ OK: $OK${NC}"
echo -e "  ${YELLOW}⚠️  Avisos: $WARNINGS${NC}"
echo -e "  ${RED}❌ Errors: $ERRORS${NC}"
echo ""

if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}  Tot correcte! Pots fer commit.${NC}"
    echo ""
    echo "  git add -A"
    echo "  git commit -m 'refactor: reorganitzar repositori en 3 zones (obres/sistema/estat)'"
    echo "  git push"
else
    echo -e "${RED}  Hi ha errors que cal corregir abans de fer commit.${NC}"
fi
echo ""
