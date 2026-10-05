#!/bin/bash
# Arion Mission Control — Dashboard Launcher
PORT=${1:-9090}

# Matar instància anterior si existeix
tmux kill-session -t dashboard 2>/dev/null
sleep 1

# Llançar en tmux
tmux new-session -d -s dashboard "cd ~/biblioteca-universal-arion && python3 scripts/dashboard_server.py --port $PORT"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     🏛  ARION — Mission Control              ║"
echo "║                                              ║"
echo "║   ✅ Dashboard actiu a:                      ║"
echo "║   → http://localhost:$PORT                   ║"
echo "║                                              ║"
echo "║   Aturar: tmux kill-session -t dashboard     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Obrir navegador automàticament
if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$PORT" 2>/dev/null &
elif command -v wslview &>/dev/null; then
    wslview "http://localhost:$PORT" 2>/dev/null &
elif command -v explorer.exe &>/dev/null; then
    explorer.exe "http://localhost:$PORT" 2>/dev/null &
fi
