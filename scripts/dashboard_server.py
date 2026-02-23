#!/usr/bin/env python3
"""Dashboard de Monitorització — Biblioteca Universal Arion

Servidor web que mostra en temps real l'estat de tot el sistema:
- Worker autònom (Claude Code)
- Cua de tasques
- Obres i traduccions
- Pipeline de traducció
- Sistema (CPU, RAM, disc)
- OpenClaw
- Logs en temps real

Ús: python3 scripts/dashboard_server.py [--port 8080]
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import threading

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓ
# ═══════════════════════════════════════════════════════════════

PROJECT_DIR = Path.home() / "biblioteca-universal-arion"
TASKS_DIR = Path.home() / ".openclaw" / "workspace" / "tasks"
LOG_FILE = Path.home() / "claude-worker.log"
QUEUE_FILE = PROJECT_DIR / "config" / "obra-queue.json"
PORT = 8080

# ═══════════════════════════════════════════════════════════════
# DATA COLLECTORS
# ═══════════════════════════════════════════════════════════════

def get_worker_status():
    """Estat del worker (tmux session)."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", "worker"],
            capture_output=True, timeout=5
        )
        active = result.returncode == 0
        pid = None
        if active:
            r = subprocess.run(
                ["tmux", "list-panes", "-t", "worker", "-F", "#{pane_pid}"],
                capture_output=True, text=True, timeout=5
            )
            pid = r.stdout.strip() if r.returncode == 0 else None
        return {"active": active, "pid": pid}
    except Exception:
        return {"active": False, "pid": None}


def get_tasks():
    """Comptar i llistar tasques."""
    result = {"pending": [], "running": [], "done_today": 0, "done_total": 0, "failed": []}
    today = datetime.now().strftime("%Y-%m-%d")

    for status in ["pending", "running", "failed"]:
        d = TASKS_DIR / status
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                data["_filename"] = f.name
                result[status].append(data)
            except Exception:
                result[status].append({"id": f.stem, "type": "?", "error": "parse_fail"})

    done_dir = TASKS_DIR / "done"
    if done_dir.exists():
        for f in done_dir.glob("*.json"):
            result["done_total"] += 1
            try:
                stat = f.stat()
                mod_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                if mod_date == today:
                    result["done_today"] += 1
            except Exception:
                pass

    return result


def get_obres():
    """Estat de totes les obres."""
    obres = []
    obres_dir = PROJECT_DIR / "obres"
    if not obres_dir.exists():
        return obres

    for categoria in sorted(obres_dir.iterdir()):
        if not categoria.is_dir():
            continue
        for autor in sorted(categoria.iterdir()):
            if not autor.is_dir():
                continue
            for obra in sorted(autor.iterdir()):
                if not obra.is_dir():
                    continue
                files = [f.name for f in obra.iterdir()]
                has_original = "original.md" in files
                has_trad = "traduccio.md" in files
                has_glossari = any(f.startswith("glossari") for f in files)
                has_notes = "notes.md" in files
                has_portada = any(f.startswith("portada") for f in files)
                has_validated = ".validated" in files
                has_needs_fix = ".needs_fix" in files
                has_fixing = ".fixing" in files

                # Determinar estat
                if has_validated:
                    estat = "validated"
                elif has_fixing:
                    estat = "fixing"
                elif has_needs_fix:
                    estat = "needs_fix"
                elif has_trad:
                    estat = "translated"
                elif has_original:
                    estat = "original_only"
                else:
                    estat = "empty"

                # Puntuació si té .validated o .needs_fix
                score = None
                if has_validated:
                    try:
                        content = (obra / ".validated").read_text()
                        import re
                        m = re.search(r'(\d+\.?\d*)/10', content)
                        if m:
                            score = float(m.group(1))
                    except Exception:
                        pass
                elif has_needs_fix:
                    try:
                        content = (obra / ".needs_fix").read_text()
                        import re
                        m = re.search(r'(\d+\.?\d*)/10', content)
                        if m:
                            score = float(m.group(1))
                    except Exception:
                        pass

                # Línies traducció
                trad_lines = 0
                if has_trad:
                    try:
                        trad_lines = len((obra / "traduccio.md").read_text().splitlines())
                    except Exception:
                        pass

                obres.append({
                    "categoria": categoria.name,
                    "autor": autor.name,
                    "obra": obra.name,
                    "path": str(obra.relative_to(PROJECT_DIR)),
                    "estat": estat,
                    "score": score,
                    "has_original": has_original,
                    "has_trad": has_trad,
                    "has_glossari": has_glossari,
                    "has_notes": has_notes,
                    "has_portada": has_portada,
                    "trad_lines": trad_lines,
                    "files_count": len(files),
                })
    return obres


def get_queue():
    """Obra-queue.json."""
    if not QUEUE_FILE.exists():
        return []
    try:
        data = json.loads(QUEUE_FILE.read_text())
        return data.get("obres", data.get("queue", []))
    except Exception:
        return []


def get_logs(n=50):
    """Últimes n línies del log."""
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text().splitlines()
        return lines[-n:]
    except Exception:
        return []


def get_system():
    """Info del sistema."""
    import shutil
    total, used, free = shutil.disk_usage(str(Path.home()))

    # CPU load
    try:
        with open("/proc/loadavg") as f:
            load = f.read().split()[:3]
    except Exception:
        load = ["?", "?", "?"]

    # Memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val) * 1024  # kB to bytes
            mem_total = meminfo.get("MemTotal", 0)
            mem_available = meminfo.get("MemAvailable", 0)
            mem_used = mem_total - mem_available
    except Exception:
        mem_total = mem_used = mem_available = 0

    # Uptime
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.read().split()[0])
    except Exception:
        uptime_seconds = 0

    return {
        "disk_total_gb": round(total / (1024**3), 1),
        "disk_used_gb": round(used / (1024**3), 1),
        "disk_free_gb": round(free / (1024**3), 1),
        "disk_percent": round(used / total * 100, 1) if total > 0 else 0,
        "mem_total_gb": round(mem_total / (1024**3), 2),
        "mem_used_gb": round(mem_used / (1024**3), 2),
        "mem_percent": round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0,
        "cpu_load": load,
        "uptime_hours": round(uptime_seconds / 3600, 1),
    }


def get_git_log(n=10):
    """Últims commits."""
    try:
        r = subprocess.run(
            ["git", "-C", str(PROJECT_DIR), "log", f"-{n}",
             "--format=%H|%h|%s|%an|%ar|%ai"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return []
        commits = []
        for line in r.stdout.strip().splitlines():
            parts = line.split("|", 5)
            if len(parts) >= 6:
                commits.append({
                    "hash": parts[0], "short": parts[1],
                    "message": parts[2], "author": parts[3],
                    "relative": parts[4], "date": parts[5],
                })
        return commits
    except Exception:
        return []


def get_openclaw_status():
    """Estat d'OpenClaw."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "openclaw"], capture_output=True, text=True, timeout=5
        )
        active = r.returncode == 0
        pids = r.stdout.strip().splitlines() if active else []
        return {"active": active, "pids": pids}
    except Exception:
        return {"active": False, "pids": []}


def get_diem_balance():
    """Llegir saldo DIEM del last_heartbeat o log."""
    try:
        for line in reversed(get_logs(100)):
            if "DIEM:" in line:
                import re
                m = re.search(r'DIEM:\s*([\d.]+)', line)
                if m:
                    return float(m.group(1))
    except Exception:
        pass
    return None


def collect_all_data():
    """Recull totes les dades del sistema."""
    return {
        "timestamp": datetime.now().isoformat(),
        "worker": get_worker_status(),
        "tasks": get_tasks(),
        "obres": get_obres(),
        "queue": get_queue(),
        "system": get_system(),
        "git": get_git_log(),
        "openclaw": get_openclaw_status(),
        "diem": get_diem_balance(),
        "logs": get_logs(80),
        "lock_file": (Path.home() / ".openclaw/workspace/tasks/worker.lock").exists(),
        "last_log_time": None,
    }


# ═══════════════════════════════════════════════════════════════
# DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arion — Mission Control</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg-primary: #0a0e17;
  --bg-secondary: #111827;
  --bg-card: #151d2e;
  --bg-card-hover: #1a2540;
  --border: #1e2d4a;
  --border-glow: #2563eb33;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #475569;
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --accent-green: #10b981;
  --accent-emerald: #34d399;
  --accent-yellow: #f59e0b;
  --accent-orange: #f97316;
  --accent-red: #ef4444;
  --accent-purple: #8b5cf6;
  --accent-pink: #ec4899;
  --gradient-blue: linear-gradient(135deg, #3b82f6, #06b6d4);
  --gradient-green: linear-gradient(135deg, #10b981, #34d399);
  --gradient-warm: linear-gradient(135deg, #f59e0b, #f97316);
  --shadow-glow: 0 0 30px rgba(59, 130, 246, 0.1);
  --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
  --font-mono: 'JetBrains Mono', monospace;
  --font-display: 'DM Sans', sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-display);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Subtle background grid */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(59, 130, 246, 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(6, 182, 212, 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(139, 92, 246, 0.02) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

/* ═══ HEADER ═══ */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(10, 14, 23, 0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  font-family: var(--font-mono);
  font-size: 1.3rem;
  font-weight: 700;
  background: var(--gradient-blue);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.5px;
}

.logo span { opacity: 0.5; font-weight: 300; }

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  font-family: var(--font-mono);
}

.status-live {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-green);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-live .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent-green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.refresh-timer { opacity: 0.6; }

/* ═══ LAYOUT ═══ */
.dashboard {
  position: relative;
  z-index: 1;
  max-width: 1600px;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* ═══ STATS ROW ═══ */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
}

.stat-card:hover {
  border-color: var(--accent-blue);
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.stat-card .label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  font-family: var(--font-mono);
}

.stat-card .value {
  font-size: 2rem;
  font-weight: 700;
  font-family: var(--font-mono);
  line-height: 1;
}

.stat-card .sub {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.3rem;
  font-family: var(--font-mono);
}

.stat-blue .value { color: var(--accent-blue); }
.stat-blue::before { background: var(--gradient-blue); }
.stat-green .value { color: var(--accent-green); }
.stat-green::before { background: var(--gradient-green); }
.stat-yellow .value { color: var(--accent-yellow); }
.stat-yellow::before { background: var(--gradient-warm); }
.stat-purple .value { color: var(--accent-purple); }
.stat-purple::before { background: linear-gradient(135deg, #8b5cf6, #ec4899); }
.stat-cyan .value { color: var(--accent-cyan); }
.stat-cyan::before { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
.stat-red .value { color: var(--accent-red); }
.stat-red::before { background: linear-gradient(135deg, #ef4444, #f97316); }

/* ═══ GRID PANELS ═══ */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
  background: rgba(255,255,255,0.01);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.panel-body { padding: 1rem 1.25rem; }
.panel-body.no-pad { padding: 0; }

/* ═══ OBRES TABLE ═══ */
.obra-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 0.85rem;
  transition: background 0.2s;
}

.obra-row:hover { background: var(--bg-card-hover); }

.obra-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.obra-name .cat {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.obra-autor { color: var(--text-secondary); font-size: 0.8rem; }

.obra-score {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.85rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.6rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-family: var(--font-mono);
  font-weight: 500;
}

.badge-validated { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
.badge-needs-fix { background: rgba(245, 158, 11, 0.15); color: var(--accent-yellow); }
.badge-fixing { background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); }
.badge-translated { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
.badge-original { background: rgba(71, 85, 105, 0.2); color: var(--text-muted); }
.badge-corrupted { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }

/* ═══ TASK LIST ═══ */
.task-item {
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.task-type {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 600;
  white-space: nowrap;
}

.type-supervision { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); }
.type-translation { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
.type-fix { background: rgba(245, 158, 11, 0.15); color: var(--accent-yellow); }
.type-publish { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
.type-review { background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); }
.type-default { background: rgba(71, 85, 105, 0.2); color: var(--text-secondary); }

.task-instruction {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* ═══ LOG CONSOLE ═══ */
.log-console {
  background: #080c14;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
  padding: 1rem;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-muted);
}

.log-line.heartbeat { color: var(--accent-cyan); }
.log-line.success { color: var(--accent-green); }
.log-line.error { color: var(--accent-red); }
.log-line.warning { color: var(--accent-yellow); }
.log-line.fix { color: var(--accent-purple); }

/* ═══ GIT LOG ═══ */
.commit-item {
  padding: 0.5rem 1.25rem;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  font-size: 0.8rem;
}

.commit-hash {
  font-family: var(--font-mono);
  color: var(--accent-blue);
  font-size: 0.72rem;
  flex-shrink: 0;
}

.commit-msg { color: var(--text-secondary); flex: 1; }
.commit-time {
  font-family: var(--font-mono);
  color: var(--text-muted);
  font-size: 0.7rem;
  flex-shrink: 0;
}

/* ═══ PROGRESS BARS ═══ */
.progress-bar {
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 0.5rem;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 1s ease;
}

.progress-blue { background: var(--gradient-blue); }
.progress-green { background: var(--gradient-green); }
.progress-yellow { background: var(--gradient-warm); }
.progress-red { background: linear-gradient(135deg, #ef4444, #f97316); }

/* ═══ SYSTEM GAUGES ═══ */
.gauge-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.gauge-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  font-family: var(--font-mono);
}

.gauge-label { color: var(--text-secondary); }
.gauge-value { color: var(--text-primary); font-weight: 500; }

/* ═══ PIPELINE FLOW ═══ */
.pipeline-flow {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem 0;
  flex-wrap: wrap;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  color: var(--text-muted);
  transition: all 0.3s;
}

.pipeline-step.active {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.pipeline-step.done {
  background: rgba(16, 185, 129, 0.1);
  border-color: var(--accent-green);
  color: var(--accent-green);
}

.pipeline-arrow {
  color: var(--text-muted);
  font-size: 0.8rem;
  opacity: 0.4;
}

/* ═══ RESPONSIVE ═══ */
@media (max-width: 1200px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .stats-row { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 768px) {
  .header { padding: 0.75rem 1rem; }
  .dashboard { padding: 1rem; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}

/* ═══ CONTROL BUTTONS ═══ */
.ctrl-btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.ctrl-btn:hover { transform: translateY(-1px); }
.ctrl-btn:active { transform: translateY(0); }
.ctrl-btn.btn-green { border-color: var(--accent-green); color: var(--accent-green); }
.ctrl-btn.btn-green:hover { background: rgba(16, 185, 129, 0.15); box-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }
.ctrl-btn.btn-blue { border-color: var(--accent-blue); color: var(--accent-blue); }
.ctrl-btn.btn-blue:hover { background: rgba(59, 130, 246, 0.15); box-shadow: 0 0 15px rgba(59, 130, 246, 0.2); }
.ctrl-btn.btn-yellow { border-color: var(--accent-yellow); color: var(--accent-yellow); }
.ctrl-btn.btn-yellow:hover { background: rgba(245, 158, 11, 0.15); box-shadow: 0 0 15px rgba(245, 158, 11, 0.2); }
.ctrl-btn.btn-orange { border-color: var(--accent-orange); color: var(--accent-orange); }
.ctrl-btn.btn-orange:hover { background: rgba(249, 115, 22, 0.15); box-shadow: 0 0 15px rgba(249, 115, 22, 0.2); }
.ctrl-btn.loading { opacity: 0.5; pointer-events: none; }

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-in { animation: fadeIn 0.4s ease-out; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo">ARION <span>Mission Control</span></div>
    <div class="status-badge status-live" id="live-badge">
      <div class="dot"></div>
      <span>LIVE</span>
    </div>
  </div>
  <div class="header-right">
    <span id="clock"></span>
    <span class="refresh-timer" id="refresh-timer">↻ 15s</span>
  </div>
</div>

<div class="dashboard" id="dashboard">
  <div class="stats-row" id="stats-row"></div>

  <!-- Control Panel -->
  <div class="panel" style="border-color:var(--accent-blue)">
    <div class="panel-header">
      <div class="panel-title">🎛 Control Panel</div>
      <span id="action-status" style="font-family:var(--font-mono);font-size:0.75rem;color:var(--accent-green)"></span>
    </div>
    <div class="panel-body" style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center">
      <button onclick="doAction('restart-worker')" class="ctrl-btn btn-green">▶ Restart Worker</button>
      <button onclick="doAction('heartbeat')" class="ctrl-btn btn-blue">💓 Heartbeat</button>
      <button onclick="doAction('clear-lock')" class="ctrl-btn btn-yellow">🔓 Clear Lock</button>
      <button onclick="doAction('clear-running')" class="ctrl-btn btn-orange">♻️ Unstick Tasks</button>
      <div id="worker-detail" style="margin-left:auto;font-family:var(--font-mono);font-size:0.72rem;color:var(--text-secondary)"></div>
    </div>
  </div>

  <!-- Pipeline Flow -->
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">⚡ Pipeline Cicle de Vida</div>
    </div>
    <div class="panel-body">
      <div class="pipeline-flow" id="pipeline-flow"></div>
    </div>
  </div>

  <div class="grid-2">
    <!-- Obres -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">📚 Obres</div>
        <span id="obres-count" style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted)"></span>
      </div>
      <div class="panel-body no-pad" id="obres-list" style="max-height:450px;overflow-y:auto"></div>
    </div>

    <!-- Tasks -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">📋 Cua de Tasques</div>
        <span id="tasks-count" style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted)"></span>
      </div>
      <div class="panel-body no-pad" id="tasks-list" style="max-height:450px;overflow-y:auto"></div>
    </div>
  </div>

  <div class="grid-3">
    <!-- Log Console -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">🖥 Terminal</div>
      </div>
      <div class="log-console" id="log-console"></div>
    </div>

    <!-- Right column -->
    <div style="display:flex;flex-direction:column;gap:1.5rem">
      <!-- System -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">💻 Sistema</div>
        </div>
        <div class="panel-body">
          <div class="gauge-row" id="system-gauges"></div>
        </div>
      </div>

      <!-- Git Log -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">📝 Git</div>
        </div>
        <div class="panel-body no-pad" id="git-log" style="max-height:250px;overflow-y:auto"></div>
      </div>
    </div>
  </div>
</div>

<script>
const REFRESH_INTERVAL = 15000;
let countdown = 15;
let data = null;

// ═══ CLOCK ═══
function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('ca-ES', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
setInterval(updateClock, 1000);
updateClock();

// ═══ REFRESH TIMER ═══
setInterval(() => {
  countdown--;
  if (countdown <= 0) countdown = Math.round(REFRESH_INTERVAL/1000);
  document.getElementById('refresh-timer').textContent = `↻ ${countdown}s`;
}, 1000);

// ═══ RENDER STATS ═══
function renderStats(d) {
  const tasks = d.tasks;
  const obres = d.obres;
  const validated = obres.filter(o => o.estat === 'validated').length;
  const needsFix = obres.filter(o => o.estat === 'needs_fix').length;
  const totalTrad = obres.filter(o => o.has_trad).length;

  const cards = [
    { label: 'Traduccions', value: totalTrad, sub: `de ${obres.length} obres`, cls: 'stat-blue' },
    { label: 'Validades', value: validated, sub: `${totalTrad > 0 ? Math.round(validated/totalTrad*100) : 0}% completat`, cls: 'stat-green' },
    { label: 'Pendents Fix', value: needsFix, sub: needsFix > 0 ? 'en procés' : 'tot OK', cls: needsFix > 0 ? 'stat-yellow' : 'stat-green' },
    { label: 'Done Avui', value: tasks.done_today, sub: `${tasks.done_total} total`, cls: 'stat-purple' },
    { label: 'Cua', value: tasks.pending.length, sub: `${tasks.running.length} running`, cls: 'stat-cyan' },
    { label: 'DIEM', value: d.diem ? d.diem.toFixed(1) : '?', sub: 'saldo', cls: 'stat-yellow' },
  ];

  document.getElementById('stats-row').innerHTML = cards.map(c => `
    <div class="stat-card ${c.cls} animate-in">
      <div class="label">${c.label}</div>
      <div class="value">${c.value}</div>
      <div class="sub">${c.sub}</div>
    </div>
  `).join('');
}

// ═══ RENDER PIPELINE ═══
function renderPipeline(d) {
  const obres = d.obres;
  const counts = {
    pending: obres.filter(o => o.estat === 'empty' || o.estat === 'original_only').length,
    translated: obres.filter(o => o.estat === 'translated').length,
    supervision: d.tasks.pending.filter(t => (t.type||'').includes('supervis')).length + d.tasks.running.filter(t => (t.type||'').includes('supervis')).length,
    needs_fix: obres.filter(o => o.estat === 'needs_fix').length,
    fixing: obres.filter(o => o.estat === 'fixing').length,
    validated: obres.filter(o => o.estat === 'validated').length,
  };

  const steps = [
    { icon: '📥', label: 'Pending', count: counts.pending, key: 'pending' },
    { icon: '🔄', label: 'Traducció', count: counts.translated, key: 'translated' },
    { icon: '🔍', label: 'Supervisió', count: counts.supervision, key: 'supervision' },
    { icon: '🔧', label: 'Needs Fix', count: counts.needs_fix, key: 'needs_fix' },
    { icon: '⚙️', label: 'Fixing', count: counts.fixing, key: 'fixing' },
    { icon: '✅', label: 'Validat', count: counts.validated, key: 'validated' },
    { icon: '🌐', label: 'Web', count: counts.validated, key: 'web' },
  ];

  document.getElementById('pipeline-flow').innerHTML = steps.map((s, i) => {
    const cls = s.count > 0 ? (s.key === 'validated' || s.key === 'web' ? 'done' : 'active') : '';
    return `${i > 0 ? '<span class="pipeline-arrow">→</span>' : ''}
      <div class="pipeline-step ${cls}">
        ${s.icon} ${s.label} <strong>${s.count}</strong>
      </div>`;
  }).join('');
}

// ═══ RENDER OBRES ═══
function renderObres(d) {
  const obres = d.obres.sort((a, b) => {
    const order = { validated: 0, fixing: 1, needs_fix: 2, translated: 3, original_only: 4, empty: 5 };
    return (order[a.estat] || 5) - (order[b.estat] || 5);
  });

  document.getElementById('obres-count').textContent = `${obres.length} obres`;
  document.getElementById('obres-list').innerHTML = obres.map(o => {
    const badgeCls = {
      validated: 'badge-validated', needs_fix: 'badge-needs-fix',
      fixing: 'badge-fixing', translated: 'badge-translated',
      original_only: 'badge-original', empty: 'badge-original',
    }[o.estat] || 'badge-original';

    const badgeText = {
      validated: '✅ Validat', needs_fix: '⚠️ Fix', fixing: '🔧 Fixing',
      translated: '📝 Traduït', original_only: '📄 Original', empty: '📁 Buit',
    }[o.estat] || o.estat;

    const scoreText = o.score !== null ? `${o.score}/10` : '';
    const scoreColor = o.score !== null ? (o.score >= 7 ? 'var(--accent-green)' : o.score >= 5 ? 'var(--accent-yellow)' : 'var(--accent-red)') : '';

    const icons = [
      o.has_original ? '📄' : '',
      o.has_trad ? '📝' : '',
      o.has_glossari ? '📖' : '',
      o.has_notes ? '🗒' : '',
      o.has_portada ? '🎨' : '',
    ].filter(Boolean).join('');

    return `<div class="obra-row">
      <div class="obra-name">
        <span>${o.obra.replace(/-/g, ' ')}</span>
        <span class="cat">${o.categoria}</span>
      </div>
      <div class="obra-autor">${o.autor.replace(/-/g, ' ')}</div>
      <div class="obra-score" style="color:${scoreColor}">${scoreText}</div>
      <div style="display:flex;gap:0.5rem;align-items:center">
        <span style="font-size:0.7rem;letter-spacing:1px">${icons}</span>
        <span class="badge ${badgeCls}">${badgeText}</span>
      </div>
    </div>`;
  }).join('');
}

// ═══ RENDER TASKS ═══
function renderTasks(d) {
  const tasks = [...d.tasks.running.map(t => ({...t, _status: 'running'})),
                 ...d.tasks.pending.map(t => ({...t, _status: 'pending'})),
                 ...d.tasks.failed.map(t => ({...t, _status: 'failed'}))];

  document.getElementById('tasks-count').textContent = `${tasks.length} actives`;
  document.getElementById('tasks-list').innerHTML = tasks.length === 0
    ? '<div class="task-item" style="color:var(--text-muted)">Cap tasca activa — tot completat 🎉</div>'
    : tasks.map(t => {
      const type = t.type || 'task';
      const typeCls = {
        supervision: 'type-supervision', translation: 'type-translation', translate: 'type-translation',
        fix: 'type-fix', publish: 'type-publish', review: 'type-review',
      }[type] || 'type-default';

      const statusIcon = { running: '⚡', pending: '⏳', failed: '❌' }[t._status] || '•';
      const instr = (t.instruction || t.id || '').substring(0, 120);

      return `<div class="task-item">
        <span>${statusIcon}</span>
        <span class="task-type ${typeCls}">${type}</span>
        <span class="task-instruction">${instr}</span>
      </div>`;
    }).join('');
}

// ═══ RENDER LOGS ═══
function renderLogs(d) {
  const el = document.getElementById('log-console');
  const wasAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;

  el.innerHTML = d.logs.map(line => {
    let cls = 'log-line';
    if (line.includes('HEARTBEAT')) cls += ' heartbeat';
    else if (line.includes('✅') || line.includes('completad')) cls += ' success';
    else if (line.includes('❌') || line.includes('Error') || line.includes('ERROR')) cls += ' error';
    else if (line.includes('⚠️') || line.includes('WARNING')) cls += ' warning';
    else if (line.includes('FIX') || line.includes('🔧')) cls += ' fix';
    return `<div class="${cls}">${line}</div>`;
  }).join('');

  if (wasAtBottom) el.scrollTop = el.scrollHeight;
}

// ═══ RENDER SYSTEM ═══
function renderSystem(d) {
  const sys = d.system;
  const gauges = [
    { label: 'CPU Load', value: `${sys.cpu_load[0]}`, pct: Math.min(parseFloat(sys.cpu_load[0]) * 25, 100), color: 'blue' },
    { label: 'Memòria', value: `${sys.mem_used_gb}/${sys.mem_total_gb} GB`, pct: sys.mem_percent, color: sys.mem_percent > 80 ? 'red' : 'green' },
    { label: 'Disc', value: `${sys.disk_used_gb}/${sys.disk_total_gb} GB`, pct: sys.disk_percent, color: sys.disk_percent > 85 ? 'red' : 'yellow' },
  ];

  const worker = d.worker;
  const oc = d.openclaw;

  document.getElementById('system-gauges').innerHTML = `
    <div style="display:flex;gap:1rem;margin-bottom:0.5rem">
      <div class="badge ${worker.active ? 'badge-validated' : 'badge-corrupted'}">
        Worker ${worker.active ? '✅ Actiu' : '❌ Inactiu'}
      </div>
      <div class="badge ${oc.active ? 'badge-validated' : 'badge-corrupted'}">
        OpenClaw ${oc.active ? '✅ Actiu' : '❌ Inactiu'}
      </div>
    </div>
    ${gauges.map(g => `
      <div class="gauge-item">
        <div class="gauge-header">
          <span class="gauge-label">${g.label}</span>
          <span class="gauge-value">${g.value} (${g.pct.toFixed(0)}%)</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill progress-${g.color}" style="width:${g.pct}%"></div>
        </div>
      </div>
    `).join('')}
    <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem">
      Uptime: ${sys.uptime_hours}h
    </div>
  `;
}

// ═══ RENDER GIT ═══
function renderGit(d) {
  document.getElementById('git-log').innerHTML = d.git.map(c => `
    <div class="commit-item">
      <span class="commit-hash">${c.short}</span>
      <span class="commit-msg">${c.message}</span>
      <span class="commit-time">${c.relative}</span>
    </div>
  `).join('');
}

// ═══ FETCH & RENDER ALL ═══
async function refresh() {
  try {
    const resp = await fetch('/api/status');
    data = await resp.json();

    renderStats(data);
    renderPipeline(data);
    renderObres(data);
    renderTasks(data);
    renderLogs(data);
    renderSystem(data);
    renderGit(data);
    renderWorkerDetail(data);

    document.getElementById('live-badge').className = 'status-badge status-live';
  } catch (e) {
    document.getElementById('live-badge').innerHTML = '<span style="color:var(--accent-red)">● OFFLINE</span>';
  }
  countdown = Math.round(REFRESH_INTERVAL/1000);
}

// ═══ ACTIONS ═══
async function doAction(action) {
  const btn = event.target;
  const statusEl = document.getElementById('action-status');
  btn.classList.add('loading');
  btn.textContent += ' ...';
  statusEl.textContent = '⏳ Executant...';
  statusEl.style.color = 'var(--accent-yellow)';

  try {
    const resp = await fetch(`/api/actions/${action}`);
    const data = await resp.json();
    statusEl.textContent = data.ok ? `✅ ${data.msg}` : `❌ ${data.msg}`;
    statusEl.style.color = data.ok ? 'var(--accent-green)' : 'var(--accent-red)';
    setTimeout(refresh, 2000);
  } catch (e) {
    statusEl.textContent = `❌ Error: ${e.message}`;
    statusEl.style.color = 'var(--accent-red)';
  }

  btn.classList.remove('loading');
  btn.textContent = btn.textContent.replace(' ...', '');
  setTimeout(() => { statusEl.textContent = ''; }, 8000);
}

// ═══ WORKER DETAIL ═══
function renderWorkerDetail(d) {
  const el = document.getElementById('worker-detail');
  const worker = d.worker;
  const lock = d.lock_file;
  const running = d.tasks.running.length;
  const lastLog = d.logs.length > 0 ? d.logs[d.logs.length - 1].substring(0, 50) : 'cap';

  let html = '';
  if (!worker.active) {
    html += '<span style="color:var(--accent-red)">⚠️ WORKER ATURAT</span>';
    if (lock) html += ' | <span style="color:var(--accent-yellow)">🔒 Lock actiu</span>';
  } else {
    html += `<span style="color:var(--accent-green)">PID: ${worker.pid || '?'}</span>`;
  }
  if (running > 0) html += ` | ⚡ ${running} running`;
  el.innerHTML = html;
}

refresh();
setInterval(refresh, REFRESH_INTERVAL);
</script>
<div id="tsec" class="card" style="margin-top:1rem;">
<div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
<h3 style="font-size:0.85rem;">⌨ Terminal</h3>
<div style="display:flex;gap:6px;"><div style="width:8px;height:8px;border-radius:50%;background:#ef4444"></div><div style="width:8px;height:8px;border-radius:50%;background:#f59e0b"></div><div style="width:8px;height:8px;border-radius:50%;background:#10b981"></div></div></div>
<div id="to" style="font-family:var(--font-mono);font-size:12px;line-height:1.7;padding:12px 16px;max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.3);"><div style="color:var(--accent-blue)">Arion v4 — 'help' per comandes</div></div>
<div style="display:flex;align-items:center;gap:8px;padding:8px 16px;border-top:1px solid var(--border);">
<span style="color:var(--accent-green);font-family:var(--font-mono);font-size:12px;">arion$</span>
<input id="ti" type="text" placeholder="help..." style="flex:1;background:transparent;border:none;outline:none;color:var(--text-primary);font-family:var(--font-mono);font-size:12px;" autocomplete="off"></div></div>
<script>
(function(){var O=document.getElementById('to'),I=document.getElementById('ti'),H=[],hi=-1;
function ad(t,c){var d=document.createElement('div');d.style.cssText='color:'+(c||'#94a3b8')+';white-space:pre-wrap;word-break:break-word';d.textContent=t;O.appendChild(d);O.scrollTop=O.scrollHeight;}
function pr(s){var d=document.createElement('div');d.innerHTML='<span style="color:#10b981">arion</span><span style="color:#475569">$</span> <span style="color:#e2e8f0">'+s.replace(/</g,'&lt;')+'</span>';O.appendChild(d);}
async function ap(p,b){try{var r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return await r.json();}catch(e){return{error:e.message};}}
async function ex(cmd){if(!cmd.trim())return;H.unshift(cmd);hi=-1;pr(cmd);var p=cmd.trim().split(/\s+/),c=p[0].toLowerCase(),a=p.slice(1).join(' ');
if(c==='help'){['═══ ARION COMMANDS ═══','','  tradueix <autor> <obra> [ll]  Traducció','  revisa <obra>                Supervisió','  corregeix <obra>             Correcció','  cerca <autor> <obra>          Cerca font','  portada <obra>               Portada','  estat                        Estat','  worker restart|stop          Worker','  heartbeat                    Heartbeat','  build / publish              Web','  logs [n] / obres / cua       Info','  clear / help                 Terminal'].forEach(function(l){ad(l);});return;}
if(c==='clear'){O.innerHTML='';ad('Netejat.','#3b82f6');return;}
if(c==='estat'||c==='status'){ad('📊 Carregant...','#f59e0b');var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && echo "═══ ESTAT ═══" && (tmux has-session -t worker 2>/dev/null && echo "Worker: ✅ ACTIU" || echo "Worker: ❌ INACTIU") && echo "Obres: $(find obres/ -name traduccio.md|wc -l) | Val: $(find obres/ -name .validated|wc -l) | Fix: $(find obres/ -name .needs_fix|wc -l)" && echo "Pend: $(ls ~/.openclaw/workspace/tasks/pending/*.json 2>/dev/null|wc -l) | Run: $(ls ~/.openclaw/workspace/tasks/running/*.json 2>/dev/null|wc -l) | Done: $(find ~/.openclaw/workspace/tasks/done/ -name \\*.json -newermt $(date +%Y-%m-%d) 2>/dev/null|wc -l)"'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});if(r.error)ad('❌ '+r.error,'#ef4444');return;}
if(c==='tradueix'||c==='traduir'){if(!a){ad('Ús: tradueix <autor> <obra>','#ef4444');return;}ad('📝 Creant traducció: '+a,'#8b5cf6');var r=await ap('/api/task',{type:'translation',instruction:"Tradueix "+a+". Usa Pipeline V2.",duration:60});ad(r.success?'✅ Tasca creada':'❌ '+(r.error||r.output),r.success?'#10b981':'#ef4444');return;}
if(c==='revisa'||c==='supervisa'){if(!a){ad('Ús: revisa <obra>','#ef4444');return;}ad('🔎 Supervisió: '+a,'#3b82f6');var r=await ap('/api/task',{type:'supervision',instruction:"Supervisa qualitat de "+a+". Puntua 0-10.",duration:30});ad(r.success?'✅ Tasca creada':'❌ Error',r.success?'#10b981':'#ef4444');return;}
if(c==='corregeix'||c==='fix'){if(!a){ad('Ús: corregeix <obra>','#ef4444');return;}ad('🔧 Fix: '+a,'#f59e0b');var r=await ap('/api/task',{type:'fix',instruction:"Corregeix "+a+". Llegeix .needs_fix.",duration:45});ad(r.success?'✅ Tasca creada':'❌ Error',r.success?'#10b981':'#ef4444');return;}
if(c==='cerca'||c==='busca'){if(!a){ad('Ús: cerca <autor> <obra>','#ef4444');return;}ad('🔍 Cercant...','#06b6d4');var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && python3 scripts/cercador_fonts_v2.py '+a});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='portada'){if(!a){ad('Ús: portada <obra>','#ef4444');return;}ad('🎨 Portada: '+a,'#ec4899');var r=await ap('/api/task',{type:'design',instruction:"Genera portada per "+a+" amb Venice AI.",duration:15});ad(r.success?'✅ Creada':'❌ Error',r.success?'#10b981':'#ef4444');return;}
if(c==='worker'){var s=p[1];if(s==='restart'){ad('🔄 Reiniciant...','#f59e0b');var r=await ap('/api/execute',{command:'tmux kill-session -t worker 2>/dev/null; mv ~/.openclaw/workspace/tasks/running/*.json ~/.openclaw/workspace/tasks/pending/ 2>/dev/null; sleep 2; cd ~/biblioteca-universal-arion && tmux new-session -d -s worker "bash scripts/claude-worker-mini.sh" && sleep 2 && echo "✅ Reiniciat"'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});}else if(s==='stop'){ad('🛑 Aturant...','#ef4444');await ap('/api/execute',{command:'tmux kill-session -t worker 2>/dev/null && echo "Aturat"'});}else ad('worker restart|stop','#94a3b8');return;}
if(c==='heartbeat'){ad('💓 Executant...','#f59e0b');var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && bash scripts/heartbeat.sh 2>&1|tail -30'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='build'){ad('🏗️ Build...','#06b6d4');var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && python3 scripts/build.py --clean 2>&1'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='publish'){ad('🚀 Publicant...','#10b981');var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && python3 scripts/build.py --clean 2>&1 && git add -A && git commit -m "build: web" && git push 2>&1'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='logs'){var n=parseInt(p[1])||20;var r=await ap('/api/execute',{command:'grep -v HEARTBEAT ~/claude-worker.log|tail -'+n});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='obres'){var r=await ap('/api/execute',{command:'cd ~/biblioteca-universal-arion && for d in obres/*/*/*/;do n=$(basename "$d");t="$d/traduccio.md";[ -f "$t" ]||continue;l=$(wc -l<"$t");s="⏳";[ -f "$d/.validated" ]&&s="✅";[ -f "$d/.needs_fix" ]&&s="🔧";echo "$s $n ($l ln)";done|sort'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
if(c==='cua'){var r=await ap('/api/execute',{command:'echo "PENDING:" && ls ~/.openclaw/workspace/tasks/pending/*.json 2>/dev/null|while read f;do echo "  ⏳ $(basename $f .json)";done && echo "RUNNING:" && ls ~/.openclaw/workspace/tasks/running/*.json 2>/dev/null|while read f;do echo "  🔄 $(basename $f .json)";done'});if(r.output)r.output.split('\n').forEach(function(l){ad(l);});return;}
ad("Desconegut: '"+c+"'. Escriu 'help'.",'#ef4444');}
I.addEventListener('keydown',function(e){if(e.key==='Enter'){ex(I.value);I.value='';}else if(e.key==='ArrowUp'){e.preventDefault();hi=Math.min(hi+1,H.length-1);if(H[hi])I.value=H[hi];}else if(e.key==='ArrowDown'){e.preventDefault();hi=Math.max(hi-1,-1);I.value=hi>=0?H[hi]:'';}else if(e.key==='Tab'){e.preventDefault();var v=I.value.toLowerCase(),CS=['tradueix','revisa','corregeix','cerca','portada','estat','worker restart','worker stop','heartbeat','build','publish','obres','cua','logs','clear','help'];var m=CS.find(function(c){return c.startsWith(v)});if(m)I.value=m+' ';}});
document.getElementById('tsec').addEventListener('click',function(){I.focus();});
})();
</script>

</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTTP SERVER
# ═══════════════════════════════════════════════════════════════

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif path == "/api/actions/restart-worker":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                import subprocess
                subprocess.run(["rm", "-f", str(Path.home() / ".openclaw/workspace/tasks/worker.lock")], timeout=5)
                subprocess.run(["tmux", "kill-session", "-t", "worker"], capture_output=True, timeout=5)
                time.sleep(1)
                subprocess.Popen(
                    ["tmux", "new-session", "-d", "-s", "worker",
                     f"cd {PROJECT_DIR} && bash scripts/claude-worker-mini.sh"],
                )
                self.wfile.write(json.dumps({"ok": True, "msg": "Worker reiniciat"}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({"ok": False, "msg": str(e)}).encode())

        elif path == "/api/actions/heartbeat":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                import subprocess
                r = subprocess.run(
                    ["bash", str(PROJECT_DIR / "scripts/heartbeat.sh")],
                    capture_output=True, text=True, timeout=120
                )
                self.wfile.write(json.dumps({"ok": r.returncode == 0, "msg": r.stdout[-500:] if r.stdout else r.stderr[-500:]}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({"ok": False, "msg": str(e)}).encode())

        elif path == "/api/actions/clear-lock":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                lock = Path.home() / ".openclaw/workspace/tasks/worker.lock"
                if lock.exists():
                    lock.unlink()
                    self.wfile.write(json.dumps({"ok": True, "msg": "Lock eliminat"}).encode())
                else:
                    self.wfile.write(json.dumps({"ok": True, "msg": "No hi havia lock"}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({"ok": False, "msg": str(e)}).encode())

        elif path == "/api/actions/clear-running":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                running_dir = TASKS_DIR / "running"
                pending_dir = TASKS_DIR / "pending"
                moved = 0
                if running_dir.exists():
                    for f in running_dir.glob("*.json"):
                        f.rename(pending_dir / f.name)
                        moved += 1
                self.wfile.write(json.dumps({"ok": True, "msg": f"{moved} tasques retornades a pending"}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({"ok": False, "msg": str(e)}).encode())

        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                result = collect_all_data()
                self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        cl = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(cl).decode('utf-8')
        parsed = urlparse(self.path)
        if parsed.path == '/api/execute':
            try:
                data = json.loads(body)
                cmd = data.get('command', '')
                safe = 'biblioteca-universal-arion' in cmd or any(cmd.strip().startswith(p) for p in ['cat ','ls ','grep ','tail ','head ','tmux ','git ','find ','wc ','echo ','mv '])
                if not safe:
                    self.send_response(403); self.send_header('Content-Type','application/json'); self.end_headers()
                    self.wfile.write(json.dumps({"error":"No permes"}).encode()); return
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd=str(PROJECT_DIR))
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({"output":(result.stdout+result.stderr)[-5000:],"returncode":result.returncode}).encode())
            except Exception as e:
                self.send_response(500); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({"error":str(e)}).encode())
            return
        if parsed.path == '/api/task':
            try:
                data = json.loads(body)
                t,instr,dur = data.get('type','translation'), data.get('instruction',''), data.get('duration',30)
                cmd = f'bash {PROJECT_DIR}/scripts/task-manager.sh add {t} "{instr}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({"success":result.returncode==0,"output":result.stdout+result.stderr}).encode())
            except Exception as e:
                self.send_response(500); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({"error":str(e)}).encode())
            return

    def log_message(self, format, *args):
        pass  # Silenciar logs del servidor


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Arion Dashboard")
    parser.add_argument("--port", type=int, default=PORT, help="Port")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    print(f"""
╔══════════════════════════════════════════════════╗
║        🏛  ARION — Mission Control               ║
║                                                  ║
║   Dashboard: http://localhost:{args.port}            ║
║                                                  ║
║   Auto-refresh cada 15 segons                    ║
║   Ctrl+C per aturar                              ║
╚══════════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard aturat")
        server.server_close()


if __name__ == "__main__":
    main()
