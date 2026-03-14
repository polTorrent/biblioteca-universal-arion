#!/usr/bin/env python3
"""Extract selected Theocritus Idylls from Perseus XML."""

import xml.etree.ElementTree as ET

ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

tree = ET.parse('/home/jo/biblioteca-universal-arion/_theocritus_raw.xml')
root = tree.getroot()

# Selected idylls with their titles (Greek, Catalan)
idylls_info = {
    '1': ('Θύρσις ἢ ᾠδή', 'Tirsis o el cant'),
    '2': ('Φαρμακεύτριαι', 'Les fetilleres'),
    '7': ('Θαλύσια', 'Les festes de la collita'),
    '11': ('Κύκλωψ', 'El Ciclop'),
    '15': ('Συρακούσιαι ἢ Ἀδωνιάζουσαι',
           "Les siracusanes o les dones a la festa d'Adonis"),
    '18': ('Ἑλένης ἐπιθαλάμιος', "Epitalami d'Helena"),
    '24': ('Ἡρακλίσκος', 'El petit Hèracles'),
}

roman = {
    '1': 'I', '2': 'II', '7': 'VII', '11': 'XI',
    '15': 'XV', '18': 'XVIII', '24': 'XXIV',
}

edition_div = root.find('.//tei:div[@type="edition"]', ns)
poems = edition_div.findall('tei:div[@type="textpart"][@subtype="poem"]', ns)

header = (
    "# Εἰδύλλια (Idil·lis — selecció)\n"
    "**Autor:** Θεόκριτος (Teòcrit)\n"
    "**Font:** [Perseus Digital Library]"
    "(https://www.perseus.tufts.edu/hopper/text?"
    "doc=Perseus%3Atext%3A1999.01.0228)\n"
    "**Llengua:** grec antic\n"
    "\n---\n"
)

TEI = '{http://www.tei-c.org/ns/1.0}'


def extract_poem_text(elem):
    """Recursively extract lines and speaker labels."""
    result = []
    for child in elem:
        tag = child.tag.replace(TEI, '')
        if tag == 'head':
            continue
        elif tag == 'speaker':
            speaker_name = (child.text or '').strip()
            if speaker_name:
                result.append(('speaker', speaker_name))
        elif tag == 'l':
            text = ''.join(child.itertext()).strip()
            if text:
                result.append(('line', text))
        elif tag in ('sp', 'lg', 'p', 'div'):
            result.extend(extract_poem_text(child))
    return result


output = header

for poem in poems:
    n = poem.get('n')
    if n not in idylls_info:
        continue

    greek_title, catalan_title = idylls_info[n]
    output += "\n## Εἰδύλλιον {} — {} ({})\n\n".format(
        roman[n], greek_title, catalan_title
    )

    elements = extract_poem_text(poem)
    for kind, text in elements:
        if kind == 'speaker':
            output += "\n**{}**\n\n".format(text)
        else:
            output += "{}  \n".format(text)

    output += "\n"

# Write output
out_path = '/home/jo/biblioteca-universal-arion/obres/poesia/teocrit/idillis/original.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output)

# Stats
for n in ['1', '2', '7', '11', '15', '18', '24']:
    matching = [p for p in poems if p.get('n') == n]
    if matching:
        line_count = len(matching[0].findall('.//tei:l', ns))
        print("Idyll {}: {} lines".format(n, line_count))

print("\nFile written to", out_path)
