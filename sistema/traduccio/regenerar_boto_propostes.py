#!/usr/bin/env python3
"""
regenerar_boto_propostes.py - Regenera el botó de propostes al canal de Discord
S'executa després de cada proposta processada
Utilitza openclaw message tool per registrar correctament el modal
"""
import json
import os
import subprocess
import time
from pathlib import Path

import requests

CHANNEL_ID = "1479599316380291276"
LAST_MESSAGE_FILE = Path.home() / ".openclaw" / "workspace" / "propostes-button-message.txt"


def get_last_message_id() -> str | None:
    try:
        return LAST_MESSAGE_FILE.read_text().strip()
    except (OSError, ValueError):
        return None


def save_last_message_id(message_id: str) -> None:
    LAST_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_MESSAGE_FILE.write_text(str(message_id))

def regenerate_button() -> int:
    """Regenera el botó utilitzant openclaw CLI"""

    # Eliminar missatge antic si existeix
    old_id = get_last_message_id()
    if old_id:
        try:
            subprocess.run(
                ["openclaw", "message", "delete", "--channel", "discord",
                 "--channel-id", CHANNEL_ID, "--message-id", old_id],
                capture_output=True, timeout=10
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    components = {
        "blocks": [
            {"text": "# 📚 Biblioteca Universal Arion — Propostes de Traducció\n\nClica el botó per proposar una nova obra per traduir al català.", "type": "text"},
            {"accessory": {"button": {"label": "➕ Nova proposta", "style": "primary"}, "type": "button"}, "text": "📝 Envia la teva proposta", "type": "text"}
        ],
        "container": {"accentColor": "#5865F2"},
        "modal": {
            "fields": [
                {"label": "Títol de l'obra", "maxLength": 200, "minLength": 2, "name": "titol", "placeholder": "Ex: Faust, Hamlet, La Divina Comèdia...", "required": True, "type": "text"},
                {"label": "Idioma original", "maxLength": 50, "name": "idioma", "placeholder": "Ex: alemany, anglès, francès...", "required": False, "type": "text"}
            ],
            "title": "Nova proposta de traducció"
        },
        "reusable": True
    }

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "http://127.0.0.1:18789/message",
             "-H", f"Authorization: Bearer {os.environ.get('OPENCLAW_API_TOKEN', '')}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({
                 "action": "send",
                 "channel": "discord",
                 "channelId": CHANNEL_ID,
                 "components": components
             })],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            message_id = data.get("result", {}).get("messageId")
            if message_id:
                save_last_message_id(message_id)
                print(f"✅ Botó regenerat correctament: {message_id}")
                return 0
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        print(f"Error: {e}")

    # Fallback: crear manualment amb curl directe a Discord
    print("⚠️ Fallback: creant manualment...")
    return create_manual_button()

def create_manual_button() -> int:
    """Fallback: crea el botó directament via Discord API"""
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"

    ts = int(time.time())
    payload = {
        "flags": 32768,
        "components": [{
            "type": 17,
            "accent_color": 5793266,
            "components": [
                {"type": 10, "content": "# 📚 Biblioteca Universal Arion — Propostes de Traducció\n\nClica el botó per proposar una nova obra per traduir al català."},
                {"type": 10, "content": "📝 Envia la teva proposta"},
                {"type": 1, "components": [{"type": 2, "style": 1, "label": "➕ Nova proposta", "custom_id": f"occomp:cid=btn_p{ts};mid=mdl_p{ts}"}]}
            ]
        }]
    }

    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        msg_id = r.json().get("id")
        if msg_id:
            save_last_message_id(msg_id)
        print(f"✅ Botó creat manualment: {msg_id}")
        return 0
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(regenerate_button())