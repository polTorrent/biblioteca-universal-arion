#!/usr/bin/env python3
"""Descarrega 7 capítols del Mengzi des de Wikisource xinès."""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

CHAPTERS = [
    ("梁惠王上", "Liang Hui Wang I"),
    ("公孫丑上", "Gongsun Chou I"),
    ("滕文公上", "Teng Wen Gong I"),
    ("離婁上", "Li Lou I"),
    ("萬章上", "Wan Zhang I"),
    ("告子上", "Gaozi I"),
    ("盡心上", "Jin Xin I"),
]

OUTPUT = "obres/filosofia/mengzi/seleccio-7-capitols/original.md"


def fetch_chapter(ch_zh: str) -> str | None:
    page = f"孟子/{ch_zh}"
    url = (
        "https://zh.wikisource.org/w/api.php"
        f"?action=parse&page={urllib.parse.quote(page)}&prop=wikitext&format=json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    if "parse" not in data:
        return None
    wikitext = data["parse"]["wikitext"]["*"]
    # Neteja markup wiki
    wikitext = re.sub(r"\{\{[^}]*\}\}", "", wikitext)
    wikitext = re.sub(r"\[\[Category:[^\]]*\]\]", "", wikitext)
    wikitext = re.sub(r"\[\[File:[^\]]*\]\]", "", wikitext)
    wikitext = re.sub(r"<ref[^>]*>.*?</ref>", "", wikitext, flags=re.DOTALL)
    wikitext = re.sub(r"<ref[^/]*/>", "", wikitext)
    return wikitext.strip()


def main():
    parts = [
        "# 孟子 — Mengzi (Selecció de 7 capítols)\n",
        "**Autor**: 孟子 (Mengzi / Menci, c. 372–289 aC)\n",
        "**Llengua original**: xinès clàssic\n",
        "**Font**: [Wikisource](https://zh.wikisource.org/wiki/孟子)\n\n---\n",
    ]

    for ch_zh, ch_en in CHAPTERS:
        try:
            text = fetch_chapter(ch_zh)
            if text:
                parts.append(f"\n## {ch_zh} ({ch_en})\n")
                parts.append(text)
                parts.append("\n")
                print(f"OK: {ch_zh} — {len(text)} chars")
            else:
                print(f"NOT FOUND: {ch_zh}")
        except Exception as e:
            print(f"ERROR: {ch_zh}: {e}")
        time.sleep(0.5)

    output = "\n".join(parts)
    Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\nTotal: {len(output)} chars written to {OUTPUT}")


if __name__ == "__main__":
    main()
