#!/usr/bin/env python3
"""Build final original.md for Plato's Apology."""

with open('/home/jo/biblioteca-universal-arion/.tmp_apologia_clean.txt', 'r') as f:
    greek = f.read()

header = (
    "# Ἀπολογία Σωκράτους\n"
    "**Autor:** Πλάτων (Plató)\n"
    "**Font:** [Perseus Digital Library — Platonis Opera, ed. Burnet (1905)]"
    "(https://github.com/PerseusDL/canonical-greekLit/blob/master/data/tlg0059/tlg002/tlg0059.tlg002.perseus-grc2.xml)\n"
    "**Llengua:** grec antic\n"
    "\n---\n\n"
)

outpath = '/home/jo/biblioteca-universal-arion/obres/filosofia/plato/apologia/original.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(header + greek)

import os
size = os.path.getsize(outpath)
print(f'Escrit: {size} bytes')
print('DONE')
