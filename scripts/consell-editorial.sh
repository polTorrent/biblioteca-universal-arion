#!/bin/bash
# =============================================================================
# consell-editorial.sh — Agent autònom del Consell Editorial
# =============================================================================
# Analitza el catàleg actual i crea una TASCA perquè el worker generi
# propostes d'obres noves i les afegeixi a obra-queue.json.
#
# Ús:
#   bash scripts/consell-editorial.sh              # Execució normal
#   bash scripts/consell-editorial.sh --dry-run    # Mostra la tasca que crearia, sense crear-la
#   bash scripts/consell-editorial.sh --force      # Ignora límit de pending
# =============================================================================

set -euo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
export PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
export QUEUE="${QUEUE:-$PROJECT/config/obra-queue.json}"
export OBRES_DIR="$PROJECT/obres"
MAX_PENDING_QUEUE="${MAX_PENDING_QUEUE:-10}"
MAX_PROPOSTES="${MAX_PROPOSTES_PER_EXECUCIO:-3}"
DRY_RUN=false
FORCE=false

# ── Arguments ─────────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --force)   FORCE=true ;;
    esac
done

# ── Logger ────────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CONSELL] $1"; }

# ── Funcions d'anàlisi ───────────────────────────────────────────────────────

# Retorna el nombre d'obres amb status "pending" a la cua
count_pending() {
    python3 -c "
import json, sys
with open('$QUEUE') as f:
    data = json.load(f)
pending = [o for o in data.get('obres', []) if o.get('status') == 'pending']
print(len(pending))
" 2>/dev/null || echo "0"
}

# Genera un resum compacte del catàleg (una línia per categoria)
generar_resum_cataleg() {
    python3 << 'PYEOF'
import json, os

queue_path = os.environ.get('QUEUE', 'config/obra-queue.json')
obres_dir = os.environ.get('OBRES_DIR', 'obres')

with open(queue_path) as f:
    data = json.load(f)
obres_queue = data.get('obres', [])

categories = {}
idiomes = set()
for o in obres_queue:
    cat = o.get('categoria', '?')
    autor = o.get('autor', '?')
    idiomes.add(o.get('llengua', '?'))
    categories.setdefault(cat, set()).add(autor)

if os.path.isdir(obres_dir):
    for cat in os.listdir(obres_dir):
        cat_path = os.path.join(obres_dir, cat)
        if not os.path.isdir(cat_path):
            continue
        for autor in os.listdir(cat_path):
            if os.path.isdir(os.path.join(cat_path, autor)):
                categories.setdefault(cat, set()).add(autor.replace('-', ' ').title())

lines = []
for cat in sorted(categories):
    autors = sorted(categories[cat])
    lines.append(cat.title() + ' (' + str(len(autors)) + '): ' + ', '.join(autors) + '.')

lines.append('Idiomes: ' + ', '.join(sorted(idiomes)) + '.')

all_cats = {'filosofia', 'narrativa', 'poesia', 'teatre', 'assaig', 'oriental'}
missing = all_cats - set(categories.keys())
if missing:
    lines.append('FALTEN categories: ' + ', '.join(sorted(missing)) + '.')

print(' '.join(lines))
PYEOF
}

# =============================================================================
# EXECUCIÓ PRINCIPAL
# =============================================================================

log "══════════════════════════════════════════════════"
log "Consell Editorial — Sessió iniciada"

# 1. Comprovar quantes obres pending hi ha
pending=$(count_pending)
log "Obres pending a la cua: $pending (màx: $MAX_PENDING_QUEUE)"

if [ "$FORCE" = false ] && [ "$pending" -ge "$MAX_PENDING_QUEUE" ]; then
    log "La cua ja té $pending obres pending (>= $MAX_PENDING_QUEUE). No cal afegir-ne més."
    log "══════════════════════════════════════════════════"
    exit 0
fi

# 2. Generar resum del catàleg
log "Analitzant catàleg actual..."
resum=$(generar_resum_cataleg)
log "Resum generat:"
echo "$resum" | while IFS= read -r line; do log "  $line"; done

# 3. Construir la instrucció completa per al worker
instruction="Ets el Consell Editorial de la Biblioteca Universal Arion (traduccions al català d'obres clàssiques). Catàleg actual: ${resum}

Fes el següent:
1. Proposa ${MAX_PROPOSTES} obres noves per traduir. Criteris: domini públic (autor mort >70 anys), cànon universal, diversificar categories/idiomes/èpoques, <15.000 paraules, text original disponible online (Gutenberg, Perseus, Wikisource, Latin Library, Aozora, CText). Preferir obres sense traducció catalana recent. No repeteixis autors ni obres del catàleg.
2. Per cada obra proposada, afegeix-la a config/obra-queue.json amb els camps: autor, titol, llengua, categoria (filosofia|narrativa|poesia|teatre|assaig|oriental), dificultat (1-5), paraules_aprox, fonts (llista), status \"pending\", notes (justificació).
3. Fes commit amb missatge descriptiu i push."

# 4. Crear tasca o mostrar-la (dry-run)
if [ "$DRY_RUN" = true ]; then
    log "Mode dry-run: tasca que es crearia:"
    log "  Tipus: consell-editorial"
    log "  Instrucció:"
    echo "$instruction" | while IFS= read -r line; do log "    $line"; done
    log "══════════════════════════════════════════════════"
    exit 0
fi

log "Creant tasca per al worker..."
bash "$PROJECT/scripts/task-manager.sh" add consell-editorial "$instruction"

log "Tasca creada. El worker la processarà automàticament."
log "══════════════════════════════════════════════════"
