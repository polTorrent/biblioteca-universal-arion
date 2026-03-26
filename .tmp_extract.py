#!/usr/bin/env python3
"""Extract Greek text from Perseus TEI XML."""
import xml.etree.ElementTree as ET
import re

tree = ET.parse('/home/jo/biblioteca-universal-arion/.tmp_apologia_grc.xml')
root = tree.getroot()
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

body = root.find('.//tei:body', ns)
sections = body.findall('.//tei:div[@type="textpart"]', ns)
if not sections:
    sections = body.findall('.//tei:div', ns)

output = []
for div in sections:
    section_n = div.get('n', '')
    text = ''.join(div.itertext()).strip()
    text = re.sub(r'\s+', ' ', text)
    if text and len(text) > 10:
        output.append(f'## [{section_n}]\n\n{text}\n')

result = '\n'.join(output)
print(f'Sections: {len(output)}')
print(f'Characters: {len(result)}')
print('---PREVIEW---')
print(result[:500])
print('...END PREVIEW...')
print(result[-300:])

outpath = '/home/jo/biblioteca-universal-arion/.tmp_apologia_clean.txt'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(result)
print(f'Written to {outpath}')
