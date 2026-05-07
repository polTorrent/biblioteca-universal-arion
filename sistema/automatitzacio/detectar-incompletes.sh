#!/bin/bash
# =============================================================================  
# detectar-incompletes.sh — Detecta obres incompletes i genera tasques
# =============================================================================
# Executa cada X hores per generar tasques de completar traduccions
# =============================================================================

set -uo pipefail

PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$PROJECT/sistema/tasks"
MIN_LINES=100  # Mínim de línies per considerar una traducció completa

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INCOMPLETES] $1"; }

# Comptar tasques pendents
count_pending() {
    ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l
}

# Crear tasca de completar traducció
create_task() {
    local obra_path="$1"
    local lines="$2"
    local slug=$(basename "$obra_path")
    local author=$(basename $(dirname "$obra_path"))
    local category=$(basename $(dirname $(dirname "$obra_path")))
    
    local task_id="$(date +%s)_translate_completar-${slug}"
    local priority="1"  # Alta prioritat
    
    # Generar instrucció específica
    local instruction="COMPLETA la traducció de '${slug}' (${category}/${author}). "
    instruction+="Actualment té només ${lines} línies (mínim esperat: ${MIN_LINES}). "
    instruction+="Continua la traducció des d'on s'ha quedat seguint exactament l'estil i format existents. "
    instruction+="Si necessites l'original, revisa original.md a la mateixa carpeta."
    
    # Escriu tasca
    local task_file="$TASKS_DIR/pending/${task_id}.json"
    cat > "$task_file" <<EOF
{
  "id": "$task_id",
  "type": "translate",
  "priority": $priority,
  "max_time": 60,
  "instruction": "$instruction",
  "metadata": {
    "obra_path": "$obra_path",
    "lines": $lines,
    "category": "$category",
    "author": "$author",
    "slug": "$slug"
  }
}
EOF
    
    log "✅ Tasca creada: $task_id"
    log "   Obra: $slug | Línies: $lines"
}

# =============================================================================
# CERCAR OBRES INCOMPLETES
# =============================================================================

log "🔍 Cercant obres incompletes (< $MIN_LINES línies)..."

found=0
max_tasks=10  # Màxim de tasques per execució

# Cercar totes les traduccions
while IFS= read -r -d '' traduccio; do
    # Comptar línies
    lines=$(wc -l < "$traduccio")
    
    # Si té menys del mínim i no té fitxer .completed ni .validated
    obra_dir=$(dirname "$traduccio")
    if [ "$lines" -lt "$MIN_LINES" ]; then
        if [ ! -f "$obra_dir/.completed" ] && [ ! -f "$obra_dir/.validated" ]; then
            # Comprovar si ja hi ha tasca per aquesta obra
            if ! grep -r "$(basename \"$obra_dir\")" "$TASKS_DIR/pending/" "$TASKS_DIR/running/" 2>/dev/null; then
                if [ "$found" -lt "$max_tasks" ]; then
                    create_task "$obra_dir" "$lines"
                    found=$((found + 1))
                fi
            fi
        fi
    fi
done < <(find "$PROJECT/obres" -name "traduccio.md" -type f -print0)

log "📊 Total tasques creades: $found"

# Si hem creat tasques, notificar al worker
if [ "$found" -gt 0 ]; then
    log "🚀 Notificant al worker..."
    touch "$PROJECT/sistema/state/worker_trigger"
fi