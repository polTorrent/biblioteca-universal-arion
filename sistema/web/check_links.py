#!/usr/bin/env python3
"""Comprova enllaços interns dels fitxers HTML generats a docs/.

Detecta href/src que apunten a fitxers locals de docs/ que no existeixen.
Ús: python3 sistema/web/check_links.py [directori]
"""
import re
import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parents[2]
DOCS = Path(sys.argv[1]) if len(sys.argv) > 1 else ARREL / "docs"

ATRIBUT = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')

# Prefixos que no són fitxers locals
EXTERNS = ("http://", "https://", "//", "mailto:", "tel:", "data:", "#", "javascript:")


def es_local(url: str) -> bool:
    if not url or url.startswith(EXTERNS):
        return False
    # Falsos positius: entitats HTML (ex. mailto codificat) i concatenacions JS
    if url.startswith("&#") or "' +" in url or '" +' in url or "${" in url:
        return False
    return True


def main() -> int:
    if not DOCS.is_dir():
        print(f"No existeix el directori: {DOCS}")
        return 2

    trencats: dict[str, set[str]] = {}
    for html in DOCS.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        for url in ATRIBUT.findall(text):
            if not es_local(url):
                continue
            net = url.split("#")[0].split("?")[0]
            if not net:
                continue
            desti = (html.parent / net).resolve()
            if not desti.exists():
                trencats.setdefault(url, set()).add(html.name)

    if not trencats:
        print("OK — cap enllaç intern trencat.")
        return 0

    print(f"Enllaços trencats: {len(trencats)}")
    for url in sorted(trencats):
        origen = ", ".join(sorted(trencats[url])[:3])
        extra = "" if len(trencats[url]) <= 3 else f" (+{len(trencats[url]) - 3})"
        print(f"  {url}  ← {origen}{extra}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
