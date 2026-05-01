#!/bin/bash
# Recuperar tasques fallides amb retries < 3
cd ~/.openclaw/workspace/tasks

for f in failed/*.json; do
    if [ -f "$f" ]; then
        retries=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('retries', 0))" 2>/dev/null)
        if [ "$retries" -lt 3 ]; then
            filename=$(basename "$f")
            mv "$f" "pending/$filename"
            echo "Mogut: $filename (retries: $retries)"
        fi
    fi
done