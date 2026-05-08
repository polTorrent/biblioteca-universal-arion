#!/usr/bin/env python3
"""Fetch complete Greek text of Plato's Crito from Wikisource (Burnet 1903 ed.)"""

from __future__ import annotations

import re
import sys
import urllib.request
import html as htmlmod
from pathlib import Path
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "obres" / "filosofia" / "plato" / "criton" / "original.md"


def fetch_and_process() -> None:
    """Fetch Crito text from Greek Wikisource and write processed markdown."""
    url = "https://el.wikisource.org/wiki/%CE%9A%CF%81%CE%AF%CF%84%CF%89%CE%BD"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_html: str = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Error fetching {url}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Extract the main content area
    content_start = raw_html.find("prp-pages-output")
    if content_start < 0:
        print("Error: no s'ha trobat 'prp-pages-output' al HTML", file=sys.stderr)
        sys.exit(1)

    content_end = raw_html.find('class="printfooter"')
    if content_end < 0:
        content_end = len(raw_html)

    content = raw_html[content_start:content_end]

    # Replace <br> and block elements with newlines
    text = content
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<p[^>]*>", "", text)
    text = re.sub(r"</div>", "\n", text)
    text = re.sub(r"<div[^>]*>", "", text)

    # Convert Stephanus page markers to visible labels
    def replace_stephanus(match: re.Match[str]) -> str:
        full = match.group(0)
        num_match = re.search(r'id="p\.(\d+[a-e]?)"', full)
        if num_match:
            num = num_match.group(1)
            # Only use lettered markers (43a, 43b, etc.), skip bare page nums
            if re.match(r"^\d+$", num):
                return ""
            return f"\n[{num}] "
        return ""

    text = re.sub(
        r'<span[^>]*id="p\.\d+[a-e]?"[^>]*>.*?</span>', replace_stephanus, text
    )

    # Handle St.I markers - remove them
    text = re.sub(r'<span[^>]*id="St\.[^"]*"[^>]*>.*?</span>', "", text)

    # Remove page number spans
    text = re.sub(r'<span[^>]*class="pagenum"[^>]*>.*?</span>', "", text)

    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = htmlmod.unescape(text)

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # Remove the initial wrapping text
    if text.startswith("prp-pages-output"):
        nl = text.find("\n")
        text = text[nl:] if nl >= 0 else ""
    text = text.strip()

    # Build the final organized markdown
    lines = text.split("\n")
    output: list[str] = []
    output.append("# Κρίτων")
    output.append("")
    output.append("Plató, *Critó* (ed. John Burnet, 1903, Oxford Classical Texts)")
    output.append("")
    output.append(
        "Font: [Greek Wikisource]"
        "(https://el.wikisource.org/wiki/%CE%9A%CF%81%CE%AF%CF%84%CF%89%CE%BD)"
    )
    output.append("")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for Stephanus marker at start of line
        m = re.match(r"^\[(\d+[a-e])\]\s*(.*)", line)
        if m:
            section = m.group(1)
            rest = m.group(2).strip()
            output.append(f"## {section}")
            output.append("")
            if rest:
                output.append(rest)
                output.append("")
        elif line in (
            "ΚΡΙΤΩΝ",
            "ΣΩΚΡΑΤΗΣΚΡΙΤΩΝ",
            "ΣΩΚΡΑΤΗΣ ΚΡΙΤΩΝ",
        ):
            continue
        else:
            output.append(line)
            output.append("")

    final = "\n".join(output)
    final = re.sub(r"\n{3,}", "\n\n", final)
    final = final.strip() + "\n"

    # Write to file
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(final, encoding="utf-8")

    # Report stats
    sections = re.findall(r"^## (\d+[a-e])$", final, re.MULTILINE)
    print(f"Written {len(final)} chars to {OUTPUT_PATH}")
    print(f"Stephanus sections: {len(sections)}")
    print(f"Sections: {', '.join(sections)}")
    print()
    print("First 500 chars:")
    print(final[:500])
    print()
    print("Last 500 chars:")
    print(final[-500:])


if __name__ == "__main__":
    fetch_and_process()
