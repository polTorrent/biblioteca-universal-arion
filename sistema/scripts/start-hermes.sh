#!/bin/bash
# start-hermes.sh - Inicia serveis Hermes al carregar WSL
# Afegir a .bashrc o .profile: source ~/biblioteca-universal-arion/sistema/scripts/start-hermes.sh

HERMES_SCRIPTS="/home/jo/biblioteca-universal-arion/sistema/scripts"
START_SCRIPT="$HERMES_SCRIPTS/iniciar-serveis-hermes.sh"

# Només executar si no hi ha sessió tmux activa de Hermes
if ! tmux has-session -t hermes-gateway 2>/dev/null; then
    echo "Iniciant serveis Hermes..."
    if [ -x "$START_SCRIPT" ]; then
        "$START_SCRIPT"
    fi
fi