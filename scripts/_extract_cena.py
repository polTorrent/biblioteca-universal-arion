#!/usr/bin/env python3
"""Extreu la Cena Trimalchionis (cap. XXVI-LXXVIII) del Satyricon complet."""
from pathlib import Path

obra_dir = Path("obres/narrativa/petroni/cena-trimalchionis-el-banquet-de-trimalcio")
original = obra_dir / "original.md"

with open(original, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Cena Trimalchionis: cap XXVI (línia 199) fins final cap LXXVIII (línia 609)
# 0-indexed: 198 to 608
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if line.strip() == "## XXVI.":
        start_idx = i
    if line.strip() == "## LXXIX.":
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"ERROR: start={start_idx}, end={end_idx}")
    exit(1)

cena_lines = lines[start_idx:end_idx]
cena_text = "".join(cena_lines).strip()
print(f"Extracted lines {start_idx+1}-{end_idx} ({len(cena_lines)} lines, {len(cena_text)} chars)")

header = """**Autor:** Petronius
**Font:** [wikisource](https://la.wikisource.org/wiki/Satyricon)
**Llengua:** llatí

---

"""

with open(original, "w", encoding="utf-8") as f:
    f.write(header + cena_text + "\n")

print(f"original.md reescrit amb la Cena Trimalchionis (cap. XXVI-LXXVIII)")
