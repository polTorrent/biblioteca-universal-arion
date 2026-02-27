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
PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
QUEUE="${QUEUE:-$PROJECT/config/obra-queue.json}"
OBRES_DIR="$PROJECT/obres"
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

# Genera un resum del catàleg actual per enviar a Claude
generar_resum_cataleg() {
    python3 -c "
import json, os, sys

queue_path = '$QUEUE'
obres_dir = '$OBRES_DIR'

# Llegir obra-queue.json
with open(queue_path) as f:
    data = json.load(f)
obres_queue = data.get('obres', [])

# Recollir obres dels directoris (per si n'hi ha que no estan a la cua)
obres_dirs = set()
if os.path.isdir(obres_dir):
    for cat in os.listdir(obres_dir):
        cat_path = os.path.join(obres_dir, cat)
        if not os.path.isdir(cat_path):
            continue
        for autor in os.listdir(cat_path):
            autor_path = os.path.join(cat_path, autor)
            if not os.path.isdir(autor_path):
                continue
            for obra in os.listdir(autor_path):
                obra_path = os.path.join(autor_path, obra)
                if os.path.isdir(obra_path):
                    obres_dirs.add(f'{cat}/{autor}/{obra}')

# Resum d'obres a la cua
lines = []
lines.append('OBRES A LA CUA:')
categories = {}
idiomes = set()
autors = set()
for o in obres_queue:
    cat = o.get('categoria', '?')
    autor = o.get('autor', '?')
    titol = o.get('titol', '?')
    llengua = o.get('llengua', '?')
    status = o.get('status', '?')
    lines.append(f'  - [{status}] {autor}: {titol} ({llengua}, {cat})')
    categories[cat] = categories.get(cat, 0) + 1
    idiomes.add(llengua)
    autors.add(autor)

lines.append('')
lines.append('OBRES ALS DIRECTORIS (traduïdes o en procés):')
for d in sorted(obres_dirs):
    lines.append(f'  - {d}')

lines.append('')
lines.append('ESTADÍSTIQUES:')
lines.append(f'  Total obres cua: {len(obres_queue)}')
for cat, count in sorted(categories.items()):
    lines.append(f'  - {cat}: {count}')
lines.append(f'  Idiomes: {\", \".join(sorted(idiomes))}')
lines.append(f'  Autors: {\", \".join(sorted(autors))}')

# Detectar buits
all_cats = {'filosofia', 'narrativa', 'poesia', 'teatre', 'assaig', 'oriental'}
missing_cats = all_cats - set(categories.keys())
if missing_cats:
    lines.append(f'  Categories SENSE obres: {\", \".join(sorted(missing_cats))}')

print('\n'.join(lines))
" 2>/dev/null
}

# Genera el prompt complet per Claude
generar_prompt() {
    local resum="$1"
    cat <<PROMPT_EOF
Ets el Consell Editorial de la Biblioteca Universal Arion, una biblioteca oberta de traduccions al català d'obres clàssiques universals.

CATÀLEG ACTUAL:
$resum

CRITERIS DE SELECCIÓ (per ordre de prioritat):
1. DOMINI PÚBLIC: Autor mort fa >70 anys (obligatori)
2. UNIVERSALITAT: Obres del cànon universal reconegut, imprescindibles
3. DIVERSITAT: Categories, idiomes i èpoques poc representades al catàleg
4. INTERÈS: Valor cultural, educatiu, tendència actual, aniversaris
5. TRADUCCIÓ CATALANA: Preferir obres sense traducció catalana o amb traducció antiga (>30 anys) o exhaurida. Evitar duplicar traduccions recents i de qualitat.
6. DIFICULTAT: Preferir obres <15.000 paraules
7. FONTS DISPONIBLES: Que el text original estigui disponible online (Gutenberg, Perseus, Wikisource, Latin Library, Aozora, CText, etc.)

PROPOSA exactament $MAX_PROPOSTES obres noves que diversifiquin el catàleg. Per cada obra retorna JSON:
{
  "autor": "Nom Autor",
  "titol": "Títol Original",
  "llengua": "idioma original",
  "categoria": "filosofia|narrativa|poesia|teatre|assaig|oriental",
  "dificultat": 1-5,
  "paraules_aprox": número,
  "fonts": ["gutenberg", "perseus", "wikisource", "latin_library", "aozora", "ctext"],
  "justificacio": "Per què aquesta obra és prioritària. Inclou info sobre traduccions catalanes existents si en tens constància.",
  "notes": "observacions"
}

Respon NOMÉS amb un JSON array, sense markdown, sense backticks, sense explicacions.
IMPORTANT: No repeteixis autors ni obres del catàleg actual. Diversifica al màxim.
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
resposta=$(unset CLAUDECODE; timeout 90 claude -p "$prompt" --max-turns 1 2>/dev/null) || {
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
