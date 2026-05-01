#!/bin/bash
# Llistar tasques fallides amb prioritat
for f in ~/.openclaw/workspace/tasks/failed/*.json; do
    if [ -f "$f" ]; then
        priority=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('prioritat', 9))" 2>/dev/null)
        tipus=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('tipus', '?'))" 2>/dev/null)
        retries=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('retries', 0))" 2>/dev/null)
        filename=$(basename "$f")
        echo "P${priority} | ${filename} | ${tipus} | retries: ${retries}"
    fi
done | sort