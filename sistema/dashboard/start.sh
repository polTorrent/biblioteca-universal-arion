#!/bin/bash
# Arion Dashboard - Instal·lació i Inici

set -e

echo "========================================="
echo "ARION DASHBOARD - Instal·lació"
echo "========================================="
echo ""

# Directori del dashboard
DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DASHBOARD_DIR"

# Instal·lar dependencies Python
echo "📦 Instal·lant dependencies..."
pip3 install flask flask-socketio flask-cors tailer eventlet --quiet

# Crear directori de logssi no existeixen
mkdir -p logs

# Verificar que existeixen els fitxers de log
touch logs/hermes.log
touch logs/llm.log
touch logs/worker.log
touch logs/tools.log

echo "✓ Dependencies instal·lades"
echo ""

# Arrencar el servidor
echo "🚀 Arrencant Dashboard..."
echo "   URL: http://localhost:9120"
echo "   URL (TailScale): http://100.93.26.104:9120"
echo ""
echo "Prem Ctrl+C per aturar"
echo "========================================="
echo ""

# Arrencar Flask amb SocketIO
python3 server.py