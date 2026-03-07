#!/bin/bash
# =============================================================================
# processar-propostes.sh - Processa propostes de Discord i crea tasques
# =============================================================================
# Es crida des del heartbeat o manualment
# Comprova el canal de propostes, processa les noves, crea tasques
# =============================================================================

set -eo pipefail

PROJECT="$HOME/biblioteca-universal-arion"
CONFIG="$PROJECT/config/propostes-discord.json"
PROPOSTES_DIR="$PROJECT/propostes"
PROPOSTES_PROCESSADES="$HOME/.openclaw/workspace/propostes-processades.txt"
LOG="$HOME/claude-worker.log"

# Crear directoris si no existeixen
mkdir -p "$PROPOSTES_DIR"
mkdir -p "$(dirname "$PROPOSTES_PROCESSADES")"
touch "$PROPOSTES_PROCESSADES"

# Log amb timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [PROPOSTES] $1" >> "$LOG"
    echo "$1"
}

# Funció per crear tasca al worker
crear_tasca() {
    local titol="$1"
    local idioma="${2:-desconegut}"
    local usuari_id="${3:-desconegut}"
    local timestamp=$(date +%s)
    local task_id="${timestamp}_proposta_${RANDOM}"
    
    # Crear fitxer de tasca
    cat > "$PROPOSTES_DIR/${task_id}.json" << EOF
{
  "id": "${task_id}",
  "type": "proposta",
  "description": "Tradueix: ${titol}",
  "titol": "${titol}",
  "idioma_original": "${idioma}",
  "usuari_discord_id": "${usuari_id}",
  "status": "pending",
  "created_at": "$(date -Iseconds)",
  "source": "discord_form"
}
EOF
    
    # Afegir a la cua del worker
    if [ -f "$PROJECT/task-queue.json" ]; then
        python3 << PYTHON
import json
with open("$PROJECT/task-queue.json", "r+") as f:
    try:
        data = json.load(f)
    except:
        data = []
    data.append({
        "id": "${task_id}",
        "type": "proposta",
        "description": "Tradueix: ${titol}",
        "usuari_discord_id": "${usuari_id}",
        "status": "pending",
        "created_at": "$(date -Iseconds)"
    })
    f.seek(0)
    json.dump(data, f, indent=2)
    f.truncate()
PYTHON
    fi
    
    # Guardar com a processada
    echo "${task_id}|${titol}|${usuari_id}|$(date -Iseconds)" >> "$PROPOSTES_PROCESSADES"
    
    log "✅ Proposta creada: ${titol} (usuari: ${usuari_id})"
    
    # Retornar task_id
    echo "$task_id"
}

# Funció per verificar si una obra s'ha publicat
verificar_publicacio() {
    local titol="$1"
    local obra_dir=""
    
    # Buscar l'obra al catàleg
    obra_dir=$(find "$PROJECT/obres" -type f -name "*.md" | xargs grep -l -i "$titol" 2>/dev/null | head -1)
    
    if [ -n "$obra_dir" ]; then
        local obra_path=$(dirname "$obra_dir")
        if [ -f "$obra_path/.validated" ]; then
            return 0  # Publicada
        fi
    fi
    return 1  # No publicada
}

# Funció per notificar usuari via Discord
notificar_usuari() {
    local usuari_id="$1"
    local titol="$2"
    local estat="$3"
    
    log "📨 Enviant notificació a ${usuari_id}: ${titol} - ${estat}"
    
    # Enviar notificació real mitjançant OpenClaw
    # Utilitza el canal de notificacions de Discord
    local canal_notificacions="1479504522614476953"
    local missatge=""
    
    case "$estat" in
        "publicada")
            missatge="🎉 **La teva proposta ja està disponible!**\n\n📚 **${titol}** ha estat traduït i publicat.\n\n🔗 Visita la biblioteca per llegir-lo: https://biblioteca-arion.cat\n\nGràcies per la teva proposta! <@${usuari_id}>"
            ;;
        "en_progres")
            missatge="📖 **Traducció en curs**\n\n📚 **${titol}** s'està traduint.\n\nT'avisarem quan estigui disponible!"
            ;;
        *)
            missatge="📋 **Actualització de proposta**\n\n📚 **${titol}** - Estat: ${estat}"
            ;;
    esac
    
    # Guardar per al heartbeat
    cat > "$HOME/.openclaw/workspace/pending_notification.txt" << EOF
channel:${canal_notificacions}
user:${usuari_id}
message:${missatge}
timestamp:$(date -Iseconds)
EOF
    
    log "✅ Notificació preparada per enviar"
}

# Funció principal per processar propostes noves
processar_propostes_noves() {
    log "🔍 Comprovant propostes noves..."
    
    # Aquesta funció serà cridada quan es detecti una nova proposta
    # Les propostes arriben via el formulari de Discord
    
    # Comprovar fitxers de proposta temporals creats pel formulari
    for proposta_file in "$PROPOSTES_DIR"/tmp_*.json 2>/dev/null; do
        if [ -f "$proposta_file" ]; then
            log "📋 Processant: $proposta_file"
            
            titol=$(python3 -c "import json; print(json.load(open('$proposta_file')).get('titol', ''))")
            idioma=$(python3 -c "import json; print(json.load(open('$proposta_file')).get('idioma', 'desconegut'))")
            usuari=$(python3 -c "import json; print(json.load(open('$proposta_file')).get('usuari_id', 'desconegut'))")
            
            if [ -n "$titol" ]; then
                crear_tasca "$titol" "$idioma" "$usuari"
                rm "$proposta_file"
            fi
        fi
    done
}

# Funció per comprovar propostes publicades i notificar
comprovar_publicacions() {
    log "🔍 Comprovant propostes publicades..."
    
    while IFS='|' read -r task_id titol usuari_id created_at; do
        if [ -n "$titol" ] && [ -n "$usuari_id" ]; then
            if verificar_publicacio "$titol"; then
                log "🎉 Publicada: $titol"
                notificar_usuari "$usuari_id" "$titol" "publicada"
                
                # Marcar com a notificada
                sed -i "s/^${task_id}|/${task_id}|NOTIFICAT|/" "$PROPOSTES_PROCESSADES"
            fi
        fi
    done < "$PROPOSTES_PROCESSADES"
}

# Main
case "${1:-}" in
    " crear")
        shift
        crear_tasca "$@"
        ;;
    "verificar")
        comprovar_publicacions
        ;;
    "processar")
        processar_propostes_noves
        ;;
    "notificar")
        shift
        notificar_usuari "$@"
        ;;
    *)
        processar_propostes_noves
        comprovar_publicacions
        ;;
esac