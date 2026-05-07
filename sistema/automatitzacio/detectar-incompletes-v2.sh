#!/bin/bash
# =============================================================================
# detectar-incompletes-v2.sh — Detecta obres incompletes comparant amb l'original
# =============================================================================
# Millora: Compara mida original vs traducció en lloc de només línies
# =============================================================================

set -uo pipefail

PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$PROJECT/sistema/tasks"
MIN_RATIO=0.4  # Mínim 30% de l'original

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INCOMPLETES-V2] $1"; }

# Comptar paraules d'un fitxer (més fiable que línies)
count_words() {
    local file="$1"
    if [ -f "$file" ]; then
        # Comptar paraules, ignorant metadades YAML i comentaris
        grep -v "^---\|^#\|^$" "$file" 2>/dev/null | wc -w
    else
        echo 0
    fi
}

# Comptar unitats de verificació segons gènere (més precís)
count_units() {
    local file="$1"
    if [ -f "$file" ]; then
        # Intentar comptar segons patró del gènere
        # Aforismes: ### N o **N.**
        # Paràgrafs: numerats o separats per línia en blanc
        # Estrofes: ## o separades
        # Seccions: # o §
        local units=$(grep -cE "^### |^\*\*[0-9]+\.\*\*|^§ |^Capítol " "$file" 2>/dev/null || echo "0")
        if [ "$units" -lt 5 ]; then
            # Si poques unitats formals, usar paràgrafs
            units=$(awk '/./ {if (blank++ > 0) count++; blank=0} !/./ {blank++} END {print count+1}' "$file" 2>/dev/null || echo "1")
        fi
        echo "$units"
    else
        echo 0
    fi
}

# Crear tasca de completar
create_task() {
    local obra_path="$1"
    local original_words="$2"
    local traduccio_words="$3"
    local ratio="$4"
    local slug=$(basename "$obra_path")
    
    local task_id="$(date +%s)_translate_completar-${slug}"
    local priority="1"  # Alta prioritat per obres molt incompletes
    
    local instruction="COMPLETA la traducció de '${slug}'. "
    instruction+="L'original té ${original_words} paraules però la traducció només en té ${traduccio_words} (${ratio}% completat). "
    instruction+="Continua des d'on s'ha quedat seguint EXACTAMENT l'estil existent. "
    instruction+="IMPORTANT: Verifica amb 'python3 scripts/verificar_traduccio.py' abans de finalitzar."
    
    local task_file="$TASKS_DIR/pending/${task_id}.json"
    cat > "$task_file" <<EOF
{
  "id": "$task_id",
  "type": "translate",
  "priority": $priority,
  "max_time": 90,
  "instruction": "$instruction",
  "metadata": {
    "obra_path": "$obra_path",
    "original_words": $original_words,
    "traduccio_words": $traduccio_words,
    "ratio": $ratio,
    "slug": "$slug"
  }
}
EOF
    
    log "✅ $slug: ${original_words}→${traduccio_words} paraules (${ratio}%)"
}

# =============================================================================
# ESCANEAR TOTES LES OBRES
# =============================================================================

log "🔍 Analitzant totes les obres..."
log "   Criteri: traducció < ${MIN_RATIO} de l'original"

found=0
max_tasks=15

# Trobar totes les obres amb original i traducció
while IFS= read -r -d '' traduccio; do
    obra_dir=$(dirname "$traduccio")
    original="$obra_dir/original.md"
    
    # Si existeix l'original
    if [ -f "$original" ]; then
        # Comptar paraules
        orig_words=$(count_words "$original")
        trad_words=$(count_words "$traduccio")
        
        # Calcular ràtio (evitant divisió per zero)
        if [ "$orig_words" -gt 0 ]; then
            ratio=$(python3 -c "print(f'{$trad_words / $orig_words * 100:.1f}')")
            
            # Si la traducció és molt menor que l'original
            if [ "$(python3 -c "print($trad_words / $orig_words < $MIN_RATIO)")" = "True" ]; then
                # Comprovar si ja hi ha tasca
                if ! grep -rq "$(basename "$obra_dir")" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null; then
                    if [ "$found" -lt "$max_tasks" ]; then
                        create_task "$obra_dir" "$orig_words" "$trad_words" "$ratio"
                        found=$((found + 1))
                    fi
                fi
            fi
        fi
    fi
done < <(find "$PROJECT/obres" -name "traduccio.md" -type f -print0)

log "📊 Total tasques creades: $found"

# Notificar al worker
if [ "$found" -gt 0 ]; then
    log "🚀 Notificant al worker..."
    touch "$PROJECT/sistema/state/worker_trigger"
fi