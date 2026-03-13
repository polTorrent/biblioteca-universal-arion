"""Parseja el XML de Perseus per extreure el text grec d'Els Treballs i els Dies d'Hesíode."""

import re
import html as h
import sys
from pathlib import Path

INPUT_PATH = Path("/tmp/hesiod_perseus.xml")
DEST = Path(__file__).resolve().parent.parent / "obres/poesia/hesiode/els-treballs-i-els-dies/original.md"


def parse_greek_lines(xml: str) -> list[str]:
    """Extreu línies gregues netes del XML de Perseus."""
    raw_lines = re.findall(r'<l[^>]*>(.*?)</l>', xml, re.DOTALL)
    skip_prefixes = (
        'Greek', 'English', 'Basic', 'Text key', 'Check', 'Revise', 'Fix', 'converted',
    )
    clean_lines: list[str] = []
    for line in raw_lines:
        clean = re.sub(r'<[^>]+>', '', line)
        clean = h.unescape(clean).strip()
        if clean and not clean.startswith(skip_prefixes):
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', clean):
                clean_lines.append(clean)
    return clean_lines


def main() -> None:
    if not INPUT_PATH.exists():
        print(f"Error: no s'ha trobat {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    xml = INPUT_PATH.read_text(encoding="utf-8")
    lines = parse_greek_lines(xml)
    print(f"Total Greek lines: {len(lines)}")

    cards = re.findall(r'<milestone[^>]*unit="card"[^>]*n="(\d+)"', xml)
    print(f"Card markers: {cards}")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with open(DEST, "w", encoding="utf-8") as f:
        f.write("# Ἔργα καὶ Ἡμέραι\n\n")
        f.write("**Ἡσίοδος** (Hesiod, s. VIII-VII aC)\n\n")
        f.write("Font: Perseus Digital Library (CC BY-SA 3.0)\n\n")
        f.write("---\n\n")
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {DEST}")
    print("\nFirst 10 lines:")
    for line in lines[:10]:
        print(line)
    print("\nLast 5 lines:")
    for line in lines[-5:]:
        print(line)


if __name__ == "__main__":
    main()
