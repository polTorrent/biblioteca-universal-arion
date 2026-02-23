#!/usr/bin/env python3
"""Traducció de De Brevitate Vitae de Sèneca."""

import os
import sys

os.environ["CLAUDECODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio
from scripts.post_traduccio import post_processar_traduccio, netejar_metadades_font
from scripts.utils import crear_metadata_yml

OBRA_PATH = "filosofia/seneca/de-brevitate-vitae"
TITOL = "De Brevitate Vitae"
AUTOR = "Sèneca"
LLENGUA_ORIGEN = "llatí"
GENERE = "filosofia"

CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 3000,
    "fer_avaluacio": True,
    "fer_refinament": True,
    "llindar_qualitat": 7.0,
    "max_iteracions_refinament": 2,
    "mostrar_dashboard": False,
    "dashboard_port": 5050,
}


def main():
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / OBRA_PATH
    original_path = obra_dir / "original.md"
    traduccio_path = obra_dir / "traduccio.md"

    crear_metadata_yml(obra_dir, TITOL, AUTOR, LLENGUA_ORIGEN, GENERE)

    if not original_path.exists():
        print(f"❌ Error: No existeix {original_path}")
        sys.exit(1)

    print("═" * 60)
    print(f"  TRADUCCIÓ: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} → català")
    print("═" * 60)
    print()

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    text_original = netejar_metadades_font(text_original)

    # Netejar capçalera
    import re
    match = re.search(r'\[1\]', text_original)
    if match:
        text_narratiu = text_original[match.start():]
    else:
        text_narratiu = text_original

    print(f"Text original: {len(text_narratiu)} caràcters")
    print()

    config = ConfiguracioPipelineV2(
        directori_obra=obra_dir,
        fer_analisi_previa=CONFIG["fer_analisi_previa"],
        crear_glossari=CONFIG["crear_glossari"],
        fer_chunking=CONFIG["fer_chunking"],
        max_chars_chunk=CONFIG["max_chars_chunk"],
        fer_avaluacio=CONFIG["fer_avaluacio"],
        fer_refinament=CONFIG["fer_refinament"],
        llindars=LlindarsAvaluacio(
            global_minim=CONFIG["llindar_qualitat"],
            max_iteracions=CONFIG["max_iteracions_refinament"],
        ),
        mostrar_dashboard=CONFIG["mostrar_dashboard"],
        dashboard_port=CONFIG["dashboard_port"],
    )

    pipeline = PipelineV2(config=config)

    print("Iniciant traducció amb Pipeline V2...")
    print()

    resultat = pipeline.traduir(
        text=text_narratiu,
        llengua_origen=LLENGUA_ORIGEN,
        autor=AUTOR,
        obra=TITOL,
        genere=GENERE,
    )

    traduccio_final = f"""# {TITOL}
*{AUTOR}*

Traduït del {LLENGUA_ORIGEN} per Biblioteca Arion

---

{resultat.traduccio_final}

---

*Traducció de domini públic.*
"""

    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(traduccio_final)

    print()
    print(resultat.resum())
    print()
    print(f"Traducció guardada a: {traduccio_path}")

    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    print()
    print("═" * 60)
    print("  ✅ TRADUCCIÓ COMPLETADA I PUBLICADA")
    print("═" * 60)

    return resultat


if __name__ == "__main__":
    main()
