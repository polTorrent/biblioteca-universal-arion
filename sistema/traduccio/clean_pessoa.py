#!/usr/bin/env python3
"""Clean poem tags from original.md"""
import re
import sys
from pathlib import Path

p = Path("obres/poesia/fernando-pessoa/o-guardador-de-rebanhos-el-guardador-de-ramats/original.md")
if not p.exists():
    print(f"Error: {p} no existeix", file=sys.stderr)
    sys.exit(1)
t = p.read_text(encoding="utf-8")
t = t.replace("<poem>", "").replace("</poem>", "")
t = re.sub(r"\n{4,}", "\n\n\n", t)
p.write_text(t, encoding="utf-8")
print(f"Cleaned. Size: {len(t)} chars")
