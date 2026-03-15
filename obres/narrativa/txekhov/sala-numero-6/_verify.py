#!/usr/bin/env python3
import unicodedata

path = '/home/jo/biblioteca-universal-arion/obres/narrativa/txekhov/sala-numero-6/traduccio.md'
with open(path) as f:
    text = f.read()

# Check Cyrillic
cyrillic_found = False
for i, line in enumerate(text.split('\n'), 1):
    for c in line:
        if 'CYRILLIC' in unicodedata.name(c, ''):
            print(f'Line {i}: still has Cyrillic')
            cyrillic_found = True
            break
if not cyrillic_found:
    print('No Cyrillic remaining')

# Check name variants
variants = [
    "Andrey ", "Efímitx", "Dmitritch", "Dmitrikh", "Mihail ",
    "Moisseika", "Sergueïtx", "Serguèievitx", "Dariuxka",
    " Hobotov", "Andréi ", "Dmitritx ", "Averianítx",
    "Averiànytx", "Dmítrïtx"
]
for v in variants:
    if v in text:
        idx = text.find(v)
        ctx = text[max(0,idx-20):idx+len(v)+20]
        print(f'Name variant: "{v}" in: ...{ctx}...')

# Check artifacts
if '`json' in text:
    print('JSON artifact found')
if 'Canviant' in text and 'concís' in text:
    print('Editing notes found')
if '"Ievgueni' in text and '": "' in text:
    print('JSON data found')

# Check grammar
if 'del anglès' in text:
    print('Grammar: "del anglès" still present')

print(f'\nTotal lines: {len(text.split(chr(10)))}')
print(f'Total chars: {len(text)}')
