#!/usr/bin/env python3
"""Fetch Song of Songs (Shir Hashirim) from Sefaria API and save as original.md"""

import json
import re
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

OUTPUT = Path("obres/poesia/anonim-hebreu/cantic-dels-cantics/original.md")
BOOK = "Song_of_Songs"
CHAPTERS = 8


def _flatten_text(text: list | str) -> list[str]:
    """Sefaria pot retornar text com a llista niuada o string; aplanem."""
    if isinstance(text, str):
        return [text]
    result: list[str] = []
    for item in text:
        if isinstance(item, list):
            result.extend(_flatten_text(item))
        else:
            result.append(str(item))
    return result


def fetch_chapter(ch: int) -> list[str]:
    url = f"https://www.sefaria.org/api/v3/texts/{BOOK}.{ch}?version=source"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"  ✗ Error descarregant capítol {ch}: {exc}")
        return []
    for v in data.get("versions", []):
        text = v.get("text", [])
        if text:
            flat = _flatten_text(text)
            return [re.sub(r"<[^>]+>", "", verse) for verse in flat]
    return []


def main() -> None:
    lines = ["# שיר השירים — Càntic dels Càntics (Song of Songs)\n"]
    lines.append("**Llengua original**: hebreu bíblic\n")
    lines.append("**Font**: Sefaria.org — Miqra According to the Masorah (CC BY-SA)\n")
    lines.append("---\n")

    for ch in range(1, CHAPTERS + 1):
        print(f"  Capítol {ch}...")
        verses = fetch_chapter(ch)
        if not verses:
            print(f"  ⚠ Cap vers trobat al capítol {ch}")
            continue
        lines.append(f"\n## פרק {ch} — Capítol {ch}\n")
        for i, verse in enumerate(verses, 1):
            lines.append(f"**{ch}:{i}** {verse}\n")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    total = sum(1 for line in lines if line.startswith("**"))
    print(f"\n✅ {total} versets escrits a {OUTPUT}")

if __name__ == "__main__":
    main()
