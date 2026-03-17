#!/usr/bin/env python3
"""Extract Menschliches Allzumenschliches text from Gutenberg raw download."""

with open("/home/jo/biblioteca-universal-arion/nietzsche_menschliches_raw.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Lines 39-11485 (1-indexed) contain the actual text
body = "".join(lines[38:11485]).strip()

header = (
    "# Menschliches, Allzumenschliches\n"
    "# Ein Buch für freie Geister\n"
    "\n"
    "**Friedrich Nietzsche** (1878)\n"
    "\n"
    "*Text complet del primer i segon volum.*\n"
    "*Font: Project Gutenberg (ID 7207), domini públic.*\n"
    "\n"
    "---\n"
    "\n"
)

output = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/menschliches-allzumenschliches/original.md"
with open(output, "w", encoding="utf-8") as f:
    f.write(header + body + "\n")

print(f"DONE - wrote {len(body)} chars")
