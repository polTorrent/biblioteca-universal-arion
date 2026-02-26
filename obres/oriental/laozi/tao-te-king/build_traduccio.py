#!/usr/bin/env python3
"""Fusiona els chunks de traducció en un sol traduccio.md complet."""
import os

d = '/home/jo/biblioteca-universal-arion/obres/oriental/laozi/tao-te-king'

header = """# Tao Te King (道德經)
*Laozi (老子)*

Traduït del xinès clàssic per Biblioteca Arion

---

## 道經 (Llibre del Tao)

"""

with open(os.path.join(d, 'tao_ch1_27.md')) as f:
    ch1_27 = f.read()

with open(os.path.join(d, 'tao_ch28_54.md')) as f:
    lines = f.readlines()

# Lines 0-39 are chapters XXVIII-XXXVII, line 40 is ---, lines 42+ are XXXVIII-LIV
ch28_37 = ''.join(lines[:40])
ch38_54 = ''.join(lines[42:])

separator = """
---

## 德經 (Llibre del Te)

"""

with open(os.path.join(d, 'tao_ch55_81.md')) as f:
    ch55_81 = f.read()

footer = """
---

*Traducció de domini públic — Biblioteca Universal Arion*
*Llicència CC BY-SA 4.0*
"""

content = header + ch1_27 + '\n' + ch28_37 + separator + ch38_54 + '\n' + ch55_81 + footer

with open(os.path.join(d, 'traduccio.md'), 'w') as f:
    f.write(content)

words = len(content.split())
lines_count = content.count('\n')
print(f'Done. Lines: {lines_count}, Words: {words}')
