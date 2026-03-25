#!/bin/bash
# propostes-discord.sh - Processa propostes del canal Discord i crea tasques
# Usage: ./propostes-discord.sh

set -e

CANAL_PROPOSTES="1479599316380291276"
PROPOSTES_FILE="$HOME/.openclaw/workspace/propostes-processades.txt"
TASK_QUEUE="$HOME/biblioteca-universal-arion/task-queue.json"

# Crear fitxer de propostes processades si no existeix
mkdir -p "$(dirname "$PROPOSTES_FILE")"
touch "$PROPOSTES_FILE"

# Obtenir missatges del canal de propostes (via OpenClaw API)
# Això requereix que l'API estigui disponible

# Funció per crear tasca
crear_tasca() {
    local titol="$1"
    local usuari="$2"
    local timestamp=$(date +%s)
    local task_id="${timestamp}_proposta"
    
    # Crear fitxer de tasca
    cat > "$HOME/biblioteca-universal-arion/tasks/proposals/${task_id}.json" << EOF
{
    "id": "${task_id}",
    "type": "proposta",
    "description": "Proposta: ${titol}",
    "titol": "${titol}",
    "usuari_discord": "${usuari}",
    "status": "pending",
    "created_at": "$(date -Iseconds)"
}
EOF
    
    echo "✅ Tasca creada: ${task_id}"
    echo "${task_id}|${titol}|${usuari}|$(date -Iseconds)" >> "$PROPOSTES_FILE"
}

# Funció per notificar usuari
notificar_usuari() {
    local usuari_id="$1"
    local missatge="$2"
    
    # Enviar missatge via Discord
    # Això es fariavia l'API de Discord o OpenClaw
    echo "📨 Notificant usuari ${usuari_id}: ${missatge}"
}

# Main
echo "🔍 Comprovant propostes noves..."

# Aquí aniria la lògica per obtenir missatges del canal
# Per ara, retornem status
echo "📊 Propostes processades: $(wc -l < "$PROPOSTES_FILE")"