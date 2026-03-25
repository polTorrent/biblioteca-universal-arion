#!/usr/bin/env python3
"""
informe_detallat.py - Genera informes detallats per a la Biblioteca Arion
Inclou: tasques actives, obres pendents, problemes, estimacions
"""
import json
from pathlib import Path
import re
from datetime import datetime
import subprocess

PROJECT = Path.home() / "biblioteca-universal-arion"
TASKS_DIR = Path.home() / ".openclaw" / "workspace" / "tasks"
OBRES_DIR = PROJECT / "obres"
QUEUE_FILE = PROJECT / "config" / "obra-queue.json"

def get_running_task() -> dict[str, str] | None:
    """Obté la tasca actualment en execució"""
    running_dir = TASKS_DIR / "running"
    if running_dir.exists():
        for f in running_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                return {
                    "id": data.get("id", "desconegut"),
                    "type": data.get("type", "desconegut"),
                    "instruction": data.get("instruction", "")[:100],
                    "started": data.get("started_at", "desconegut")
                }
            except Exception:
                pass
    return None

def get_pending_tasks(limit: int = 10) -> list[dict[str, str | int]]:
    """Obté les tasques pendents"""
    pending_dir = TASKS_DIR / "pending"
    tasks = []
    if pending_dir.exists():
        for f in sorted(pending_dir.glob("*.json"), key=lambda x: x.stat().st_mtime)[:limit]:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                tasks.append({
                    "type": data.get("type", "desconegut"),
                    "instruction": data.get("instruction", "")[:80],
                    "priority": data.get("priority", 0)
                })
            except Exception:
                pass
    return tasks

def get_obres_status() -> dict[str, list[dict[str, str | float | None]]]:
    """Obté l'estat de totes les obres"""
    obres = {
        "validades": [],
        "en_progres": [],
        "needs_fix": [],
        "pendents": [],
        "sense_original": []
    }
    
    if OBRES_DIR.exists():
        for categoria in OBRES_DIR.iterdir():
            if not categoria.is_dir():
                continue
            for autor in categoria.iterdir():
                if not autor.is_dir():
                    continue
                for obra in autor.iterdir():
                    if not obra.is_dir():
                        continue
                    
                    obra_name = obra.name
                    files = list(obra.iterdir())
                    filenames = [f.name for f in files]
                    
                    has_validated = ".validated" in filenames
                    has_needs_fix = ".needs_fix" in filenames
                    has_fixing = ".fixing" in filenames
                    has_original = "original.md" in filenames
                    has_traduccio = any("traduccio" in f.lower() for f in filenames)
                    has_metadata = "metadata.yml" in filenames or "metadata.json" in filenames
                    
                    # Llegir score si existeix
                    score = None
                    reason = None
                    needs_fix_file = obra / ".needs_fix"
                    if needs_fix_file.exists():
                        try:
                            content = needs_fix_file.read_text()
                            score_match = re.search(r'(\d+\.?\d*)/10', content)
                            if score_match:
                                score = float(score_match.group(1))
                            # Extreure primera línia com a raó
                            reason = content.split('\n')[0][:60]
                        except Exception:
                            pass
                    
                    obra_info = {
                        "name": obra_name,
                        "path": str(obra.relative_to(PROJECT)),
                        "score": score,
                        "reason": reason
                    }
                    
                    if has_validated:
                        obres["validades"].append(obra_info)
                    elif has_fixing:
                        obres["en_progres"].append({**obra_info, "status": "correcció"})
                    elif has_needs_fix:
                        obres["needs_fix"].append(obra_info)
                    elif has_traduccio:
                        obres["en_progres"].append({**obra_info, "status": "traducció"})
                    elif has_original:
                        obres["pendents"].append(obra_info)
                    else:
                        obres["sense_original"].append(obra_info)
    
    return obres

def get_estimation(obres: dict[str, list[dict]]) -> dict[str, float]:
    """Calcula estimacions de temps"""
    # Assumptes:
    # - Traducció nova: ~30 min per 1000 paraules
    # - Correcció: ~15 min per obra
    # - Validació: ~5 min per obra
    
    estimations = {
        "traduccions_pendents": len(obres["pendents"]) * 2,  # hores
        "correccions_pendents": len(obres["needs_fix"]) * 0.5,  # hores
        "validacions_pendents": len([o for o in obres["en_progres"] if o.get("status") == "traducció"]) * 0.25,  # hores
    }
    estimations["total_hores"] = sum(estimations.values())
    estimations["dies_laborables"] = estimations["total_hores"] / 6  # 6 hores/dia
    
    return estimations

def get_failed_tasks() -> list[dict[str, str | int]]:
    """Obté les tasques fallides"""
    failed_dir = TASKS_DIR / "failed"
    tasks = []
    if failed_dir.exists():
        for f in list(failed_dir.glob("*.json"))[:5]:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                tasks.append({
                    "type": data.get("type", "desconegut"),
                    "instruction": data.get("instruction", "")[:60],
                    "error": data.get("error", "desconegut")[:50],
                    "retries": data.get("retries", 0)
                })
            except Exception:
                pass
    return tasks

def get_worker_status() -> str:
    """Obté l'estat del worker"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude-worker"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return "✅ ACTIU"
        return "❌ INACTIU"
    except Exception:
        return "❓ DESCONEGUT"

def generate_report() -> str:
    """Genera l'informe complet"""
    now = datetime.now()
    
    # Obtenir dades
    running = get_running_task()
    pending = get_pending_tasks()
    obres = get_obres_status()
    failed = get_failed_tasks()
    estimations = get_estimation(obres)
    worker = get_worker_status()
    
    # Traduccions totals
    total_trad = len(obres["en_progres"]) + len(obres["validades"]) + len(obres["needs_fix"])
    
    # Tasques avui
    done_dir = TASKS_DIR / "done"
    done_today = 0
    if done_dir.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        for f in done_dir.glob("*.json"):
            if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today:
                done_today += 1
    
    report = f"""📚 **INFORME BIBLIOTECA ARION** — {now.strftime('%H:%M %d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ⚙️ ESTAT DEL WORKER
{worker} | {done_today} tasques avui | {len(pending)} pendents | {len(failed)} fallides

"""
    
    # Tasca actual
    if running:
        report += f"""## 🔄 TASCA ACTUAL
**Tipus:** {running['type']}
**Instrucció:** {running['instruction']}...

"""
    else:
        report += """## 🔄 TASCA ACTUAL
⚠️ Cap tasca en execució

"""
    
    # Obres pendents de correcció
    if obres["needs_fix"]:
        report += "## 🔧 OBRES PENDENTS DE CORRECCIÓ\n"
        report += "| Obra | Puntuació | Motiu |\n"
        report += "|------|-----------|-------|\n"
        for obra in obres["needs_fix"][:10]:
            score_str = f"{obra['score']:.1f}/10" if obra['score'] else "N/A"
            reason_str = obra['reason'] if obra['reason'] else "Qualitat insuficient"
            report += f"| {obra['name'][:30]} | {score_str} | {reason_str[:40]} |\n"
        report += "\n"
    
    # Obres en progrés
    if obres["en_progres"]:
        report += "## 📖 OBRES EN PROGRÉS\n"
        for obra in obres["en_progres"][:8]:
            status = obra.get('status', 'desconegut')
            emoji = "📝" if status == "traducció" else "🔧"
            report += f"{emoji} **{obra['name'][:35]}** ({status})\n"
        report += "\n"
    
    # Obres pendents
    if obres["pendents"]:
        report += f"## 📋 OBRES PENDENTS ({len(obres['pendents'])})\n"
        for obra in obres["pendents"][:5]:
            report += f"⏳ {obra['name'][:40]}\n"
        if len(obres["pendents"]) > 5:
            report += f"_...i {len(obres['pendents']) - 5} més_\n"
        report += "\n"
    
    # Estimacions
    report += f"""## ⏱️ ESTIMACIONS
| Categoria | Hores |
|-----------|-------|
| Traduccions pendents | {estimations['traduccions_pendents']:.1f}h |
| Correccions pendents | {estimations['correccions_pendents']:.1f}h |
| Validacions | {estimations['validacions_pendents']:.1f}h |
| **TOTAL** | **{estimations['total_hores']:.1f}h** ({estimations['dies_laborables']:.1f} dies) |

"""
    
    # Tasques fallides
    if failed:
        report += "## ❌ TASQUES FALLIDES\n"
        for task in failed[:3]:
            report += f"• **{task['type']}**: {task['instruction']}\n"
            report += f"  Error: {task['error']} ({task['retries']} reintents)\n"
        report += "\n"
    
    # Resum
    report += f"""## 📊 RESUM
| Mètrica | Valor |
|---------|-------|
| Total traduccions | {total_trad} |
| ✅ Validades | {len(obres['validades'])} |
| 🔧 Pendents correcció | {len(obres['needs_fix'])} |
| 📖 En progres | {len(obres['en_progres'])} |
| ⏳ Pendents traducció | {len(obres['pendents'])} |

"""
    
    # Problemes que necessiten supervisió
    report += "## ⚠️ PROBLEMES QUE NECESSITEN SUPERVISIÓ\n"
    problems = []
    
    if worker == "❌ INACTIU":
        problems.append("🔴 **Worker aturat** - Requerim reinici manual")
    
    if failed:
        problems.append(f"🟡 **{len(failed)} tasques fallides** - Requereixen revisió")
    
    if obres["needs_fix"]:
        low_score = [o for o in obres["needs_fix"] if o.get("score") and o["score"] < 5]
        if low_score:
            problems.append(f"🟡 **{len(low_score)} obres amb puntuació < 5** - Possiblement requerixen retraducció")
    
    if obres["sense_original"]:
        problems.append(f"🟡 **{len(obres['sense_original'])} obres sense original** - Requerixen fetch de font")
    
    if problems:
        report += "\n".join(problems) + "\n"
    else:
        report += "✅ Cap problema detectat\n"
    
    return report

if __name__ == "__main__":
    print(generate_report())