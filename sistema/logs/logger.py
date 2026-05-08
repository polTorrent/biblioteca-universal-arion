#!/usr/bin/env python3
"""
logger.py — Logger JSON estructurat per al sistema Arion.

Ús:
    python3 sistema/logs/logger.py worker task_started --task-id "x" --obra "y"
    python3 sistema/logs/logger.py error task_failed --task-id "x" --error "timeout"

Els logs s'escriuen a:
    sistema/logs/structured.log  (JSON lines — un per línia)
    sistema/logs/worker.log      (format humà)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
STRUCTURED_LOG = LOG_DIR / "structured.log"
HUMAN_LOG = LOG_DIR / "worker.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(component: str, event: str, level: str = "info", **kwargs) -> None:
    """Escriu entrada de log estructurat (JSON) i humà."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "event": event,
        "level": level,
    }
    entry.update(kwargs)

    # JSON lines (estructurat)
    with open(STRUCTURED_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Format humà
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    ts = entry["timestamp"][:19].replace("T", " ")
    emoji = {"info": "📋", "warning": "⚠️", "error": "❌", "critical": "🚨", "success": "✅"}.get(level, "•")
    human = f"[{ts}] {emoji} [{component}] {event}"
    if extra:
        human += f" ({extra})"
    with open(HUMAN_LOG, "a", encoding="utf-8") as f:
        f.write(human + "\n")


def main():
    parser = argparse.ArgumentParser(description="Logger JSON per Arion")
    parser.add_argument("component", help="Component (worker, heartbeat, traduccio, fetch)")
    parser.add_argument("event", help="Event (task_started, task_completed, error, etc.)")
    parser.add_argument("--level", default="info", choices=["info", "warning", "error", "critical", "success"])
    parser.add_argument("--task-id", help="ID de la tasca")
    parser.add_argument("--obra", help="Ruta de l'obra")
    parser.add_argument("--model", help="Model utilitzat")
    parser.add_argument("--diem", type=float, help="Saldo DIEM")
    parser.add_argument("--error", help="Missatge d'error")
    parser.add_argument("--duration", type=float, help="Durada en segons")

    args = parser.parse_args()
    kwargs = {k: v for k, v in vars(args).items()
              if k not in ("component", "event", "level") and v is not None}

    log(args.component, args.event, args.level, **kwargs)


if __name__ == "__main__":
    main()
