import xml.etree.ElementTree as ET

ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
tree = ET.parse('_perseus_theoc_raw.xml')
root = tree.getroot()
body = root.find('.//tei:body', ns)
main_div = body.find('tei:div', ns)
divs = main_div.findall('tei:div', ns)

wanted = ['1', '2', '7', '11', '15']
titles = {
    '1': 'Θύρσις (Thyrsis) - The death of Daphnis',
    '2': 'Φαρμακεύτρια (Pharmakeutria) - The Sorceress',
    '7': 'Θαλύσια (Thalysia) - Harvest Festival',
    '11': 'Κύκλωψ (Kyklops) - Polyphemus and Galatea',
    '15': 'Συρακόσιαι ἢ Ἀδωνιάζουσαι (Syrakosiai) - The Women at the Adonia',
}

def get_text(elem):
    text = elem.text or ''
    for child in elem:
        text += get_text(child)
        text += child.tail or ''
    return text

output = []
for d in divs:
    n = d.get('n')
    if n not in wanted:
        continue
    title = titles.get(n, '')
    output.append('')
    output.append('## Εἰδύλλιον ' + n + ' - ' + title)
    output.append('')
    lines = d.findall('.//tei:l', ns)
    for l in lines:
        ln = l.get('n', '')
        txt = get_text(l).strip()
        output.append(txt)
    output.append('')

with open('_theocritus_selected_idylls.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print('Done: ' + str(len(output)) + ' lines')
