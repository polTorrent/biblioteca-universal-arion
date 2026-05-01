#!/bin/bash
# Iniciar worker Venice AI amb nohup
# El worker usa DeepSeek V4 Pro per totes les tasques

cd ~/biblioteca-universal-arion

# Matem qualsevol worker antic de claude (si existeix)
pkill -f "claude-worker" 2>/dev/null || true
sleep 1

# Netegem el lockfile si existeix
rm -f ~/.openclaw/workspace/tasks/worker.lock 2>/dev/null

# Iniciem el worker nou
nohup bash sistema/automatitzacio/venice-worker.sh > /dev/null 2>&1 &

echo "✅ Venice Worker iniciat (PID $!)"
echo "   Logs: tail -f ~/venice-worker.log"
echo "   Status: bash sistema/automatitzacio/worker-status.sh"