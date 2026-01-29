#!/usr/bin/env python3
"""Script per traduir 'El Biombo de l'Infern' (地獄変) d'Akutagawa Ryūnosuke."""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Afegir el directori arrel al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio

def main():
    """Executa la traducció de Jigokuhen."""

    # Rutes
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / "narrativa" / "akutagawa" / "biombo-infern"
    original_path = obra_dir / "original.md"
    traduccio_path = obra_dir / "traduccio.md"

    # Llegir text original
    print("═" * 60)
    print("  TRADUCCIÓ: El Biombo de l'Infern (地獄変)")
    print("  Autor: Akutagawa Ryūnosuke")
    print("═" * 60)
    print()

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    # Extreure només el text narratiu (sense capçalera markdown)
    # Buscar des del primer capítol
    if "一\n" in text_original:
        idx = text_original.index("一\n")
        text_narratiu = text_original[idx:]
        # Treure el peu
        if "*Text de domini públic" in text_narratiu:
            text_narratiu = text_narratiu.split("*Text de domini públic")[0].strip()
    else:
        text_narratiu = text_original

    print(f"Text original: {len(text_narratiu)} caràcters")
    print()

    # Configurar pipeline
    config = ConfiguracioPipelineV2(
        fer_analisi_previa=True,
        crear_glossari=True,
        fer_chunking=True,
        max_chars_chunk=2500,  # Chunks més petits per millor qualitat
        fer_avaluacio=True,
        fer_refinament=True,
        llindars=LlindarsAvaluacio(
            global_minim=7.5,
            veu_autor_minim=7.0,
            max_iteracions=2,
        ),
        mostrar_dashboard=True,
        dashboard_port=5050,
    )

    # Crear i executar pipeline
    pipeline = PipelineV2(config=config)

    print("Iniciant traducció amb Pipeline V2...")
    print("(El dashboard s'obrirà al navegador)")
    print()

    resultat = pipeline.traduir(
        text=text_narratiu,
        llengua_origen="japonès",
        autor="Akutagawa Ryūnosuke",
        obra="El Biombo de l'Infern",
        genere="narrativa",
    )

    # Guardar traducció
    traduccio_final = f"""# El Biombo de l'Infern
*Akutagawa Ryūnosuke (1918)*

Traduït del japonès per Biblioteca Arion

---

{resultat.traduccio_final}

---

*Traducció de domini públic. Font original: Aozora Bunko (青空文庫).*
"""

    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(traduccio_final)

    # Mostrar resum
    print()
    print(resultat.resum())
    print()
    print(f"Traducció guardada a: {traduccio_path}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # POST-PROCESSAMENT AUTOMÀTIC
    # ═══════════════════════════════════════════════════════════════════════════════
    from scripts.post_traduccio import post_processar_traduccio

    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    return resultat

if __name__ == "__main__":
    main()
