#!/usr/bin/env python3
"""Script per publicar la Biblioteca Arion a la web.

Ús:
    python scripts/publicar_web.py                    # Publicar tot sense portades
    python scripts/publicar_web.py --portades        # Amb portades (requereix VENICE_API_KEY)
    python scripts/publicar_web.py --obra epictetus-enchiridion  # Una obra específica
"""

import argparse
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Afegir el directori arrel al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.web_publisher import WebPublisher, WebPublisherConfig


def main():
    parser = argparse.ArgumentParser(
        description="Publicar la Biblioteca Arion a GitHub Pages"
    )
    parser.add_argument(
        "--portades",
        action="store_true",
        help="Generar portades amb Venice.ai",
    )
    parser.add_argument(
        "--obra",
        type=str,
        help="Publicar només una obra específica (slug: autor-obra)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs",
        help="Directori de sortida (per defecte: docs)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BIBLIOTECA ARION - PUBLICACIÓ WEB")
    print("=" * 60)
    print()

    # Configuració
    config = WebPublisherConfig(
        output_dir=Path(args.output),
        generar_portades=args.portades,
    )

    publisher = WebPublisher(publisher_config=config)

    # Filtrar obres si cal
    obres_filtrades = [args.obra] if args.obra else None

    # Publicar
    result = publisher.publicar_tot(
        generar_portades=args.portades,
        obres_filtrades=obres_filtrades,
    )

    # Resum
    print()
    print("=" * 60)
    print("RESULTAT")
    print("=" * 60)
    print(f"Obres publicades: {result['obres_publicades']}")
    print(f"Directori: {result['output_dir']}")

    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    if result['obres']:
        print("\nObres publicades:")
        for obra in result['obres']:
            print(f"  - {obra}.html")

    print()
    print("Per veure la web localment:")
    print(f"  cd {result['output_dir']} && python3 -m http.server 8000")
    print("  Obre http://localhost:8000")

    return 0 if not result['errors'] else 1


if __name__ == "__main__":
    sys.exit(main())
