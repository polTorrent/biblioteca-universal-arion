#!/usr/bin/env python3
"""Fetch 20 poems from Les Fleurs du mal by Baudelaire from Wikisource (1868 edition)."""

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://fr.wikisource.org/w/api.php"
HEADERS = {"User-Agent": "BibliotecaArion/1.0"}

# 20 selected poems from Les Fleurs du mal (1868 edition) — correct Wikisource page titles
# NOTE: Wikisource uses typographic apostrophe \u2019 not straight apostrophe '
POEMS = [
    ("Au lecteur", "Les Fleurs du mal (1868)/Au lecteur"),
    ("Bénédiction", "Les Fleurs du mal (1868)/Bénédiction"),
    ("L\u2019Albatros", "Les Fleurs du mal (1868)/L\u2019Albatros"),
    ("Élévation", "Les Fleurs du mal (1868)/Élévation"),
    ("Correspondances", "Les Fleurs du mal (1868)/Correspondances"),
    ("La Beauté", "Les Fleurs du mal (1868)/La Beauté"),
    ("Hymne à la beauté", "Les Fleurs du mal (1868)/Hymne à la beauté"),
    ("La Chevelure", "Les Fleurs du mal (1868)/La Chevelure"),
    ("Harmonie du soir", "Les Fleurs du mal (1868)/Harmonie du soir"),
    ("L\u2019Invitation au voyage", "Les Fleurs du mal (1868)/L\u2019Invitation au voyage"),
    ("La Cloche fêlée", "Les Fleurs du mal (1868)/La Cloche fêlée"),
    ("Spleen (Quand le ciel bas et lourd\u2026)", "Les Fleurs du mal (1868)/Spleen (\u00ab Quand le ciel bas et lourd\u2026 \u00bb)"),
    ("Le Vampire", "Les Fleurs du mal (1868)/Le Vampire"),
    ("Remords posthume", "Les Fleurs du mal (1868)/Remords posthume"),
    ("Le Chat", "Les Fleurs du mal (1868)/Le Chat (\u00ab Viens, mon beau chat, sur mon c\u0153ur amoureux \u00bb)"),
    ("L\u2019Ennemi", "Les Fleurs du mal (1868)/L\u2019Ennemi"),
    ("La Vie antérieure", "Les Fleurs du mal (1868)/La Vie antérieure"),
    ("L\u2019Homme et la mer", "Les Fleurs du mal (1868)/L\u2019Homme et la mer"),
    ("Recueillement", "Les Fleurs du mal (1868)/Recueillement"),
    ("L\u2019Horloge", "Les Fleurs du mal (1868)/L\u2019Horloge"),
]


class FetchError(Exception):
    """Error fetching a poem from Wikisource."""


def fetch_poem_html(page_title: str) -> str:
    """Fetch rendered HTML for a poem page from Wikisource."""
    params = urllib.parse.urlencode({
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "format": "json",
        "disabletoc": "1",
    })
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    if "error" in data:
        raise FetchError(data["error"].get("info", "unknown API error"))

    raw_html: str = data.get("parse", {}).get("text", {}).get("*", "")
    if not raw_html.strip():
        raise FetchError("empty response from API")

    return raw_html


def html_to_text(raw_html: str) -> str:
    """Convert Wikisource poem HTML to clean plain text."""
    # Remove ws-noexport blocks (headers, footers, navigation)
    text = re.sub(
        r'<[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>',
        "", raw_html, flags=re.DOTALL,
    )
    text = re.sub(r'<small class="ws-noexport"[^>]*>.*?</small>', "", text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*ws-noexport[^>]*>.*?</div>', "", text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', "", text, flags=re.DOTALL)

    # Remove page numbers
    text = re.sub(r'<span class="pagenum"[^>]*>.*?</span>', "", text, flags=re.DOTALL)

    # Convert line breaks
    text = text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = text.replace("</p>", "\n")

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean up lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove CSS remnants at the start
    text = re.sub(r"^\.mw-parser-output[^}]*\}[^}]*\}.*?(?=\n[A-ZÀ-Ú])", "", text, flags=re.DOTALL)

    # Remove leading blank lines
    text = text.lstrip("\n")

    return text


def main() -> int:
    output_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "obres/poesia/baudelaire/20-poemes-les-flors-del-mal/original.md"
    )

    parts: list[str] = [
        "# Les Fleurs du mal — Charles Baudelaire",
        "",
        "*Selecció de 20 poemes (edició 1868, domini públic)*",
        "",
        "Font: [Wikisource](https://fr.wikisource.org/wiki/Les_Fleurs_du_mal_(1868))",
        "",
        "---",
        "",
    ]

    success_count = 0

    for i, (display_title, page) in enumerate(POEMS, 1):
        short = page.split("/")[-1]
        print(f"  [{i}/20] {short}...", end=" ", flush=True)

        try:
            raw_html = fetch_poem_html(page)
            text = html_to_text(raw_html)
            char_count = len(text)
            print(f"OK ({char_count} chars)")
            parts.append(f"## {i}. {display_title}")
            parts.append("")
            parts.append(text)
            success_count += 1
        except Exception as e:
            print(f"FAIL: {e}")
            parts.append(f"## {i}. {display_title}")
            parts.append("")
            parts.append(f"*[Error: {e}]*")

        parts.append("")
        parts.append("---")
        parts.append("")

        if i < len(POEMS):
            time.sleep(0.5)

    content = "\n".join(parts)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n  {success_count}/20 poemes obtinguts correctament")
    print(f"  Guardat: {output_path} ({len(content)} caràcters)")

    return 0 if success_count >= 15 else 1


if __name__ == "__main__":
    sys.exit(main())
