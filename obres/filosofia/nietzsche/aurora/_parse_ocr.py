#!/usr/bin/env python3
"""Parse and clean Book 5 of Morgenrothe from OCR text."""
import re

with open("/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/_morgenrothe_ocr.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

text = "".join(lines[10672:])

# Find aphorism number markers (lines like "423." or "425-" or "494-")
pattern = re.compile(r"^\s*[•]?\s*(\d{3})[.\-]\s*$", re.MULTILINE)
matches = list(pattern.finditer(text))
print(f"Found {len(matches)} aphorism markers:")
nums = []
for m in matches:
    n = int(m.group(1))
    nums.append(n)
    print(f"  {n}")

# Find missing
expected = set(range(423, 576))
found = set(nums)
missing = sorted(expected - found)
print(f"\nMissing aphorisms: {missing}")
