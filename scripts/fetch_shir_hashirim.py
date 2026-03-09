#!/usr/bin/env python3
"""Fetch Song of Songs (Shir Hashirim) from Sefaria API and save as original.md"""

import json
import re
import urllib.request

OUTPUT = "obres/poesia/anonim-hebreu/cantic-dels-cantics/original.md"
BOOK = "Song_of_Songs"
CHAPTERS = 8

def fetch_chapter(ch: int) -> list[str]:
    url = f"https://www.sefaria.org/api/v3/texts/{BOOK}.{ch}?version=source"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    for v in data.get("versions", []):
        text = v.get("text", [])
        if text:
            return [re.sub(r"<[^>]+>", "", str(verse)) for verse in text]
    return []

def main():
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

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Count total verses
    total = sum(1 for l in lines if l.startswith("**"))
    print(f"\n✅ {total} versets escrits a {OUTPUT}")

if __name__ == "__main__":
    main()
