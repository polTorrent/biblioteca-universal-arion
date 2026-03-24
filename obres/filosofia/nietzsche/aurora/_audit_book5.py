#!/usr/bin/env python3
"""Audit Llibre V: compare original vs translation length and detect truncation."""
import re

def extract_aphorisms(filepath):
    with open(filepath) as f:
        content = f.read()
    blocks = re.split(r"(?=^### \d+\.)", content, flags=re.M)
    aphs = {}
    for block in blocks:
        m = re.match(r"^### (\d+)\.", block)
        if m:
            num = int(m.group(1))
            aphs[num] = block.strip()
    return aphs

orig = extract_aphorisms("original.md")
trad = extract_aphorisms("traduccio.md")

print("=== LLIBRE V AUDIT (423-575) ===")
print(f"{'Aph':>4} {'Orig':>6} {'Trad':>6} {'Ratio':>6} {'Status'}")
print("-" * 50)

suspect = []
for n in range(423, 576):
    if n in orig and n in trad:
        o_len = len(orig[n])
        t_len = len(trad[n])
        ratio = t_len / o_len if o_len > 0 else 0
        status = ""
        if ratio < 0.3:
            status = "TRUNCAT"
            suspect.append(n)
        elif ratio < 0.5:
            status = "CURT"
            suspect.append(n)
        elif ratio > 2.0:
            status = "LLARG?"
        print(f"{n:>4} {o_len:>6} {t_len:>6} {ratio:>6.2f} {status}")

print(f"\nSospitosos (ratio < 0.5): {len(suspect)}")
print(f"Llista: {suspect}")
