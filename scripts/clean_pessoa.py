#!/usr/bin/env python3
"""Clean poem tags from original.md"""
import re

p = "obres/poesia/fernando-pessoa/o-guardador-de-rebanhos-el-guardador-de-ramats/original.md"
with open(p) as f:
    t = f.read()
t = t.replace("<poem>", "").replace("</poem>", "")
t = re.sub(r"\n{4,}", "\n\n\n", t)
with open(p, "w") as f:
    f.write(t)
print(f"Cleaned. Size: {len(t)} chars")
