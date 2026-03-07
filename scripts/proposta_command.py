#!/usr/bin/env python3
"""
proposta_command.py - Processa comandes !proposta al canal de Discord
S'executa quan es detecta un missatge que comença amb !proposta
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

def crear_tasca(titol: str, idioma: str = "", usuari_id: str = "", canal_id: str = ""):
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
        "canal_discord_id": canal_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "source": "discord_command"
    }
    
    # Crear fitxer de tasca
    PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasca_file, "w") as f:
        json.dump(tasca, f, indent=2)
    
    # Afegir a la cua del worker
    try:
        data: list[dict] = []
        if TASK_QUEUE.exists():
            try:
                data = json.loads(TASK_QUEUE.read_text())
            except (json.JSONDecodeError, OSError):
                data = []
            if not isinstance(data, list):
                data = []
        data.append(tasca)
        TASK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        TASK_QUEUE.write_text(json.dumps(data, indent=2))
    except OSError as e:
        log(f"Error afegint a la cua: {e}")
    
    log(f"✅ Proposta creada: {titol} (usuari: {usuari_id})")
    return task_id

if __name__ == "__main__":
    # Format: !proposta Títol, idioma
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # Extreure títol i idioma
    text = text.replace("!proposta", "").strip()
    
    if not text:
        print(json.dumps({
            "success": False,
            "error": "Format: !proposta Títol, idioma",
            "example": "!proposta Faust, alemany"
        }))
        sys.exit(1)
    
    parts = text.split(",")
    titol = parts[0].strip()
    idioma = parts[1].strip() if len(parts) > 1 else ""
    
    # Crear tasca
    task_id = crear_tasca(titol, idioma)
    
    # Resposta
    print(json.dumps({
        "success": True,
        "task_id": task_id,
        "titol": titol,
        "idioma": idioma,
        "message": f"Nova proposta! 📚\n\nObra: **{titol}**\nIdioma: {idioma or 'desconegut'}\n\n✅ Tasca creada i assignada al worker."
    }))