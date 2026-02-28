#!/usr/bin/env python3
"""Descarrega Fröken Julie de Projekt Runeberg i genera original.md."""

import html
import re
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError


BASE_URL = "https://runeberg.org/frkjulie/"
PARTS = ["01.html", "02.html", "03.html", "04.html", "05.html"]
OUTPUT = Path("obres/teatre/august-strindberg/froken-julie-la-senyoreta-julia/original.md")


def fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset)


def html_to_text(raw_html: str) -> str:
    body_match = re.search(r"<body[^>]*>(.*?)</body>", raw_html, re.DOTALL)
    if not body_match:
        return ""
    text = body_match.group(1)
    # Remove navigation
    text = re.sub(r"<form.*?</form>", "", text, flags=re.DOTALL)
    text = re.sub(r"<table.*?</table>", "", text, flags=re.DOTALL)
    # Remove Project Runeberg footer
    text = re.sub(r"<tt>Project Runeberg.*?</tt>", "", text, flags=re.DOTALL)
    text = re.sub(r'<a href="https://validator.*?</a>', "", text, flags=re.DOTALL)
    text = re.sub(r'<a href="https://www.defective.*?</a>', "", text, flags=re.DOTALL)
    # Convert tags to markdown
    text = re.sub(r"<h[123][^>]*>(.*?)</h[123]>", r"\n## \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p\b[^>]*>", "\n\n", text)
    text = re.sub(r"<hr[^>]*>", "\n---\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # Clean whitespace
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    header = """# Fröken Julie

**Ett naturalistiskt sorgespel**

*August Strindberg* (1888)

**Font**: [Projekt Runeberg](https://runeberg.org/frkjulie/) — domini públic

---

## Personer

- **Fröken Julie**, 25 år
- **Jean**, Betjänt, 30 år
- **Kristin**, Kokerska, 35 år

---

"""
    parts_text: list[str] = []
    for part in PARTS:
        url = BASE_URL + part
        print(f"  Descarregant {url}...")
        try:
            raw = fetch_page(url)
        except (HTTPError, URLError, TimeoutError) as e:
            print(f"    Error descarregant {url}: {e}", file=sys.stderr)
            sys.exit(1)
        text = html_to_text(raw)
        parts_text.append(text)
        print(f"    {len(text)} caràcters")

    full_text = header + "\n\n---\n\n".join(parts_text)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(full_text + "\n", encoding="utf-8")

    word_count = len(full_text.split())
    print(f"\nEscrit a {OUTPUT}")
    print(f"Total: {word_count} paraules, {len(full_text)} caràcters")


if __name__ == "__main__":
    main()
