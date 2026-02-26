#!/usr/bin/env python3
"""Compila les tres parts de la traducció del Tao Te King en un sol fitxer."""

import os

base = os.path.join(os.path.dirname(__file__), '..', 'obres', 'oriental', 'laozi', 'tao-te-king')

with open(os.path.join(base, 'tao_ch1_27.md')) as f1:
    part1 = f1.read()

with open(os.path.join(base, 'tao_ch28_54.md')) as f2:
    part2 = f2.read()

with open(os.path.join(base, 'tao_ch55_81.md')) as f3:
    part3 = f3.read()

# Replace the --- separator in part2 with the De Jing section header
part2 = part2.replace(
    '\n---\n',
    '\n---\n\n**De Jing (德經) \u2014 Llibre de la Virtut**[^12]\n'
)

header = """# Tao Te King
*Laozi (老子)*

Traduït del xinès clàssic per Biblioteca Arion

---

**Dao Jing (道經) \u2014 Llibre del Dao**[^11]

"""

footer = """
---

*Traducció de domini públic.*
"""

with open(os.path.join(base, 'traduccio.md'), 'w') as out:
    out.write(header)
    out.write(part1)
    out.write('\n')
    out.write(part2)
    out.write('\n')
    out.write(part3)
    out.write(footer)

print('traduccio.md compilat correctament')
