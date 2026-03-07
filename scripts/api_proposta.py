#!/usr/bin/env python3
"""
API endpoint per rebre propostes del formulari web
Corre al dashboard_server.py
"""
import json
import os
from datetime import datetime
from pathlib import Path

PROJECT = Path.home() / "biblioteca-universal-arion"
PROPOSTES_DIR = PROJECT / "propostes"
TASK_QUEUE = PROJECT / "task-queue.json"

def handle_proposta(data):
    """Processa una proposta rebuda del formulari web"""
    titol = data.get('titol', '').strip()
    autor = data.get('autor', '').strip()
    idioma = data.get('idioma', 'desconegut')
    comentaris = data.get('comentaris', '').strip()
    
    if not titol:
        return {'error': 'Títol obligatori'}, 400
    
    # Crear tasca
    timestamp = int(datetime.now().timestamp())
    task_id = f"{timestamp}_proposta_web"
    
    tasca = {
        "id": task_id,
        "type": "translate",
        "description": f"Tradueix: {titol}" + (f" de {autor}" if autor else ""),
        "titol": titol,
        "autor": autor,
        "idioma_original": idioma,
        "comentaris": comentaris,
        "status": "pending",
        "source": "web_form",
        "created_at": datetime.now().isoformat()
    }
    
    # Guardar tasca
    PROPOSTES_DIR.mkdir(parents=True, exist_ok=True)
    tasca_file = PROPOSTES_DIR / f"{task_id}.json"
    with open(tasa_file, "w") as f:
        json.dump(tasca, f, indent=2)
    
    # Afegir a la cua
    if TASK_QUEUE.exists():
        with open(TASK_QUEUE, "r+") as f:
            try:
                data = json.load(f)
            except:
                data = []
            if not isinstance(data, list):
                data = []
            data.append(tasca)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
    else:
        with open(TASK_QUEUE, "w") as f:
            json.dump([tasca], f, indent=2)
    
    return {'success': True, 'task_id': task_id, 'titol': titol}, 200