#!/bin/bash
# aturar-serveis-hermes.sh - Atura tots els serveis Hermes

echo "=== Aturant serveis Hermes ==="

# Aturar gateway tmux session
if tmux has-session -t hermes-gateway 2>/dev/null; then
    echo "Aturant gateway..."
    tmux send-keys -t hermes-gateway C-c 2>/dev/null || true
    sleep 2
    tmux kill-session -t hermes-gateway 2>/dev/null || true
    echo "✓ Gateway aturat"
else
    echo "Gateway no està corrent"
fi

# Aturar dashboard tmux session
if tmux has-session -t hermes-dashboard 2>/dev/null; then
    echo "Aturant dashboard..."
    tmux send-keys -t hermes-dashboard C-c 2>/dev/null || true
    sleep 2
    tmux kill-session -t hermes-dashboard 2>/dev/null || true
    echo "✓ Dashboard aturat"
else
    echo "Dashboard no està corrent"
fi

echo ""
echo "=== Estat final ==="
hermes gateway status 2>/dev/null || echo "Gateway: aturat"
tmux list-sessions 2>/dev/null || echo "Cap sessió tmux activa"