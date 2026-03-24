#!/usr/bin/env python3
"""Extract Greek text from CTS XML responses for De Anima."""
import re
from pathlib import Path

BASE = Path("/home/jo/biblioteca-universal-arion")

output_lines = [
    "**Autor:** Aristòtil (Ἀριστοτέλης)",
    "**Obra:** Περὶ Ψυχῆς (De Anima — Sobre l'Ànima)",
    "**Font:** Edició W.D. Ross, Oxford: Clarendon Press, 1956",
    "**Repositori digital:** [Scaife Viewer / First1KGreek](https://scaife.stoa.org/reader/urn:cts:greekLit:tlg0086.tlg002.1st1K-grc2/)",
    "**Llengua:** grec antic",
    "",
    "---",
    "",
]

book_titles = {
    1: "Βιβλίον Α (Llibre I)",
    2: "Βιβλίον Β (Llibre II)",
    3: "Βιβλίον Γ (Llibre III)",
}

for book_num in range(1, 4):
    xml_file = BASE / f".tmp_book{book_num}.xml"
    xml = xml_file.read_text(encoding="utf-8")

    output_lines.append(f"# {book_titles[book_num]}")
    output_lines.append("")

    # Extract chapters using div tags
    chapters = re.findall(r'<div[^>]*n="(\d+)"[^>]*type="chapter"[^>]*>(.*?)</div>', xml, re.DOTALL)
    if not chapters:
        # Try alternative: divs with n attribute at chapter level
        chapters = re.findall(r'<div[^>]*n="(\d+)"[^>]*>(.*?)</div>', xml, re.DOTALL)

    if chapters:
        for ch_num, ch_content in chapters:
            output_lines.append(f"## Capítol {ch_num}")
            output_lines.append("")
            # Remove XML tags but keep text
            text = re.sub(r'<[^>]+>', ' ', ch_content)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                # Split into paragraphs at reasonable points (sentences)
                output_lines.append(text)
                output_lines.append("")
    else:
        # Fallback: just extract all text content
        text = re.sub(r'<[^>]+>', ' ', xml)
        text = re.sub(r'\s+', ' ', text).strip()
        # Find Greek content
        words = text.split()
        greek_start = None
        for i, w in enumerate(words):
            if any(ord(c) > 0x0370 and ord(c) < 0x03FF for c in w):
                greek_start = i
                break
        if greek_start is not None:
            greek_text = ' '.join(words[greek_start:])
            output_lines.append(greek_text)
            output_lines.append("")

output_path = BASE / "obres/filosofia/aristotil/peri-psykhes/original.md"
output_path.write_text('\n'.join(output_lines), encoding='utf-8')
print(f"Written {len(output_lines)} lines to {output_path}")

# Count Greek characters
full_text = '\n'.join(output_lines)
greek_chars = sum(1 for c in full_text if ord(c) > 0x0370 and ord(c) < 0x03FF)
print(f"Greek characters: {greek_chars}")
print(f"Total characters: {len(full_text)}")
