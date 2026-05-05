#!/bin/bash
# Iniciar worker Venice AI amb nohup
# El worker usa GLM-5 (Venice) per totes les tasques

PROJECT="$HOME/biblioteca-universal-arion"
cd "$PROJECT"

# Matem qualsevol worker antic (si existeix)
pkill -f "venice-worker" 2>/dev/null || true
pkill -f "claude-worker" 2>/dev/null || true
sleep 1

# Netegem el lockfile si existeix
rm -f "$PROJECT/sistema/tasks/worker.lock" 2>/dev/null

# Iniciem el worker nou
nohup bash sistema/automatitzacio/venice-worker.sh > /dev/null 2>&1 &

echo "✅ Venice Worker iniciat (PID $!)"
echo "   Logs: tail -f ~/venice-worker.log"
echo "   Status: bash sistema/automatitzacio/worker-status.sh"