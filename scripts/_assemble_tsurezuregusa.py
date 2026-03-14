#!/usr/bin/env python3
"""Assembla la traducció completa del Tsurezuregusa a partir de chunks i grups."""
import json
import re

base = "obres/oriental/yoshida-kenko/tsurezuregusa"

# Load chunks
with open(f"{base}/.chunks_traduïts.json") as f:
    chunks = json.load(f)

# Combine all text sources
all_text = ""
for k in sorted(chunks.keys(), key=lambda x: int(x.split("_")[1])):
    all_text += chunks[k] + "\n\n"
for i in range(1, 5):
    with open(f"{base}/_group{i}.md") as f:
        all_text += f.read() + "\n\n"

# Split into fragments
fragments = {}
parts = re.split(r"(?=^## )", all_text, flags=re.MULTILINE)
for part in parts:
    part = part.strip()
    if not part:
        continue
    m = re.match(r"^## (Primer fragment|Segon fragment|Fragment (\d+))", part)
    if m:
        if m.group(0) == "## Primer fragment":
            num = 1
        elif m.group(0) == "## Segon fragment":
            num = 2
        else:
            num = int(m.group(2))
        fragments[num] = part

sorted_nums = sorted(fragments.keys())
print(f"Total fragments: {len(sorted_nums)}")
print(f"Fragment numbers: {sorted_nums}")

header = (
    "# Tsurezuregusa \u2014 Ociositats\n"
    "*Yoshida Kenk\u014d (\u5409\u7530\u517c\u597d)*\n\n"
    "Tradu\u00eft del japon\u00e8s cl\u00e0ssic per Biblioteca Arion\n\n"
    "Selecci\u00f3 de 50 fragments dels 243 originals\n\n"
    "---\n\n"
)

body = "\n\n".join(fragments[n] for n in sorted_nums)

footer = "\n\n---\n\n*Traducci\u00f3 de domini p\u00fablic \u2014 CC BY-SA 4.0*\n"

final = header + body + footer

out_path = f"{base}/traduccio.md"
with open(out_path, "w") as f:
    f.write(final)

print(f"\nEscrit a {out_path}: {len(final)} chars")
