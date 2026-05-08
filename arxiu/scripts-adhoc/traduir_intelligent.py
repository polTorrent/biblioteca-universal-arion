#!/usr/bin/env python3
"""
Wrapper per integrar Model Selector amb el pipeline de traducció
Utilitza el model òptim segons pressupost i tasca
"""

import os
import sys
from pathlib import Path

# Afegir directoris al path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "sistema" / "config"))

from model_selector import select_model_for_task, can_proceed_with_task, get_budget_report

def main():
    if len(sys.argv) < 2:
        print("Ús: python3 traduir_intelligent.py <obra_dir> [task_type]")
        print("\nTask types available:")
        for task in ["translate_filosofia", "translate_narrativa", "translate_poesia", 
                    "translate_oriental", "supervision_basic", "supervision_final"]:
            print(f"  - {task}")
        print("\nExemple:")
        print("  python3 traduir_intelligent.py obres/filosofia/seneca/de-brevitate-vitae/ translate_filosofia")
        sys.exit(1)
    
    obra_dir = sys.argv[1]
    task_type = sys.argv[2] if len(sys.argv) > 2 else "translate_filosofia"
    
    # Mostrar estat del pressupost
    print(get_budget_report())
    
    # Seleccionar model òptim
    model = select_model_for_task(task_type)
    can_afford, model, estimated_cost = can_proceed_with_task(task_type)
    
    print(f"\n📊 Tasca: {task_type}")
    print(f"🎯 Model seleccionat: {model}")
    print(f"💰 Cost estimat: {estimated_cost:.2f} DIEM")
    
    if not can_afford:
        print("\n❌ ERROR: No hi ha saldo suficient per a aquesta tasca")
        print("💡 Considera utilitzar un model més econòmic o esperar al proper reset")
        sys.exit(1)
    
    # Confirmar continuació
    response = input(f"\nContinuar amb {model}? (y/n): ")
    if response.lower() != 'y':
        print("❌ Operació cancel·lada")
        sys.exit(0)
    
    # Construir comanda amb el model seleccionat
    import subprocess
    
    # Exportar model com a variable d'entorn per al pipeline
    env = os.environ.copy()
    env["VENICE_MODEL"] = model
    env["CLAUDECODE"] = ""  # Desactivar Claude Code per usar Venice
    
    cmd = [
        "python3",
        str(_project_root / "sistema" / "traduccio" / "traduir_pipeline.py"),
        obra_dir
    ]
    
    print(f"\n🚀 Executant traducció amb {model}...")
    print(f"Comanda: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=False, text=True)
        if result.returncode == 0:
            print("\n✅ Traducció completada amb èxit")
        else:
            print(f"\n❌ Error en la traducció: {result.stderr}")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error executant traducció: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()