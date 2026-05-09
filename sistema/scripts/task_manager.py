#!/usr/bin/env python3
"""
task_manager.py — Gestor de tasques per Biblioteca Arion
- Deduplicació per hash (no es repeteix la mateixa tasca)
- Prioritats: 1=urgent, 5=normal, 9=baixa
- Dependències entre tasques
- Retry automàtic amb backoff
"""
import json, os, hashlib, time, sys, uuid
from pathlib import Path
from datetime import datetime

PROJECT = Path(os.path.expanduser("~/biblioteca-universal-arion"))
TASKS_DIR = PROJECT / "sistema/tasks"

def task_hash(task_type: str, instruction: str) -> str:
    """Hash determinista per deduplicar tasques"""
    normalized = f"{task_type}:{instruction.strip().lower()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def task_dir(status: str) -> Path:
    d = TASKS_DIR / status
    d.mkdir(parents=True, exist_ok=True)
    return d

def find_by_hash(h: str, statuses=("pending", "running")) -> Path | None:
    """Busca tasca per hash en els estats donats"""
    for status in statuses:
        for f in task_dir(status).glob("*.json"):
            try:
                d = json.loads(f.read_text())
                if d.get("_hash") == h:
                    return f
            except: pass
    return None

def find_by_keyword(keyword: str, statuses=("pending", "running", "done")) -> Path | None:
    """Busca tasca per keyword al nom del fitxer o contingut"""
    for status in statuses:
        d = task_dir(status)
        if keyword.lower() in str(d).lower():
            continue
        for f in d.glob("*.json"):
            try:
                content = f.read_text().lower()
                if keyword.lower() in content:
                    return f
            except: pass
    return None

def add_task(task_type: str, instruction: str, priority: int = 5,
             model: str = None, depends_on: list = None, metadata: dict = None) -> Path | None:
    """Afegeix una tasca (deduplicada per hash)"""
    h = task_hash(task_type, instruction)
    
    # Ja existeix?
    existing = find_by_hash(h)
    if existing:
        return None  # Duplicada, no s'afegeix
    
    task_id = f"{task_type}-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "type": task_type,
        "instruction": instruction,
        "priority": priority,
        "retries": 0,
        "total_failures": 0,
        "regen_count": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "_hash": h,
    }
    if model: task["model"] = model
    if depends_on: task["depends_on"] = depends_on
    if metadata: task["metadata"] = metadata
    
    path = task_dir("pending") / f"{task_id}.json"
    path.write_text(json.dumps(task, indent=2, ensure_ascii=False))
    return path

def move_task(task_file: Path, new_status: str) -> Path:
    """Mou una tasca a un nou estat"""
    dest = task_dir(new_status) / task_file.name
    task_file.rename(dest)
    return dest

def retry_task(task_file: Path) -> bool:
    """Incrementa retry i mou a pending si no excedit"""
    d = json.loads(task_file.read_text())
    d["retries"] = d.get("retries", 0) + 1
    d["updated_at"] = datetime.utcnow().isoformat() + "Z"
    max_retries = d.get("max_retries", 3)
    if d["retries"] >= max_retries:
        move_task(task_file, "failed")
        return False
    task_file.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    move_task(task_file, "pending")
    return True

def recover_failed(max_total_failures: int = 9, max_regen: int = 3) -> int:
    """Recupera tasques fallides que encara poden reintentar-se"""
    recovered = 0
    for f in list(task_dir("failed").glob("*.json")):
        try:
            d = json.loads(f.read_text())
            total = d.get("total_failures", d.get("retries", 0))
            regen = d.get("regen_count", 0)
            if total >= max_total_failures or regen >= max_regen:
                move_task(f, "failed_permanent")
                continue
            d["retries"] = 0
            d["regen_count"] = regen + 1
            d["recovered"] = True
            d["updated_at"] = datetime.utcnow().isoformat() + "Z"
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False))
            move_task(f, "pending")
            recovered += 1
        except: pass
    return recovered

def stats() -> dict:
    """Estadístiques de tasques"""
    result = {}
    for status in ("pending", "running", "done", "failed", "failed_permanent"):
        result[status] = len(list(task_dir(status).glob("*.json")))
    return result

def next_task() -> Path | None:
    """Següent tasca per executar (prioritat més baixa = més urgent)"""
    tasks = []
    for f in task_dir("pending").glob("*.json"):
        try:
            d = json.loads(f.read_text())
            # Comprovar dependències
            deps = d.get("depends_on", [])
            if deps:
                all_done = all(
                    any(find_by_keyword(dep, ("done",)) for _ in [1])
                    for dep in deps
                )
                if not all_done:
                    continue
            tasks.append((d.get("priority", 5), f))
        except: pass
    if not tasks:
        return None
    tasks.sort(key=lambda x: x[0])
    return tasks[0][1]

# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ús: task_manager.py [add|next|stats|recover|move|retry] ...")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 4:
            print("Ús: task_manager.py add <type> <instruction> [priority]")
            sys.exit(1)
        t = sys.argv[2]
        inst = sys.argv[3]
        pri = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        result = add_task(t, inst, pri)
        if result:
            print(f"✅ Tasca afegida: {result.name}")
        else:
            print("⏭️ Duplicada, no s'afegeix")
    
    elif cmd == "next":
        t = next_task()
        print(t if t else "No hi ha tasques pendents")
    
    elif cmd == "stats":
        for k, v in stats().items():
            print(f"  {k}: {v}")
    
    elif cmd == "recover":
        n = recover_failed()
        print(f"♻️ {n} tasques recuperades")
    
    elif cmd == "move":
        if len(sys.argv) < 4:
            print("Ús: task_manager.py move <file> <status>")
            sys.exit(1)
        src = Path(sys.argv[2])
        status = sys.argv[3]
        dest = move_task(src, status)
        print(f"📦 Mogut a {status}: {dest.name}")
    
    elif cmd == "retry":
        if len(sys.argv) < 3:
            print("Ús: task_manager.py retry <file>")
            sys.exit(1)
        ok = retry_task(Path(sys.argv[2]))
        print("✅ Reintent" if ok else "❌ Màxim revents assolit")
    
    else:
        print(f"Comand desconegut: {cmd}")
