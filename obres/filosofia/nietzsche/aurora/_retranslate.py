#!/usr/bin/env python3
"""Extract the original German text for the worst truncated aphorisms."""
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

worst = []
for n in range(423, 576):
    if n in orig and n in trad:
        o_len = len(orig[n])
        t_len = len(trad[n])
        ratio = t_len / o_len if o_len > 0 else 0
        if ratio < 0.25:
            worst.append((n, ratio, o_len))

print(f"Aforismes amb ratio < 0.25: {len(worst)}")
for n, ratio, olen in worst:
    print(f"\n{'='*80}")
    print(f"### AFORISME {n} (ratio: {ratio:.2f}, orig: {olen} chars)")
    print(f"{'='*80}")
    print(f"ORIGINAL:\n{orig[n][:2000]}")
    print(f"\nTRADUCCIO ACTUAL:\n{trad[n]}")
