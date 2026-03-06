#!/usr/bin/env python3
"""Compila les tres parts de la traducció del Tao Te King en un sol fitxer."""

from __future__ import annotations

import sys
from pathlib import Path

BASE: Path = Path(__file__).resolve().parent.parent / "obres" / "oriental" / "laozi" / "tao-te-king"

HEADER = """\
# Tao Te King
*Laozi (老子)*

Traduït del xinès clàssic per Biblioteca Arion

---

**Dao Jing (道經) — Llibre del Dao**[^11]

"""

FOOTER = """
---

*Traducció de domini públic.*
"""

PARTS: list[str] = [
    "tao_ch1_27.md",
    "tao_ch28_54.md",
    "tao_ch55_81.md",
]


def compilar() -> None:
    """Llegeix les tres parts i genera traduccio.md."""
    fitxers_absents: list[str] = [p for p in PARTS if not (BASE / p).exists()]
    if fitxers_absents:
        print(f"Error: falten fitxers a {BASE}:", file=sys.stderr)
        for nom in fitxers_absents:
            print(f"  - {nom}", file=sys.stderr)
        sys.exit(1)

    textos: list[str] = []
    for nom in PARTS:
        textos.append((BASE / nom).read_text(encoding="utf-8"))

    # Afegir capçalera del De Jing a la segona part (només el primer separador)
    marcador = "\n---\n"
    if marcador not in textos[1]:
        print("Avís: no s'ha trobat el separador '---' a la segona part; "
              "la capçalera del De Jing no s'inserirà.", file=sys.stderr)
    else:
        textos[1] = textos[1].replace(
            marcador,
            "\n---\n\n**De Jing (德經) — Llibre de la Virtut**[^12]\n",
            1,
        )

    sortida = BASE / "traduccio.md"
    sortida.write_text(
        HEADER + "\n".join(textos) + FOOTER,
        encoding="utf-8",
    )
    print(f"traduccio.md compilat correctament → {sortida}")


if __name__ == "__main__":
    compilar()
