#!/usr/bin/env python3
"""
proposta_slash_handler.py - Handler pel Slash Command /proposta
Respon amb un embed elegant quan s'usa el commando
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

PROJECT = Path.home() / "biblioteca-universal-arion"
PROPOSTES_DIR = PROJECT / "propostes"
TASK_QUEUE = PROJECT / "task-queue.json"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [PROPOSTA] {msg}")

def crear_tasca(titol: str, idioma: str = "", usuari_id: str = "", usuari_nom: str = ""):
    """Crea una tasca al worker."""
    timestamp = int(datetime.now().timestamp())
    task_id = f"{timestamp}_proposta_{os.getpid()}"
    
    tasca = {
        "id": task_id,
        "type": "translate",
        "description": f"Tradueix: {titol}",
        "titol": titol,
        "idioma_original": idioma or "desconegut",
        "usuari_discord_id": usuari_id,
        "usuari_discord_nom": usuari_nom,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "source": "slash_command"
    }
    
    # Crear fitxer de tasca
    PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasca_file, "w") as f:
        json.dump(tasca, f, indent=2)
    
    # Afegir a la cua del worker
    try:
        if TASK_QUEUE.exists():
            with open(TASK_QUEUE, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(tasca)
        with open(TASK_QUEUE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Error afegint a la cua: {e}")
    
    log(f"✅ Proposta creada: {titol} per {usuari_nom}")
    return task_id

def format_response(titol, idioma, task_id):
    """Formata la resposta com a embed elegant."""
    return {
        "embeds": [{
            "title": "📚 Nova Proposta de Traducció",
            "description": f"**{titol}**\nIdioma: {idioma or 'Desconegut'}",
            "color": 5793266,
            "fields": [
                {"name": "Estat", "value": "✅ Assignada al worker", "inline": True},
                {"name": "ID", "value": f"`{task_id}`", "inline": True}
            ],
            "footer": {"text": ".et notificarem quan estigui llesta!"},
            "timestamp": datetime.now().isoformat()
        }]
    }

if __name__ == "__main__":
    # Llegir arguments del slash command
    titol = sys.argv[1] if len(sys.argv) > 1 else ""
    idioma = sys.argv[2] if len(sys.argv) > 2 else ""
    usuari_id = sys.argv[3] if len(sys.argv) > 3 else ""
    usuari_nom = sys.argv[4] if len(sys.argv) > 4 else ""
    
    if not titol:
        print(json.dumps({
            "content": "❌ Has d'especificar un títol!\nÚs: `/proposta titol: Nom de l'obra idioma: idioma`"
        }))
        sys.exit(1)
    
    # Crear tasca
    task_id = crear_tasca(titol, idioma, usuari_id, usuari_nom)
    
    # Resposta elegant
    response = format_response(titol, idioma, task_id)
    print(json.dumps(response))