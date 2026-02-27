#!/bin/bash
# =============================================================================
# consell-editorial.sh — Agent autònom del Consell Editorial
# =============================================================================
# Manté la obra-queue.json plena amb propostes d'obres noves.
# Analitza el catàleg actual, detecta buits, i genera propostes via Claude.
#
# Ús:
#   bash scripts/consell-editorial.sh              # Execució normal
#   bash scripts/consell-editorial.sh --dry-run    # Només mostra propostes, no modifica
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

# Genera el prompt complet per Claude (compacte, <400 paraules)
generar_prompt() {
    local resum="$1"
    cat <<PROMPT_EOF
Biblioteca Universal Arion: traduccions al català d'obres clàssiques. Catàleg actual: $resum

Proposa $MAX_PROPOSTES obres noves. Criteris: domini públic (autor mort >70 anys), cànon universal, diversificar categories/idiomes/èpoques, <15.000 paraules, text original disponible online (Gutenberg, Perseus, Wikisource, Latin Library, Aozora, CText). Preferir obres sense traducció catalana recent.

No repeteixis autors ni obres del catàleg. Respon NOMÉS amb un JSON array, sense markdown ni backticks:
[{"autor":"Nom","titol":"Títol Original","llengua":"idioma","categoria":"filosofia|narrativa|poesia|teatre|assaig|oriental","dificultat":1,"paraules_aprox":5000,"fonts":["gutenberg"],"justificacio":"raó","notes":"obs"}]
PROMPT_EOF
}

# Valida una proposta individual
validar_proposta() {
    local json_proposta="$1"
    python3 -c "
import json, sys, os

proposta = json.loads('''$json_proposta''')
queue_path = '$QUEUE'
obres_dir = '$OBRES_DIR'

autor = proposta.get('autor', '').strip()
titol = proposta.get('titol', '').strip()
categoria = proposta.get('categoria', '').strip()

# Validar camps obligatoris
if not autor or not titol or not categoria:
    print('INVALID: camps buits')
    sys.exit(1)

# Validar categoria
cats_valides = {'filosofia', 'narrativa', 'poesia', 'teatre', 'assaig', 'oriental'}
if categoria not in cats_valides:
    print(f'INVALID: categoria \"{categoria}\" no vàlida')
    sys.exit(1)

# Comprovar duplicats a obra-queue.json
with open(queue_path) as f:
    data = json.load(f)
for o in data.get('obres', []):
    if o.get('autor', '').lower() == autor.lower() and o.get('titol', '').lower() == titol.lower():
        print(f'DUPLICAT: {autor} - {titol} ja és a la cua')
        sys.exit(1)

# Comprovar duplicats als directoris d'obres (per autor)
autor_slug = autor.lower().replace(' ', '-').replace('à','a').replace('è','e').replace('é','e').replace('í','i').replace('ò','o').replace('ó','o').replace('ú','u')
for cat in os.listdir(obres_dir):
    cat_path = os.path.join(obres_dir, cat)
    if not os.path.isdir(cat_path):
        continue
    for a in os.listdir(cat_path):
        if a.lower() == autor_slug or a.lower() in autor.lower() or autor.lower() in a.lower():
            # Mateix autor, comprovar si mateixa obra (aproximat)
            autor_path = os.path.join(cat_path, a)
            if not os.path.isdir(autor_path):
                continue
            titol_slug = titol.lower().replace(' ', '-').replace('à','a').replace('è','e').replace('é','e').replace('í','i').replace('ò','o').replace('ó','o').replace('ú','u')
            for obra in os.listdir(autor_path):
                if obra.lower() == titol_slug or titol_slug in obra.lower() or obra.lower() in titol_slug:
                    print(f'DUPLICAT: {autor}/{titol} ja existeix a {cat}/{a}/{obra}')
                    sys.exit(1)

print('OK')
" 2>/dev/null
}

# Afegeix una proposta validada a obra-queue.json
afegir_a_cua() {
    local json_proposta="$1"
    python3 -c "
import json, sys

proposta = json.loads('''$json_proposta''')
queue_path = '$QUEUE'

with open(queue_path) as f:
    data = json.load(f)

nova = {
    'autor': proposta['autor'],
    'titol': proposta['titol'],
    'llengua': proposta['llengua'],
    'categoria': proposta['categoria'],
    'dificultat': proposta.get('dificultat', 3),
    'paraules_aprox': proposta.get('paraules_aprox', 5000),
    'fonts': proposta.get('fonts', []),
    'status': 'pending',
    'notes': proposta.get('justificacio', '') + (' | ' + proposta.get('notes', '') if proposta.get('notes') else '')
}

data['obres'].append(nova)
data['updated_at'] = '$(date +%Y-%m-%d)'

with open(queue_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f\"Afegida: {nova['autor']} — {nova['titol']} ({nova['llengua']}, {nova['categoria']})\")
" 2>/dev/null
}

# =============================================================================
# EXECUCIÓ PRINCIPAL
# =============================================================================

log "══════════════════════════════════════════════════"
log "📚 Consell Editorial — Sessió iniciada"

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

# 3. Generar prompt i cridar Claude
log "Generant propostes via Claude..."
prompt=$(generar_prompt "$resum")

# Cridar Claude amb timeout i CLAUDECODE netejat per evitar nested sessions
resposta=$(unset CLAUDECODE; timeout 90 claude -p "$prompt" --max-turns 3 --output-format text --allowedTools "" 2>/dev/null) || {
    log "❌ Error cridant Claude. Abortant."
    exit 1
}

# 4. Parsejar la resposta JSON
log "Parsejant propostes..."

# Netejar la resposta: extreure el JSON array
propostes_json=$(python3 -c "
import json, re, sys

raw = sys.stdin.read().strip()

# Intentar trobar un JSON array dins la resposta
# Pot venir amb backticks, text extra, etc.
match = re.search(r'\[.*\]', raw, re.DOTALL)
if not match:
    print('ERROR: No s\'ha trobat cap JSON array a la resposta', file=sys.stderr)
    sys.exit(1)

try:
    arr = json.loads(match.group())
    # Validar que és una llista de dicts
    if not isinstance(arr, list) or not all(isinstance(x, dict) for x in arr):
        print('ERROR: El JSON no és una llista de diccionaris', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(arr, ensure_ascii=False))
except json.JSONDecodeError as e:
    print(f'ERROR: JSON invàlid: {e}', file=sys.stderr)
    sys.exit(1)
" <<< "$resposta") || {
    log "❌ No s'ha pogut parsejar la resposta de Claude."
    log "Resposta rebuda:"
    echo "$resposta" | head -20 | while IFS= read -r line; do log "  $line"; done
    exit 1
}

# 5. Processar cada proposta
n_total=$(python3 -c "import json; print(len(json.loads('''$propostes_json''')))" 2>/dev/null)
n_afegides=0
n_rebutjades=0

log "Propostes rebudes: $n_total"

for i in $(seq 0 $((n_total - 1))); do
    # Limitar al màxim configurat
    if [ "$n_afegides" -ge "$MAX_PROPOSTES" ]; then
        log "Límit de $MAX_PROPOSTES propostes assolit. Saltant les restants."
        break
    fi

    proposta=$(python3 -c "
import json
arr = json.loads('''$propostes_json''')
print(json.dumps(arr[$i], ensure_ascii=False))
" 2>/dev/null)

    autor=$(python3 -c "import json; print(json.loads('''$proposta''').get('autor','?'))" 2>/dev/null)
    titol=$(python3 -c "import json; print(json.loads('''$proposta''').get('titol','?'))" 2>/dev/null)
    categoria=$(python3 -c "import json; print(json.loads('''$proposta''').get('categoria','?'))" 2>/dev/null)
    llengua=$(python3 -c "import json; print(json.loads('''$proposta''').get('llengua','?'))" 2>/dev/null)

    log "── Proposta $((i+1)): $autor — $titol ($llengua, $categoria)"

    # Validar
    validacio=$(validar_proposta "$proposta")
    if [ "$validacio" != "OK" ]; then
        log "   ❌ $validacio"
        n_rebutjades=$((n_rebutjades + 1))
        continue
    fi

    if [ "$DRY_RUN" = true ]; then
        log "   ✅ Vàlida (dry-run, no s'afegeix)"
        justificacio=$(python3 -c "import json; print(json.loads('''$proposta''').get('justificacio',''))" 2>/dev/null)
        log "   Justificació: $justificacio"
    else
        afegir_a_cua "$proposta"
        log "   ✅ Afegida a obra-queue.json"
    fi
    n_afegides=$((n_afegides + 1))
done

# 6. Resum
log "──────────────────────────────────────────────────"
log "📊 Resum: $n_afegides afegides, $n_rebutjades rebutjades (de $n_total propostes)"
if [ "$DRY_RUN" = true ]; then
    log "   (mode dry-run: cap modificació feta)"
fi
log "══════════════════════════════════════════════════"
