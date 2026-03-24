#!/usr/bin/env python3
"""Merge extracted aphorisms into original.md"""
import re
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Read extracted aphorisms
with open("aphorisms_extracted.md", "r") as f:
    extracted_text = f.read()

# Parse extracted aphorisms
extracted = {}
parts = re.split(r"^(### \d+\.)", extracted_text, flags=re.M)
i = 1
while i < len(parts):
    header = parts[i]
    body = parts[i + 1] if i + 1 < len(parts) else ""
    num = int(re.search(r"(\d+)", header).group(1))
    text = header + body.rstrip()
    # Clean OCR line-break hyphens
    text = re.sub(r"-\s*\n\s*", "", text)
    # Rejoin single newlines (not double)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    extracted[num] = text.strip()
    i += 2

print(f"Extracted {len(extracted)} aphorisms: {sorted(extracted.keys())}")

# Read original.md
with open("original.md", "r") as f:
    original = f.read()

# Split into blocks by ### N. headers
blocks = re.split(r"(?=^### \d+\.)", original, flags=re.M)
header_block = blocks[0]  # Everything before first aphorism

# Parse existing aphorisms
existing = {}
for block in blocks[1:]:
    m = re.match(r"^### (\d+)\.", block)
    if m:
        existing[int(m.group(1))] = block.rstrip()

print(f"Original has {len(existing)} aphorisms")

# Merge
for num, text in extracted.items():
    if num not in existing:
        existing[num] = text

print(f"After merge: {len(existing)} aphorisms")

# Find book boundaries in header
book_headers = {
    "Erstes Buch": (1, 96),
    "Zweites Buch": (97, 148),
    "Drittes Buch": (149, 275),
    "Viertes Buch": (276, 422),
    "Fuenftes Buch": (423, 575),
}

# Rebuild: header + aphorisms in order, preserving book headers
# Extract book headers from original text
book_header_lines = {}
for line in original.split("\n"):
    for buch in ["Erstes", "Zweites", "Drittes", "Viertes", "Fünftes"]:
        if re.match(rf"^## {buch} Buch", line):
            book_header_lines[buch] = line.strip()

# Build output
output = [header_block.rstrip()]
last_book = None

for num in sorted(existing.keys()):
    # Determine which book
    if num <= 96:
        book = "Erstes"
    elif num <= 148:
        book = "Zweites"
    elif num <= 275:
        book = "Drittes"
    elif num <= 422:
        book = "Viertes"
    else:
        book = "Fünftes"

    if book != last_book:
        if book in book_header_lines and book_header_lines[book] not in output[-1]:
            # Check if already in header_block
            if book_header_lines[book] not in header_block:
                output.append("\n\n" + book_header_lines[book] + "\n")
        last_book = book

    output.append("\n" + existing[num])

result = "\n".join(output) + "\n"

with open("original.md", "w") as f:
    f.write(result)

# Verify
with open("original.md", "r") as f:
    content = f.read()
count = len(re.findall(r"^### \d+\.", content, re.M))
print(f"Final original.md: {count} numbered aphorisms")
