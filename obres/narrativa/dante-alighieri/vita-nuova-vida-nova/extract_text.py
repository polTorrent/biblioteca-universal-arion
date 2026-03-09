#!/usr/bin/env python3
"""Extreu el text de Dante del fitxer raw de Gutenberg."""
import re
from pathlib import Path

raw_path = Path(__file__).parent / "vita_nuova_raw.txt"
out_path = Path(__file__).parent / "original.md"

lines = raw_path.read_text(encoding="utf-8").splitlines(keepends=True)
text = "".join(lines[550:2656])

# Treure marcadors d'il·lustració
text = re.sub(r"\s*\[Illustrazione:.*?\]\s*", "\n\n", text)
# Netejar línies buides múltiples
text = re.sub(r"\n{3,}", "\n\n", text)
text = text.strip()

header = """# Vita Nuova (La Vida Nova)

**Autor:** Dante Alighieri
**Font:** Project Gutenberg (ed. A. Agresti, 1902)
**Llengua:** italià

---

"""

out_path.write_text(header + text + "\n", encoding="utf-8")
print(f"Escrit original.md: {len(text)} caràcters de text")
