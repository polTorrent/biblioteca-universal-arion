#!/usr/bin/env python3
"""Clean HTML entities from original.md files.

Usage: python3 scripts/clean_html_entities.py <path>
"""
import html
import re
import sys


def clean_html_entities(text: str) -> str:
    """Decode HTML entities and normalize whitespace."""
    text = text.replace("&nbsp;", " ").replace("&thinsp;", " ")
    text = html.unescape(text)
    text = re.sub(r"  +", " ", text)
    return text


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        text = f.read()

    cleaned = clean_html_entities(text)

    with open(path, "w", encoding="utf-8") as f:
        f.write(cleaned)
    print(f"OK - cleaned {path}")


if __name__ == "__main__":
    main()
