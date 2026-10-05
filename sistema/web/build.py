#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
BIBLIOTECA ARION - BUILD WEB
Genera la web a partir del contingut de `obres/` (Markdown + YAML).
════════════════════════════════════════════════════════════════════

Ús:
    python3 sistema/web/build.py            # Construir (incremental)
    python3 sistema/web/build.py --clean    # Netejar i reconstruir (recomanat)
    python3 sistema/web/build.py --watch    # Mode observació

La lògica viu al paquet `sistema/web/generador/`:
    markdown.py → MarkdownProcessor
    loader.py   → ContentLoader
    builder.py  → BuildSystem
"""

import argparse
import sys
from pathlib import Path

# Arrel del projecte: robusta tant si s'invoca com a `scripts/build.py`
# (enllaç simbòlic) com directament `sistema/web/build.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generador.builder import BuildSystem


def main():
    parser = argparse.ArgumentParser(description='Build Biblioteca Arion')
    parser.add_argument('--clean', action='store_true', help='Netejar abans de construir')
    parser.add_argument('--watch', action='store_true', help='Mode observació')
    args = parser.parse_args()

    builder = BuildSystem(PROJECT_ROOT)
    builder.build(clean=args.clean)

    if args.watch:
        print()
        print("Mode watch activat. Prem Ctrl+C per sortir.")
        try:
            import time
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            print()
            print("Aturat")


if __name__ == '__main__':
    main()
