#!/usr/bin/env python3
"""Traducció de l'Apologia de Sòcrates de Plató.

Text clàssic fonamental de la filosofia occidental.
Com que conté referències a la mort i l'execució (context històric),
usem chunks més petits per evitar problemes de filtratge de contingut.
"""

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

from agents.v2 import ConfiguracioPipelineV2, PipelineV2, ResultatPipelineV2
from agents.v2.models import LlindarsAvaluacio
from scripts.post_traduccio import post_processar_traduccio

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ - APOLOGIA DE SÒCRATES
# ═══════════════════════════════════════════════════════════════════════════════

# Ruta a l'obra
OBRA_PATH = "filosofia/plato/apologia"

# Metadades de l'obra
TITOL = "Apologia de Sòcrates"
AUTOR = "Plató"
LLENGUA_ORIGEN = "anglès"  # Traducció de Jowett (domini públic)
GENERE = "filosofia"

# Configuració del pipeline - CHUNKS PETITS per evitar filtratge
# L'Apologia conté referències a mort, execució, etc. (context històric)
# que poden activar filtres de contingut. Chunks petits = menys risc.
CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 1500,  # Chunks petits per evitar filtratge
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


def main() -> ResultatPipelineV2:
    """Executa la traducció."""

    # Rutes
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / OBRA_PATH
    original_path = obra_dir / "original.md"
    traduccio_path = obra_dir / "traduccio.md"

    # Verificar que existeix l'original
    if not original_path.exists():
        print(f"Error: No existeix {original_path}")
        print(f"   Crea primer el fitxer original.md a {obra_dir}")
        sys.exit(1)

    # Llegir text original
    print("=" * 60)
    print(f"  TRADUCCIO: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} -> catala")
    print("=" * 60)
    print()
    print("NOTA: Usant chunks petits (1500 chars) per evitar filtratge")
    print("      de contingut en textos amb referencies historiques.")
    print()

    text_original = original_path.read_text(encoding="utf-8")

    # Netejar capçalera si existeix (buscar primer paràgraf del text)
    text_narratiu = text_original

    # Buscar inici del contingut real (després de "---")
    if "---" in text_original:
        parts = text_original.split("---")
        if len(parts) >= 3:
            # Frontmatter YAML: parts[0]=buit, parts[1]=YAML, parts[2:]=contingut
            text_narratiu = "---".join(parts[2:]).strip()
            # Treure peu de pàgina si existeix
            if "*Text de domini públic" in text_narratiu:
                text_narratiu = text_narratiu.split("*Text de domini públic")[0].strip()
            if text_narratiu.endswith("---"):
                text_narratiu = text_narratiu[:-3].strip()

    print(f"Text original: {len(text_narratiu)} caràcters")
    print()

    # Configurar pipeline
    config = ConfiguracioPipelineV2(
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

    print("Iniciant traduccio amb Pipeline V2...")
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
    except Exception as exc:
        print(f"Error durant la traduccio: {exc}")
        sys.exit(1)

    if not resultat.traduccio_final.strip():
        print("Error: el pipeline ha retornat una traduccio buida")
        sys.exit(1)

    # Guardar traduccio
    traduccio_final = (
        f"# {TITOL}\n"
        f"*{AUTOR}*\n\n"
        f"Traduit de l'{LLENGUA_ORIGEN} per Biblioteca Arion\n\n"
        f"---\n\n"
        f"{resultat.traduccio_final}\n\n"
        f"---\n\n"
        f"*Traduccio de domini public.*\n"
    )

    traduccio_path.write_text(traduccio_final, encoding="utf-8")

    # Mostrar resum
    print()
    print(resultat.resum())
    print()
    print(f"Traduccio guardada a: {traduccio_path}")

    # Post-processament automatic
    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    print()
    print("=" * 60)
    print("  TRADUCCIO COMPLETADA I PUBLICADA")
    print("=" * 60)

    return resultat


if __name__ == "__main__":
    main()
