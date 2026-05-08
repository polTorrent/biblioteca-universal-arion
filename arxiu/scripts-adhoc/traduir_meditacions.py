#!/usr/bin/env python3
"""Traducció de 'Meditacions' (Τὰ εἰς ἑαυτόν) de Marc Aureli del grec antic al català."""

import os
import re
import sys

# Afegir el directori arrel al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Netejar CLAUDECODE per evitar errors de "nested sessions" si s'executa com a subprocess
os.environ.pop("CLAUDECODE", None)

from pathlib import Path

from agents.v2 import ConfiguracioPipelineV2, PipelineV2
from agents.v2.models import LlindarsAvaluacio
from scripts.post_traduccio import netejar_metadades_font, post_processar_traduccio
from scripts.utils import crear_metadata_yml

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ
# ═══════════════════════════════════════════════════════════════════════════════

OBRA_PATH = "filosofia/marc-aureli/meditacions"

TITOL = "Meditacions"
AUTOR = "Marc Aureli"
LLENGUA_ORIGEN = "grec antic"
GENERE = "filosofia"

CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 2500,
    "fer_avaluacio": True,
    "fer_refinament": True,
    "llindar_qualitat": 7.5,
    "max_iteracions_refinament": 2,
    "mostrar_dashboard": True,
    "dashboard_port": 5050,
}

# ═══════════════════════════════════════════════════════════════════════════════
# NO MODIFICAR A PARTIR D'AQUÍ
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """Executa la traducció de Meditacions de Marc Aureli."""

    # Rutes
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / OBRA_PATH
    original_path = obra_dir / "original.md"
    traduccio_path = obra_dir / "traduccio.md"

    # Crear/verificar metadata.yml amb format correcte
    crear_metadata_yml(obra_dir, TITOL, AUTOR, LLENGUA_ORIGEN, GENERE)

    # Verificar que existeix l'original
    if not original_path.exists():
        print(f"Error: No existeix {original_path}")
        print(f"   Crea primer el fitxer original.md a {obra_dir}")
        sys.exit(1)

    # Llegir text original
    print("=" * 60)
    print(f"  TRADUCCIÓ: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} -> català")
    print("=" * 60)
    print()

    text_original = original_path.read_text(encoding="utf-8")

    # Netejar metadades de fonts digitals
    text_original = netejar_metadades_font(text_original)

    # Detectar inici del contingut (primer capítol)
    text_narratiu = text_original
    match = re.search(r'^(##\s+)', text_original, re.MULTILINE)
    if match:
        text_narratiu = text_original[match.start():]

    # Treure peu de pàgina si existeix
    for footer in ['*Text de domini públic', '*Traducció de domini públic', '---\n\n*']:
        if footer in text_narratiu:
            text_narratiu = text_narratiu.split(footer)[0].strip()

    if not text_narratiu.strip():
        print("Error: El text original està buit després de netejar-lo")
        sys.exit(1)

    print(f"Text original: {len(text_narratiu)} caràcters")
    print()

    # Configurar pipeline
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

    # Crear i executar pipeline
    pipeline = PipelineV2(config=config)

    print("Iniciant traducció amb Pipeline V2...")
    if CONFIG["mostrar_dashboard"]:
        print(f"(Dashboard a http://localhost:{CONFIG['dashboard_port']})")
    print()

    try:
        resultat = pipeline.traduir(
            text=text_narratiu,
            llengua_origen=LLENGUA_ORIGEN,
            autor=AUTOR,
            obra=TITOL,
            genere=GENERE,
        )
    except Exception as e:
        print(f"Error durant la traducció: {e}")
        sys.exit(1)

    if not resultat.traduccio_final:
        print("Error: El pipeline no ha generat cap traducció")
        sys.exit(1)

    # Guardar traducció
    traduccio_final = (
        f"# {TITOL}\n"
        f"*{AUTOR}*\n\n"
        f"Traduït del {LLENGUA_ORIGEN} per Biblioteca Arion\n\n"
        f"---\n\n"
        f"{resultat.traduccio_final}\n\n"
        f"---\n\n"
        f"*Traducció de domini públic.*\n"
    )

    traduccio_path.write_text(traduccio_final, encoding="utf-8")

    # Mostrar resum
    print()
    print(resultat.resum())
    print()
    print(f"Traducció guardada a: {traduccio_path}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # POST-PROCESSAMENT AUTOMÀTIC
    # ═══════════════════════════════════════════════════════════════════════════════
    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    print()
    print("=" * 60)
    print("  TRADUCCIÓ COMPLETADA I PUBLICADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
