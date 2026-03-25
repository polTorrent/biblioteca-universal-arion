#!/usr/bin/env python3
"""Fetch Tsurezuregusa from Japanese Wikisource - extract 50 selected dan."""
from __future__ import annotations

import html as html_mod
import re
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

BASE = "https://ja.wikisource.org"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BibliotecaArion/1.0)"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"ERROR fetching {url}: {exc}", file=sys.stderr)
        sys.exit(1)
    return resp.read().decode("utf-8")

def extract_text(raw_html: str) -> str:
    """Extract main content text from Wikisource page."""
    match = re.search(r'<div class="mw-parser-output">(.*?)<div[^>]*class="[^"]*printfooter', raw_html, re.DOTALL)
    if not match:
        match = re.search(r'<div class="mw-parser-output">(.*)', raw_html, re.DOTALL)
    content = match.group(1) if match else raw_html

    # Remove navigation, categories, tables, etc.
    content = re.sub(r'<div[^>]*class="[^"]*catlinks[^"]*".*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*navbox[^"]*".*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*".*?</div>', '', content, flags=re.DOTALL)

    # Convert <br> to newlines
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'<p[^>]*>', '', content)

    # Remove remaining tags
    content = re.sub(r'<[^>]+>', '', content)
    content = html_mod.unescape(content)

    # Clean up
    lines = [l.rstrip() for l in content.split('\n')]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return '\n'.join(lines)


# Selected 50 most representative dan
# Mix of: philosophy of impermanence, aesthetics, nature, human nature, humor, Buddhism
SELECTED = [
    1, 2, 7, 10, 11, 13, 14, 19, 21, 25,
    29, 32, 35, 39, 45, 52, 53, 55, 59, 67,
    72, 74, 75, 82, 92, 95, 102, 108, 109, 117,
    120, 127, 131, 137, 138, 142, 148, 150, 155, 157,
    167, 170, 175, 188, 189, 211, 215, 231, 241, 243,
]


def parse_sections(text: str) -> dict[int, str]:
    sections: dict[int, str] = {}
    current_num: int | None = None
    current_text: list[str] = []

    for line in text.split('\n'):
        stripped = line.strip()
        if re.match(r'^\d+$', stripped) and 1 <= int(stripped) <= 243:
            if current_num is not None:
                sections[current_num] = '\n'.join(current_text).strip()
            current_num = int(stripped)
            current_text = []
        elif current_num is not None:
            current_text.append(line)

    if current_num is not None:
        sections[current_num] = '\n'.join(current_text).strip()

    return sections


def build_output(sections: dict[int, str]) -> tuple[str, list[int]]:
    output_lines = [
        "**Autor:** Yoshida Kenkō (吉田兼好)",
        "**Font:** [wikisource_ja](https://ja.wikisource.org/wiki/%E5%BE%92%E7%84%B6%E8%8D%89_(%E6%A0%A1%E8%A8%BB%E6%97%A5%E6%9C%AC%E6%96%87%E5%AD%B8%E5%A4%A7%E7%B3%BB))",
        "**Llengua:** japonès clàssic",
        "**Edició:** 校註日本文學大系 (Kōchū Nihon Bungaku Taikei)",
        "**Selecció:** 50 capítols de 243",
        "",
        "---",
        "",
        "# 徒然草 — Tsurezuregusa",
        "",
        "吉田兼好 (Yoshida Kenkō)",
        "",
    ]

    missing: list[int] = []
    for num in SELECTED:
        if num in sections:
            output_lines.append(f"## 第{num}段")
            output_lines.append("")
            output_lines.append(sections[num])
            output_lines.append("")
            output_lines.append("")
        else:
            missing.append(num)

    return '\n'.join(output_lines), missing


def main() -> None:
    url = BASE + "/wiki/%E5%BE%92%E7%84%B6%E8%8D%89_(%E6%A0%A1%E8%A8%BB%E6%97%A5%E6%9C%AC%E6%96%87%E5%AD%B8%E5%A4%A7%E7%B3%BB)"
    print("Fetching full text...")
    html_content = fetch(url)
    text = extract_text(html_content)

    sections = parse_sections(text)
    print(f"Parsed {len(sections)} sections")

    output, missing = build_output(sections)
    if missing:
        print(f"WARNING: Missing sections: {missing}", file=sys.stderr)

    repo_root = Path(__file__).resolve().parent.parent
    outpath = repo_root / "obres/oriental/yoshida-kenko/tsurezuregusa/original.md"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(output, encoding="utf-8")

    included = len([n for n in SELECTED if n in sections])
    print(f"Written {len(output)} chars to {outpath}")
    print(f"Sections included: {included}/{len(SELECTED)}")


if __name__ == "__main__":
    main()
