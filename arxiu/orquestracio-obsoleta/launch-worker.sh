#!/bin/bash
# Launcher persistent per al worker de Biblioteca Arion
# Usa setsid per desenganxar el worker del terminal

cd /home/jo/biblioteca-universal-arion

# Eliminar lock antic si existeix
rm -f sistema/tasks/worker.lock

# Llançar amb setsid (nova sessió, independent del terminal)
setsid bash sistema/automatitzacio/worker.sh --mode=hybrid >> /home/jo/biblioteca-universal-arion/sistema/logs/worker.log 2>&1 &

sleep 1
# Mostrar PID del procés worker
pgrep -f "worker.sh --mode=hybrid" | head -1
