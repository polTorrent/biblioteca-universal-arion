#!/bin/bash
# iniciar-gateway-tmux.sh - Inicia el gateway i dashboard amb tmux
# Executar a l'inici de WSL

set -e

# Funció per iniciar servei en tmux
start_in_tmux() {
    local name="$1"
    local command="$2"
    
    if tmux has-session -t "$name" 2>/dev/null; then
        echo "✓ $name ja està corrent (tmux session: $name)"
    else
        echo "Iniciant $name..."
        tmux new-session -d -s "$name" -x 120 -y 40 "$command"
        sleep 2
        if tmux has-session -t "$name" 2>/dev/null; then
            echo "✓ $name iniciat correctament"
        else
            echo "✗ Error iniciant $name"
        fi
    fi
}

echo "=== Iniciant serveis Hermes ==="
echo ""

# Iniciar dashboard
start_in_tmux "hermes-dashboard" "hermes dashboard --host 0.0.0.0 --port 9119 --no-open --insecure --tui"

# Iniciar gateway
start_in_tmux "hermes-gateway" "hermes gateway run"

echo ""
echo "=== Estat dels serveis ==="
echo ""
echo "Dashboard:"
tmux capture-pane -t hermes-dashboard -p 2>/dev/null | tail -5 || echo "  (output no disponible)"
echo ""
echo "Gateway:"
tmux capture-pane -t hermes-gateway -p 2>/dev/null | tail -5 || echo "  (output no disponible)"

echo ""
echo "=== Sessions tmux actives ==="
tmux list-sessions 2>/dev/null || echo "Cap sessió activa"

echo ""
echo "=== Comandes útils ==="
echo "  tmux attach -t hermes-dashboard  # Veure dashboard"
echo "  tmux attach -t hermes-gateway     # Veure gateway"
echo "  tmux list-sessions                # Llistar sessions"
echo "  Ctrl+b d                          # Desconnectar sense aturar"
echo "  Ctrl+c                            # Aturar servei"
echo ""
echo "Per aturar tots els serveis: ./aturar-serveis-hermes.sh"