#!/bin/bash
# Iniciar worker amb nohup (tmux no funciona amb claude)
cd ~/biblioteca-universal-arion

# Matar worker anterior si existeix
if [ -f /tmp/worker.pid ]; then
    OLD_PID=$(cat /tmp/worker.pid)
    kill $OLD_PID 2>/dev/null
    sleep 2
fi

# Moure tasques running a pending
mv ~/.openclaw/workspace/tasks/running/*.json ~/.openclaw/workspace/tasks/pending/ 2>/dev/null

# Iniciar
nohup bash sistema/automatitzacio/claude-worker-mini.sh > /dev/null 2>&1 &
echo $! > /tmp/worker.pid
echo "✅ Worker iniciat (PID $!)"
