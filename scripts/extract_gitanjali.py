#!/usr/bin/env python3
"""Extract 30 selected poems from Gitanjali raw text."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = PROJECT_ROOT / "gitanjali_raw.txt"
TARGET = (
    PROJECT_ROOT
    / "obres/poesia/rabindranath-tagore/gitanjali-seleccio-30-poemes/original.md"
)

SELECTED: list[int] = [
    1, 2, 3, 4, 5, 7, 10, 11, 12, 13,
    16, 22, 23, 27, 30, 34, 35, 36, 39, 45,
    48, 50, 56, 59, 67, 69, 72, 86, 96, 103,
]


def extract_poems(lines: list[str]) -> dict[int, str]:
    """Find poem boundaries and extract text."""
    poem_starts: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+)\.$", line.strip())
        if m and int(m.group(1)) <= 103:
            poem_starts.append((i, int(m.group(1))))

    poems: dict[int, str] = {}
    for idx, (start_line, num) in enumerate(poem_starts):
        if idx + 1 < len(poem_starts):
            end_line = poem_starts[idx + 1][0]
        else:
            search_limit = min(start_line + 100, len(lines))
            end_line = search_limit
            for j in range(start_line + 1, search_limit):
                if "***" in lines[j] or "End of" in lines[j]:
                    end_line = j
                    break
        poem_text = "\n".join(lines[start_line + 1 : end_line]).strip()
        poems[num] = poem_text

    return poems


def build_output(poems: dict[int, str]) -> tuple[str, int]:
    """Build markdown output for selected poems. Returns (text, word_count)."""
    output: list[str] = [
        "# Gitanjali (Song Offerings)",
        "## Rabindranath Tagore (1912)",
        "",
        "*Seleccio de 30 poemes de l'edicio anglesa de 1912, "
        "traduida pel propi autor del bengali original.*",
        "*Text de domini public -- Font: Project Gutenberg (ebook #7164)*",
        "",
        "---",
        "",
    ]

    word_count = 0
    missing: list[int] = []
    for num in SELECTED:
        if num not in poems:
            missing.append(num)
            continue
        output.append(f"### {num}.")
        output.append("")
        output.append(poems[num])
        output.append("")
        output.append("---")
        output.append("")
        word_count += len(poems[num].split())

    if missing:
        print(f"Warning: poems not found in source: {missing}", file=sys.stderr)

    return "\n".join(output), word_count


def main() -> None:
    if not RAW_FILE.exists():
        print(f"Error: {RAW_FILE} not found", file=sys.stderr)
        sys.exit(1)

    lines = RAW_FILE.read_text(encoding="utf-8").split("\n")
    poems = extract_poems(lines)
    text, word_count = build_output(poems)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")

    print(f"Total poems found: {len(poems)}")
    print(f"Selected: {len(SELECTED)}")
    print(f"Word count: {word_count}")
    print(f"{TARGET.name} written successfully")


if __name__ == "__main__":
    main()
