#!/usr/bin/env python3
"""Fix remaining Cyrillic and other issues"""
import unicodedata

path = '/home/jo/biblioteca-universal-arion/obres/narrativa/txekhov/sala-numero-6/traduccio.md'
with open(path, 'r') as f:
    text = f.read()

# Find all Cyrillic chars
for i, line in enumerate(text.split('\n'), 1):
    for j, c in enumerate(line):
        if 'CYRILLIC' in unicodedata.name(c, ''):
            print(f'Line {i}, pos {j}: char={repr(c)} ({unicodedata.name(c)})')
            ctx = line[max(0,j-20):j+20]
            print(f'  Context: {ctx}')

# Replace all instances containing Cyrillic in name patterns
# м = CYRILLIC SMALL LETTER EM
# і = CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
# т = CYRILLIC SMALL LETTER TE
# Replace the full name patterns
text = text.replace('Andréi Iefі\u043cі\u0442x', 'Andrei Iefímitx')

# Try character by character replacement for the specific pattern
lines = text.split('\n')
fixed_lines = []
for line in lines:
    if any('CYRILLIC' in unicodedata.name(c, '') for c in line):
        # Replace Cyrillic chars that look like Latin
        cyrillic_to_latin = {
            '\u043c': 'm',  # м → m
            '\u0456': 'i',  # і → i
            '\u0442': 't',  # т → t
            '\u0430': 'a',  # а → a
            '\u0435': 'e',  # е → e
            '\u043e': 'o',  # о → o
            '\u0440': 'r',  # р → r
            '\u0441': 's',  # с → s
        }
        new_line = ''
        for c in line:
            if c in cyrillic_to_latin:
                new_line += cyrillic_to_latin[c]
            else:
                new_line += c
        # Now fix the name that was partially Cyrillic
        new_line = new_line.replace('Andréi Iefimitx', 'Andrei Iefímitx')
        fixed_lines.append(new_line)
        print(f'Fixed Cyrillic line: {new_line[:80]}')
    else:
        fixed_lines.append(line)

text = '\n'.join(fixed_lines)

# Also fix remaining dialogue issues
text = text.replace('"Al diable!"', '—Al diable!')

# Fix remaining "Andréi" (without Cyrillic)
text = text.replace('Andréi Iefímitx', 'Andrei Iefímitx')

with open(path, 'w') as f:
    f.write(text)

print('\nDone!')
