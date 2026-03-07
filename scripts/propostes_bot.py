#!/usr/bin/env python3
"""
propostes_bot.py - Bot dedicat per gestionar propostes de la Biblioteca Arion
Escolta el canal de propostes i processa automàticament
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
import time

# Configuració
ENV_FILE = Path.home() / "biblioteca-universal-arion" / ".env"
def load_token():
    """Carrega el token del fitxer .env"""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("DISCORD_BOT_TOKEN"):
                return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get("DISCORD_BOT_TOKEN", "")

TOKEN = load_token()
CHANNEL_ID = "1479599316380291276"
PROJECT = Path.home() / "biblioteca-universal-arion"
PROPOSTES_DIR = PROJECT / "propostes"
TASK_QUEUE = PROJECT / "task-queue.json"
LAST_MESSAGE_FILE = Path.home() / ".openclaw" / "workspace" / "propostes_bot_last.txt"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def get_last_message_id():
    try:
        return LAST_MESSAGE_FILE.read_text().strip()
    except:
        return "0"

def save_last_message_id(msg_id):
    LAST_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_MESSAGE_FILE.write_text(str(msg_id))

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
        "source": "discord_bot"
    }
    
    # Crear fitxer de tasca
    PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasca_file, "w") as f:
        json.dump(tasca, f, indent=2)
    
    # Afegir a la cua
    if TASK_QUEUE.exists():
        try:
            with open(TASK_QUEUE, "r+") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
                data.append(tasca)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except:
            with open(TASK_QUEUE, "w") as f:
                json.dump([tasca], f, indent=2)
    else:
        with open(TASK_QUEUE, "w") as f:
            json.dump([tasca], f, indent=2)
    
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
    
    for msg in reversed(messages):
        content = msg.get("content", "").strip()
        author = msg.get("author", {})
        author_id = author.get("id", "")
        author_name = author.get("username", "Desconegut")
        msg_id = msg.get("id", "0")
        
        # Ignorar missatges del bot
        if author_id == "1469345148138946752":
            save_last_message_id(msg_id)
            continue
        
        # Processar propostes
        if content.lower().startswith("proposta:"):
            # Extreure títol i idioma
            parts = content[9:].strip().split("—")
            if len(parts) == 1:
                parts = content[9:].strip().split(",")
            
            titol = parts[0].strip()
            idioma = parts[1].strip() if len(parts) > 1 else ""
            
            if titol:
                task_id = crear_tasca(titol, idioma, author_id, author_name)
                log(f"✅ Proposta: {titol} ({idioma}) per {author_name}")
                
                # Respondre
                response = f"✅ **Proposta rebuda!**\n\n📚 **Obra:** {titol}\n📝 **Idioma:** {idioma or 'desconegut'}\n\nLa tasca s'ha afegit a la cua del worker."
                send_response(CHANNEL_ID, msg_id, response)
        
        save_last_message_id(msg_id)

def main():
    log("🤖 Bot de propostes iniciat")
    log(f"📡 Escoltant canal: {CHANNEL_ID}")
    
    while True:
        try:
            check_messages()
        except Exception as e:
            log(f"Error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()