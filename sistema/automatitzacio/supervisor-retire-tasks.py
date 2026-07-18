#!/usr/bin/env python3
# =============================================================================
# supervisor-retire-tasks.py — Retirar tasques a failed_permanent amb metadades
# =============================================================================
# Ús: python3 supervisor-retire-tasks.py <reason> <file_basename> [<file_basename> ...]
#
# Mou els fitxers de pending/ o failed/ a failed_permanent/, etiquetant
# status="failed_permanent" i last_error amb la raó indicada. El patró de
# dedup de millora-continua.sh (grep -lF "MILLORA CONTÍNUA de '<obra>'")
# coincideix contra el fitxer a failed_permanent/ i evita recrear-lo.
# =============================================================================
import json, os, sys, shutil
from pathlib import Path

PROJECT = Path(os.environ.get("PROJECT", os.path.expanduser("~/biblioteca-universal-arion")))
TASKS_DIR = PROJECT / "sistema" / "tasks"
REASON = sys.argv[1] if len(sys.argv) > 1 else "Supervisor retira tasca"
FILES = sys.argv[2:]

if not FILES:
    print("Ús: supervisor-retire-tasks.py <rao> <file> [<file> ...]", file=sys.stderr)
    sys.exit(2)

moved, skipped = [], []
for basename in FILES:
    src = None
    for sub in ("pending", "failed", "running"):
        cand = TASKS_DIR / sub / basename
        if cand.exists():
            src = cand
            break
    if src is None:
        print(f"SKIP (no trobat a pending/failed/running): {basename}", file=sys.stderr)
        skipped.append(basename)
        continue
    dst = TASKS_DIR / "failed_permanent" / basename
    try:
        d = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR parsejant {basename}: {e}", file=sys.stderr)
        skipped.append(basename)
        continue
    d["status"] = "failed_permanent"
    d["retired_at"] = os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip()
    d["retired_by"] = "supervisor"
    d["last_error"] = REASON
    dst.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    src.unlink()
    print(f"MOVED: {src.relative_to(PROJECT)} -> {dst.relative_to(PROJECT)}")
    moved.append(basename)

print(f"\nResum: {len(moved)} retirades, {len(skipped)} saltades.")