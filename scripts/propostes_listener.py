#!/usr/bin/env python3
"""
propostes_listener.py - Escolta el canal de propostes i processa les propostes automàticament
S'executa en background i processa missatges amb format "Proposta: Títol, idioma"
"""
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path

# Configuració
TOKEN = "MTQ2OTM0NTE0ODEzODk0Njc1Mg.GfH2xn.CHohbG2Mtdsc6iWwj-nAqA_svGT8MwKG5WF-RE"
CHANNEL_ID = "1479599316380291276"
LAST_MESSAGE_FILE = Path.home() / ".openclaw" / "workspace" / "propostes_last_message.txt"
PROPOSTES_DIR = Path.home() / "biblioteca-universal-arion" / "propostes"
TASK_QUEUE = Path.home() / "biblioteca-universal-arion" / "task-queue.json"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def get_last_message_id():
    try:
        return open(LAST_MESSAGE_FILE).read().strip()
    except:
        return "0"

def save_last_message_id(msg_id):
    LAST_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_MESSAGE_FILE, "w") as f:
        f.write(str(msg_id))

def crear_tasca(titol, idioma, usuari_id, usuari_nom):
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
        "source": "discord_channel"
    }
    
    # Crear fitxer de tasca
    PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasca_file, "w") as f:
        json.dump(tasca, f, indent=2)
    
    # Afegir a la cua
    if TASK_QUEUE.exists():
        with open(TASK_QUEUE, "r+") as f:
            data = json.load(f) if f.read(1) else []
            f.seek(0)
            if not isinstance(data, list):
                data = []
            data.append(tasca)
            json.dump(data, f, indent=2)
    
    return task_id

def send_response(channel_id, message_id, content):
    """Envia resposta al canal."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    data = {
        "content": content,
        "message_reference": {"message_id": message_id}
    }
    requests.post(url, headers=headers, json=data)

def check_messages():
    """Comprova nous missatges al canal."""
    last_id = get_last_message_id()
    
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?after={last_id}&limit=10"
    headers = {"Authorization": f"Bot {TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return
    
    messages = response.json()
    
    for msg in reversed(messages):  # Processar en ordre cronològic
        content = msg.get("content", "")
        author = msg.get("author", {})
        author_id = author.get("id", "")
        author_name = author.get("username", "Desconegut")
        msg_id = msg.get("id", "0")
        
        # Evitar processar missatges del bot
        if author_id == "1469345148138946752":
            continue
        
        # Comprovar si és una proposta
        if "proposta" in content.lower() or "— " in content:
            # Extreure títol i idioma
            content = content.replace("Proposta:", "").replace("proposta:", "").strip()
            
            if "—" in content:
                parts = content.split("—")
            elif "," in content:
                parts = content.split(",")
            else:
                parts = [content, ""]
            
            titol = parts[0].strip()
            idioma = parts[1].strip() if len(parts) > 1 else ""
            
            if titol:
                task_id = crear_tasca(titol, idioma, author_id, author_name)
                log(f"✅ Proposta: {titol} ({idioma}) per {author_name}")
                
                # Respondre
                send_response(CHANNEL_ID, msg_id, 
                    f"✅ Proposta rebuda!\n\n📚 **Obra:** {titol}\n📝 **Idioma:** {idioma or 'desconegut'}\n\nLa tasca s'ha afegit a la cua del worker.")
        
        save_last_message_id(msg_id)

def main():
    log("🎧 Escoltant propostes al canal...")
    while True:
        try:
            check_messages()
        except Exception as e:
            log(f"Error: {e}")
        time.sleep(5)  # Comprovar cada 5 segons

if __name__ == "__main__":
    main()