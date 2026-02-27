#!/usr/bin/env python3
"""Genera notes crítiques per 'La Sala número 6' de Txèkhov."""

import os
import sys

# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
os.environ["CLAUDECODE"] = "1"

# Afegir path del projecte
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import traceback
from pathlib import Path
from agents.anotador_critic import AnotadorCriticAgent, AnotacioRequest

# Directori arrel del projecte (relatiu a la ubicació d'aquest script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main() -> int:
    """Genera notes per la traducció de Txèkhov."""

    obra_dir = PROJECT_ROOT / "obres/narrativa/txekhov/sala-numero-6"
    traduccio_path = obra_dir / "traduccio.md"
    notes_path = obra_dir / "notes.md"

    if not traduccio_path.exists():
        print(f"❌ No es troba la traducció: {traduccio_path}")
        return 1

    print(f"📖 Llegint traducció: {traduccio_path}")
    text = traduccio_path.read_text(encoding="utf-8")
    print(f"   Text: {len(text)} caràcters")

    # Crear agent d'anotació
    agent = AnotadorCriticAgent()

    # Crear request d'anotació
    request = AnotacioRequest(
        text=text,
        llengua_origen="rus",
        genere="narrativa",
        context_historic="Relat publicat el 1892, durant el període de maduresa de Txèkhov. "
                        "Reflecteix la crítica social i l'absurditat de la vida a la Rússia tsarista. "
                        "L'hospital psiquiàtric és una metàfora de la societat russa.",
        densitat_notes="normal"
    )

    print("\n🔍 Generant notes crítiques...")
    print("   (Això pot trigar uns minuts amb chunking automàtic)")

    try:
        response = agent.annotate(request)

        # Parsejar resposta
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            # Si no és JSON, usar directament
            data = {"notes": response.content}

        # Generar fitxer notes.md
        notes_content = "# Notes crítiques\n\n"
        notes_content += "*La Sala número 6* d'Anton Txèkhov\n\n"
        notes_content += "---\n\n"

        if isinstance(data, dict) and "notes" in data:
            notes = data["notes"]
            if isinstance(notes, list):
                for i, nota in enumerate(notes, 1):
                    if isinstance(nota, dict):
                        # L'agent retorna: numero, tipus, text_referit, nota
                        tipus = nota.get("tipus", "G")
                        text_referit = nota.get("text_referit", "")
                        contingut = nota.get("nota", nota.get("contingut", nota.get("explicacio", "")))

                        # Usar text_referit com a títol si no hi ha títol explícit
                        titol = nota.get(
                            "titol",
                            (text_referit[:50] + "...") if len(text_referit) > 50 else text_referit,
                        )

                        notes_content += f"## [{i}] [{tipus}] {titol}\n\n"
                        if text_referit and text_referit != titol:
                            notes_content += f"> «{text_referit}»\n\n"
                        notes_content += f"{contingut}\n\n"
                    else:
                        notes_content += f"## [{i}] Nota\n\n{nota}\n\n"
            else:
                notes_content += str(notes)
        else:
            notes_content += str(data)

        # Guardar notes
        notes_path.write_text(notes_content, encoding="utf-8")
        print(f"\n✅ Notes generades: {notes_path}")
        print(f"   {len(notes_content)} caràcters")

        return 0

    except Exception as e:
        print(f"\n❌ Error generant notes: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
