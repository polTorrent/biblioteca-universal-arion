#!/usr/bin/env bash
# status.sh — Estat del sistema de desenvolupament autònom d'Arion.
set -uo pipefail

DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BL="$DEV_DIR/backlog"
ST="$DEV_DIR/state"
PROJECT_DIR="${ARION_DIR:-$HOME/biblioteca-universal-arion}"

echo "═══ ARION DEV — ESTAT ═══"
echo "Quota Claude:"
if [ -f "$ST/quota.json" ]; then
    python3 - "$ST/quota.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"  estat={d.get('status')}  ts={d.get('ts')}  reset={d.get('reset') or '-'}")
if d.get("reason"):
    print(f"  motiu={str(d['reason'])[:120]}")
PY
else
    echo "  (cap prova encara)"
fi

echo
echo "Backlog:"
for d in pending running done failed; do
    n="$(ls "$BL/$d" 2>/dev/null | grep -c '\.md$' || true)"
    printf "  %-8s %s\n" "$d" "$n"
done

echo
echo "Pendents:"
ls "$BL/pending" 2>/dev/null | grep '\.md$' | sort | sed 's/^/  /' || echo "  (buit)"

echo
echo "Branca activa: $(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo "Últims commits [auto-dev]:"
git -C "$PROJECT_DIR" log --oneline -12 --grep='\[auto-dev\]' 2>/dev/null | sed 's/^/  /' || true

if [ -f "$ST/dev-worker.lock" ]; then
    pid="$(cat "$ST/dev-worker.lock" 2>/dev/null || echo '?')"
    if kill -0 "$pid" 2>/dev/null; then
        echo
        echo "dev-worker: EN CURS (PID $pid)"
    fi
fi
