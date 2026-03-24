import re

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/morgenrothe_de.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Manual mapping of all 41 wanted aphorisms to their start lines (0-indexed)
manual_starts = {
    193: 6807,
    202: 7228,
    213: 7882,
    215: 7924,
    216: 7959,
    218: 8002,
    231: 8193,
    232: 8207,
    235: 8237,
    237: 8255,
    243: 8399,
    253: 8523,
    257: 8649,
    259: 8664,
    281: 8994,
    287: 9057,
    295: 9147,
    306: 9317,
    311: 9389,
    314: 9422,
    315: 9443,
    317: 9457,
    324: 9596,
    329: 9692,
    330: 9717,
    331: 9724,
    335: 9758,
    343: 9842,
    345: 9871,
    347: 9894,
    350: 9919,
    351: 9935,
    357: 9993,
    364: 10063,
    367: 10101,
    371: 10153,
    375: 10198,
    395: 10427,
    406: 10528,
    415: 10600,
    416: 10609,
}

# English titles from Gutenberg #39955 (Kennedy translation) for reference
english_titles = {
    193: "Esprit und Moral",
    202: "Zur Pflege der Gesundheit",
    213: "Das Wasser der Religion",
    215: "Opfer-Gesinnung",
    216: "Die Boesen und die Musik",
    218: "Mit seinen Schwaechen als Kuenstler schalten",
    231: "Von der deutschen Tugend",
    232: "Aus einer Disputation",
    235: "Dank abweisen",
    237: "Eine Parteinoth",
    243: "Die Denker als Vorzeichner",
    253: "Ueberall wo der Einzelne zurueckgeschoben wird",
    257: "Gefahr in der Milde",
    259: "Einem Geiste, der nicht rein ist",
    281: "Das Ich will Alles haben",
    287: "Der Fascinirte",
    295: "Gedankenstrich",
    306: "Griechisches Ideal",
    311: "Die sogenannte Seele",
    314: "Aus der Gesellschaft der Denker",
    315: "Sich entaeussern",
    317: "Das Urtheil des Abends",
    324: "Gegen Schwarmgeisterei",
    329: "Die Vorsichtigen",
    330: "Noch nicht genug!",
    331: "Recht und Graenze",
    335: "Damit Liebe als Liebe gespuert werde",
    343: "Zur Beruhigung",
    345: "Ehrlicher Gegner",
    347: "Um unsern Gedanken unrecht zu geben",
    350: "An die Traumer der Unsterblichkeit",
    351: "Weg damit!",
    357: "Eine Aeusserung fuer das Ohr",
    364: "Der Ueberlaeufer",
    367: "Langsam!",
    371: "Gefahr in der Person",
    375: "Was haben wir noetig?",
    395: "Die Contemplation",
    406: "Unsterblich machen",
    415: "Remedium amoris",
    416: "Wo ist der schlimmste Feind?",
}

# Find ALL aphorism starts to determine boundaries
all_starts = []
seen = set()
for i, line in enumerate(lines):
    stripped = line.strip()
    for fixfunc in [
        lambda s: s,
        lambda s: s.replace('l', '1'),
        lambda s: s.replace('o', '0'),
        lambda s: s.replace('i', '1'),
        lambda s: s.replace('^', '1'),
        lambda s: s.replace('l', '1').replace('o', '0').replace('i', '1').replace('^', '1'),
    ]:
        fixed = fixfunc(stripped)
        m = re.match(r'^(\d{1,3})[\.\-,]\s*[\x95\xb7\u2022]?\s*$', fixed)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 575 and num not in seen:
                if not re.match(r'^[\u2014\-]\s*\d+\s*[\u2014\-]', stripped):
                    all_starts.append((num, i))
                    seen.add(num)
                    break

for num, idx in manual_starts.items():
    if num not in seen:
        all_starts.append((num, idx))
        seen.add(num)

all_starts.sort(key=lambda x: x[1])

end_map = {}
for idx_pos, (num, line_idx) in enumerate(all_starts):
    if idx_pos + 1 < len(all_starts):
        end_map[num] = all_starts[idx_pos + 1][1]
    else:
        end_map[num] = len(lines)

def clean_text(raw, aph_num):
    # Remove the OCR number line at the start (e.g. "193-", "202,", "2l6.", "28l.", etc.)
    raw = re.sub(r'^[^\n]*\n', '', raw, count=1)  # remove first line (the number)
    # Remove page number lines
    raw = re.sub(r'\n\s*[\u2014\-]+\s*\d+\s*[\u2014\-]+\s*\n', '\n', raw)
    raw = re.sub(r'\n\s*Nietzsche,\s*Morgenr\u00f6the\.\s*\d+\s*\n', '\n', raw)
    raw = re.sub(r'\n\s*Digi[lt]ized\s+by\s+Google\s*\n', '\n', raw)
    raw = re.sub(r'\n\s*\d+\*\s*\n', '\n', raw)
    # Remove standalone page numbers (just a number on its own line, 3 digits)
    raw = re.sub(r'\n\s*\d{3}\s*\n', '\n', raw)
    raw = re.sub(r'\n{3,}', '\n\n', raw)
    return raw.strip()

output = []
for num in sorted(manual_starts.keys()):
    start = manual_starts[num]
    end = end_map.get(num, start + 50)
    text = ''.join(lines[start:end])
    text = clean_text(text, num)
    # Get the title from first line of text
    first_line = text.split('\n')[0].strip()
    output.append(f"### {num}. {first_line.split(' — ')[0] if ' — ' in first_line else first_line.split('.')[0] if '.' in first_line else first_line}\n{text}")

result = '\n\n\n'.join(output)

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/aphorisms_extracted.md', 'w', encoding='utf-8') as f:
    f.write("# Nietzsche - Morgenrothe: Ausgewaehlte Aphorismen (Deutsches Original)\n")
    f.write("# Quelle: Archive.org OCR der 1887 Ausgabe (gemeinfrei / public domain)\n")
    f.write("# Hinweis: OCR-Artefakte koennen vorhanden sein\n\n")
    f.write(result)

print(f"Extracted {len(manual_starts)} aphorisms")
print("Saved to aphorisms_extracted.md")
