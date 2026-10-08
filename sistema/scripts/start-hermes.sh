#!/bin/bash
# start-hermes.sh - Inicia serveis Hermes al carregar WSL
# Afegir a .bashrc o .profile: source ~/biblioteca-universal-arion/sistema/scripts/start-hermes.sh

HERMES_SCRIPTS="/home/jo/biblioteca-universal-arion/sistema/scripts"
START_SCRIPT="$HERMES_SCRIPTS/iniciar-serveis-hermes.sh"

# Només executar si el gateway no està corrent. Mirar la sessió tmux NO serveix
# per al gateway (viu fora de tmux, l'engega hermes-ensure.sh amb nohup): la
# sessió no existeix mai i el banner sortia a cada shell interactiva. 8-10-2026.
if ! pgrep -f "[h]ermes gateway" > /dev/null; then
    echo "Iniciant serveis Hermes..."
    if [ -x "$START_SCRIPT" ]; then
        "$START_SCRIPT"
    fi
fi