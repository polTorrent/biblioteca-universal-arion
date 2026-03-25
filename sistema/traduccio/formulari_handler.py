#!/usr/bin/env python3
# =============================================================================
# formulari_handler.py - Handler per processar formularis de Discord
# =============================================================================
# Es crida quan es rep una interacció de formulari via OpenClaw
# Crea la tasca al worker i notifica l'usuari
# =============================================================================

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

PROJECT = Path.home() / "biblioteca-universal-arion"
PROPOSTES_DIR = PROJECT / "propostes"
PROPOSTES_PROCESSADES = Path.home() / ".openclaw" / "workspace" / "propostes-processades.txt"
TASK_QUEUE = PROJECT / "task-queue.json"

# Crear directoris
PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
PROPOSTES_PROCESSADES.parent.mkdir(parents=True, exist_ok=True)
PROPOSTES_PROCESSADES.touch(exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [FORMULARI] {msg}")

def crear_tasca(titol: str, idioma: str = "", usuari_id: str = "", canal_id: str = ""):
    """Crea una tasca al worker i la guarda per seguiment."""
    timestamp = int(datetime.now().timestamp())
    task_id = f"{timestamp}_proposta_{os.getpid()}"
    
    tasca = {
        "id": task_id,
        "type": "proposta",
        "description": f"Tradueix: {titol}",
        "titol": titol,
        "idioma_original": idioma or "desconegut",
        "usuari_discord_id": usuari_id,
        "canal_discord_id": canal_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "source": "discord_form"
    }
    
    # Crear fitxer de tasca
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasca_file, "w", encoding="utf-8") as f:
        json.dump(tasca, f, indent=2, ensure_ascii=False)
    
    # Afegir a la cua del worker
    try:
        if TASK_QUEUE.exists():
            with open(TASK_QUEUE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(tasca)
        with open(TASK_QUEUE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        log(f"Error afegint a la cua: {e}")
    
    # Guardar com a processada
    with open(PROPOSTES_PROCESSADES, "a") as f:
        f.write(f"{task_id}|{titol}|{usuari_id}|{canal_id}|{datetime.now().isoformat()}\n")
    
    log(f"✅ Proposta creada: {titol} (usuari: {usuari_id})")
    
    # Regenerar el botó de propostes
    try:
        subprocess.run(["python3", str(PROJECT / "scripts" / "regenerar_boto_propostes.py")],
                      capture_output=True, timeout=10)
        log("🔄 Botó de propostes regenerat")
    except Exception as e:
        log(f"⚠️ Error regenerant botó: {e}")
    
    return task_id

def main():
    """Processa una interacció de formulari."""
    if len(sys.argv) < 2:
        # Llegir de stdin si no hi ha arguments
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            log("Error: No s'han rebut dades")
            sys.exit(1)
    else:
        # Llegir del primer argument
        try:
            data = json.loads(sys.argv[1])
        except (json.JSONDecodeError, ValueError):
            log("Error: Dades JSON invàlides")
            sys.exit(1)
    
    # Extreure dades del formulari
    # Format esperat (de Discord modal):
    # {
    #   "titol": "Títol de l'obra",
    #   "idioma": "Idioma original",
    #   "user_id": "ID de l'usuari deDiscord",
    #   "channel_id": "ID del canal"
    # }
    
    titol = data.get("titol", data.get("title", ""))
    idioma = data.get("idioma", data.get("language", ""))
    usuari_id = data.get("user_id", data.get("usuari_id", ""))
    canal_id = data.get("channel_id", data.get("canal_id", ""))
    
    if not titol:
        log("Error: Falta el títol")
        sys.exit(1)
    
    task_id = crear_tasca(titol, idioma, usuari_id, canal_id)
    
    # Retornar resposta
    resposta = {
        "success": True,
        "task_id": task_id,
        "titol": titol,
        "message": f"Proposta rebuda! Crearem la traducció de '{titol}'. Et notificarem quan estigui disponible."
    }
    print(json.dumps(resposta))

if __name__ == "__main__":
    main()