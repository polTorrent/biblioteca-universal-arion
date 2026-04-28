#!/usr/bin/env python3
"""
hermes_task_executor.py — Executor de tasques per Biblioteca Arion amb eines Hermes
Utilitza: terminal, file operations, git commands
"""

import json
import sys
import os
import subprocess
from pathlib import Path

PROJECT_DIR = Path.home() / "biblioteca-universal-arion"

def execute_task(task_file: str) -> dict:
    """Executa una tascautilitzant les eines disponibles."""
    
    with open(task_file) as f:
        task = json.load(f)
    
    task_id = task.get("id", "unknown")
    task_type = task.get("type", "unknown")
    obra_path = task.get("obra_path", "")
    instruction = task.get("instruction", "")
    
    print(f"[TASK] {task_id}")
    print(f"[TYPE] {task_type}")
    print(f"[OBRA] {obra_path}")
    
    # Canviar al directori del projecte
    os.chdir(PROJECT_DIR)
    
    result = {"success": False, "changes": 0, "message": ""}
    
    try:
        if task_type in ["fetch", "fix-fetch"]:
            result = execute_fetch_task(task)
        elif task_type in ["translate", "fix-translate"]:
            result = execute_translate_task(task)
        else:
            result = execute_generic_task(task)
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        return result
    
    return result

def execute_fetch_task(task: dict) -> dict:
    """Executa tasca de tipus fetch - buscar i descarregar originals."""
    obra_path = task.get("obra_path", "")
    
    # Extreu autor i obra del path
    parts = obra_path.split("/")
    if len(parts) >= 3:
        # obres/categoria/autor/obra
        if parts[0] == "obres" and parts[1] == "*":
            # Buscar el directori real
            for cat in ["filosofia", "narrativa", "poesia", "teatre", "oriental"]:
                test_path = PROJECT_DIR / "obres" / cat / parts[2] / parts[3]
                if test_path.exists():
                    obra_path = str(test_path)
                    break
        elif len(parts) >= 4:
            obra_path = str(PROJECT_DIR / "/".join(parts[:4]))
    
    obra_dir = Path(obra_path)
    original_file = obra_dir / "original.md"
    
    print(f"[FETCH] Buscant original per: {obra_dir}")
    
    # Verificar si ja existeix
    if original_file.exists() and original_file.stat().st_size > 100:
        print(f"[FETCH] Original ja existeix ({original_file.stat().st_size} bytes)")
        return {"success": True, "changes": 0, "message": "Original ja existeix"}
    
    # Crear directori si no existeix
    obra_dir.mkdir(parents=True, exist_ok=True)
    
    # Intentar descarregar amb cercador_fonts_v2.py
    cercador_script = PROJECT_DIR / "sistema/traduccio/cercador_fonts_v2.py"
    
    if cercador_script.exists():
        print(f"[FETCH] Executant cercador de fonts...")
        result = subprocess.run(
            ["python3", str(cercador_script), "--obra", obra_dir.name],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"[FETCH] Cerca completada")
            if original_file.exists():
                return {"success": True, "changes": 1, "message": "Original descarregat"}
        else:
            print(f"[FETCH] Error cercador: {result.stderr[:200]}")
    
    # Si no troba el script o falla, crear placeholder
    placeholder = f"# Original pendiente\n\nFont original no trobada.\nCal buscar manualment.\n"
    original_file.write_text(placeholder)
    
    return {"success": False, "changes": 0, "message": "No s'ha pogut descarregar l'original"}

def execute_translate_task(task: dict) -> dict:
    """Executa tasca de tipus translate - traduir o corregir traduccions."""
    obra_path = task.get("obra_path", "")
    task_type = task.get("type", "fix-translate")
    
    # Extreupath real
    parts = obra_path.split("/")
    if len(parts) >= 3 and parts[1] == "*":
        for cat in ["filosofia", "narrativa", "poesia", "teatre", "oriental"]:
            test_path = PROJECT_DIR / "obres" / cat / parts[2] / parts[3]
            if test_path.exists():
                obra_path = str(test_path)
                break
    elif len(parts) >= 4:
        obra_path = str(PROJECT_DIR / "/".join(parts[:4]))
    
    obra_dir = Path(obra_path)
    original_file = obra_dir / "original.md"
    traduccio_file = obra_dir / "traduccio.md"
    
    print(f"[TRANSLATE] Processant: {obra_dir}")
    
    # Verificar que existeix l'original
    if not original_file.exists():
        print(f"[TRANSLATE] Error: No existeix original.md")
        return {"success": False, "changes": 0, "message": "Falta original.md"}
    
    # Verificar traducció existent
    if traduccio_file.exists():
        current_size = traduccio_file.stat().st_size
        print(f"[TRANSLATE] Traducció existent: {current_size} bytes")
        
        # Verificar si és placeholder
        content = traduccio_file.read_text()[:500]
        if "placeholder" in content.lower() or "pendiente" in content.lower():
            print(f"[TRANSLATE] Traducció és placeholder, necessita revisió")
    else:
        print(f"[TRANSLATE] No existeix traducció")
    
    # Executar pipeline de traducció si existeix
    pipeline_script = PROJECT_DIR / "sistema/traduccio/traduir_pipeline.py"
    
    if pipeline_script.exists():
        print(f"[TRANSLATE] Executant pipeline...")
        # Extreure autor i obra del path
        autor = obra_dir.parent.name
        obra = obra_dir.name
        
        result = subprocess.run(
            ["python3", str(pipeline_script), "--autor", autor, "--obra", obra],
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode == 0:
            print(f"[TRANSLATE] Pipeline completat")
            return {"success": True, "changes": 1, "message": "Traducció processada"}
        else:
            print(f"[TRANSLATE] Error pipeline: {result.stderr[:200]}")
    
    return {"success": False, "changes": 0, "message": "Pipeline no disponible"}

def execute_generic_task(task: dict) -> dict:
    """Executa tasca genèrica."""
    instruction = task.get("instruction", "")
    print(f"[GENERIC] Instrucció: {instruction[:100]}...")
    
    # Per a tasques genèriques, retornem que necessiten intervenció manual
    return {"success": False, "changes": 0, "message": "Tasca genèrica requereix intervenció"}

def main():
    if len(sys.argv) < 2:
        print("Ús: hermes_task_executor.py <task_file.json>")
        sys.exit(1)
    
    task_file = sys.argv[1]
    
    if not os.path.exists(task_file):
        print(f"Error: No existeix {task_file}")
        sys.exit(1)
    
    result = execute_task(task_file)
    
    print(f"\n[RESULT] Success: {result['success']}")
    print(f"[RESULT] Changes: {result['changes']}")
    print(f"[RESULT] Message: {result['message']}")
    
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()