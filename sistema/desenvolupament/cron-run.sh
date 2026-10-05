#!/usr/bin/env bash
# cron-run.sh — Executa el dev-worker i emet NOMÉS un resum si hi ha hagut canvis
# o errors. Si tot va bé i no passa res, no diu res (patró watchdog, silenciós).
set -uo pipefail

DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${ARION_DIR:-$HOME/biblioteca-universal-arion}"
BL="$DEV_DIR/backlog"

count() { ls "$BL/$1" 2>/dev/null | grep -c '\.md$' || true; }

before_done="$(count done)"
before_failed="$(count failed)"
before_head="$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null)"

bash "$DEV_DIR/dev-worker.sh" >/dev/null 2>&1

after_done="$(count done)"
after_failed="$(count failed)"

new_done=$((after_done - before_done))
new_fail=$((after_failed - before_failed))

q="$(python3 -c 'import json;print(json.load(open("'"$DEV_DIR"'/state/quota.json")).get("status","?"))' 2>/dev/null || echo '?')"

if [ "$new_done" -gt 0 ] || [ "$new_fail" -gt 0 ]; then
    echo "🤖 Arion Dev — +$new_done fetes, +$new_fail fallides (quota=$q)"
    ls -t "$BL/done" 2>/dev/null | grep '\.md$' | head -n "$new_done" 2>/dev/null | sed 's/^/  ✔ /'
    ls -t "$BL/failed" 2>/dev/null | grep '\.md$' | head -n "$new_fail" 2>/dev/null | sed 's/^/  ✘ /'
elif [ "$q" = "LIMIT" ]; then
    echo "⏸ Arion Dev — quota Claude esgotada. Esperant el reset."
fi
# En qualsevol altre cas: silenci.
