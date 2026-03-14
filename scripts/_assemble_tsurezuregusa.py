#!/usr/bin/env python3
"""Assembla la traducció completa del Tsurezuregusa a partir de chunks i grups."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path("obres/oriental/yoshida-kenko/tsurezuregusa")
NUM_GRUPS = 4


def _chunk_sort_key(name: str) -> int:
    """Extreu l'índex numèric d'un nom de chunk (ex: 'chunk_3' → 3)."""
    parts = name.split("_")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return 0


def carregar_chunks(base: Path) -> dict[str, str]:
    """Carrega els chunks traduïts des del JSON."""
    path = base / ".chunks_traduïts.json"
    if not path.exists():
        print(f"Error: no existeix {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def carregar_grups(base: Path) -> str:
    """Carrega els fitxers de grup (_group1.md .. _group4.md)."""
    text = ""
    for i in range(1, NUM_GRUPS + 1):
        path = base / f"_group{i}.md"
        if not path.exists():
            print(f"Avís: no existeix {path}, s'omet", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            text += f.read() + "\n\n"
    return text


def extreure_fragments(all_text: str) -> dict[int, str]:
    """Extreu fragments numerats del text combinat."""
    fragments: dict[int, str] = {}
    parts = re.split(r"(?=^## )", all_text, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^## (Primer fragment|Segon fragment|Fragment (\d+))", part)
        if m:
            if m.group(0) == "## Primer fragment":
                num = 1
            elif m.group(0) == "## Segon fragment":
                num = 2
            else:
                num = int(m.group(2))
            fragments[num] = part
    return fragments


def assemblar() -> None:
    """Punt d'entrada principal: assembla la traducció completa."""
    chunks = carregar_chunks(BASE)
    chunk_text = ""
    for k in sorted(chunks.keys(), key=_chunk_sort_key):
        chunk_text += chunks[k] + "\n\n"

    grup_text = carregar_grups(BASE)
    all_text = chunk_text + grup_text

    fragments = extreure_fragments(all_text)
    if not fragments:
        print("Error: no s'han trobat fragments al text", file=sys.stderr)
        sys.exit(1)

    sorted_nums = sorted(fragments.keys())
    print(f"Total fragments: {len(sorted_nums)}")
    print(f"Fragment numbers: {sorted_nums}")

    header = (
        "# Tsurezuregusa — Ociositats\n"
        "*Yoshida Kenkō (吉田兼好)*\n\n"
        "Traduït del japonès clàssic per Biblioteca Arion\n\n"
        "Selecció de 50 fragments dels 243 originals\n\n"
        "---\n\n"
    )
    body = "\n\n".join(fragments[n] for n in sorted_nums)
    footer = "\n\n---\n\n*Traducció de domini públic — CC BY-SA 4.0*\n"

    final = header + body + footer
    out_path = BASE / "traduccio.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final)

    print(f"\nEscrit a {out_path}: {len(final)} chars")


if __name__ == "__main__":
    assemblar()
