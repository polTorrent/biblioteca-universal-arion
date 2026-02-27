#!/usr/bin/env python3
"""Descarrega i processa el text grec complet de l'Enchiridion d'Epíctet.

Font: Greek Wikisource (el.wikisource.org)
"""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Greek numerals mapping for chapter headers
GREEK_NUMERALS = {
    'αʹ': 'I', 'βʹ': 'II', 'γʹ': 'III', 'δʹ': 'IV', 'εʹ': 'V',
    'στʹ': 'VI', 'ζʹ': 'VII', 'ηʹ': 'VIII', 'θʹ': 'IX', 'ιʹ': 'X',
    'ιαʹ': 'XI', 'ιβʹ': 'XII', 'ιγʹ': 'XIII', 'ιδʹ': 'XIV', 'ιεʹ': 'XV',
    'ιστʹ': 'XVI', 'ιζʹ': 'XVII', 'ιηʹ': 'XVIII', 'ιθʹ': 'XIX', 'κʹ': 'XX',
    'καʹ': 'XXI', 'κβʹ': 'XXII', 'κγʹ': 'XXIII', 'κδʹ': 'XXIV', 'κεʹ': 'XXV',
    'κστʹ': 'XXVI', 'κζʹ': 'XXVII', 'κηʹ': 'XXVIII', 'κθʹ': 'XXIX', 'λʹ': 'XXX',
    'λαʹ': 'XXXI', 'λβʹ': 'XXXII', 'λγʹ': 'XXXIII', 'λδʹ': 'XXXIV', 'λεʹ': 'XXXV',
    'λστʹ': 'XXXVI', 'λζʹ': 'XXXVII', 'ληʹ': 'XXXVIII', 'λθʹ': 'XXXIX', 'μʹ': 'XL',
    'μαʹ': 'XLI', 'μβʹ': 'XLII', 'μγʹ': 'XLIII', 'μδʹ': 'XLIV', 'μεʹ': 'XLV',
    'μστʹ': 'XLVI', 'μζʹ': 'XLVII', 'μηʹ': 'XLVIII', 'μθʹ': 'XLIX', 'νʹ': 'L',
    'ναʹ': 'LI', 'νβʹ': 'LII', 'νγʹ': 'LIII',
}


def fetch_raw_text() -> str:
    """Fetch raw wikitext from Greek Wikisource."""
    url = (
        'https://el.wikisource.org/w/index.php?'
        'title=%CE%95%CE%B3%CF%87%CE%B5%CE%B9%CF%81%CE%AF%CE%B4%CE%B9%CE%BF%CE%BD'
        '&action=raw'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 BibliotecaArion/1.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
    return resp.read().decode('utf-8')


def clean_wikitext(raw: str) -> str:
    """Convert wikitext to clean markdown."""
    # Remove the header template
    text = re.sub(r'\{\{Κεφαλίδα.*?\}\}', '', raw, flags=re.DOTALL)

    # Remove <div> tags
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)

    # Remove wiki links: [[target|display]] -> display, [[target]] -> target
    text = re.sub(r'\[\[[^\]]*\|([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # Remove remaining templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)

    # Remove <ref> tags
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^/]*/>', '', text)

    # Convert chapter headers: ==αʹ== -> ## I (αʹ)
    def convert_header(match):
        greek_num = match.group(1).strip()
        roman = GREEK_NUMERALS.get(greek_num, greek_num)
        return f'\n## {roman} ({greek_num})\n'

    text = re.sub(r'^==\s*(.+?)\s*==$', convert_header, text, flags=re.MULTILINE)

    # Convert sub-headers (=== ... ===)
    text = re.sub(r'^===\s*(.+?)\s*===$', r'### \1', text, flags=re.MULTILINE)

    # Remove bold/italic wiki markup
    text = re.sub(r"'''(.+?)'''", r'\1', text)
    text = re.sub(r"''(.+?)''", r'\1', text)

    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def main() -> None:
    print("Descarregant text grec de l'Enchiridion d'Epíctet...")
    raw = fetch_raw_text()
    print(f"Descarregat: {len(raw)} caràcters")

    # Count chapters
    chapters = re.findall(r'^==\s*(.+?)\s*==$', raw, re.MULTILINE)
    print(f"Capítols trobats: {len(chapters)}")
    if not chapters:
        print("Error: no s'han trobat capítols al text descarregat.")
        sys.exit(1)
    print(f"Primer: {chapters[0]}, Últim: {chapters[-1]}")

    # Clean the text
    clean = clean_wikitext(raw)

    # Add header
    header = """# Ἐγχειρίδιον (Enchiridion / Manual)

**Autor:** Epíctet (Ἐπίκτητος), transmès per Arrià (Ἀρριανός)
**Llengua:** Grec antic (Κοινή)
**Font:** [Greek Wikisource](https://el.wikisource.org/wiki/%CE%95%CE%B3%CF%87%CE%B5%CE%B9%CF%81%CE%AF%CE%B4%CE%B9%CE%BF%CE%BD)
**Edició:** Basada en l'edició de Heinrich Schenkl (Teubner, 1916)

---

"""

    full_text = header + clean

    # Save
    output_path = Path(__file__).parent / 'enchiridion_greek.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"\nGuardat a: {output_path}")
    print(f"Mida final: {len(full_text)} caràcters")

    # Verify chapter count in output
    out_chapters = re.findall(r'^## [IVXLC]+ \(', full_text, re.MULTILINE)
    print(f"Capítols al fitxer final: {len(out_chapters)}")


if __name__ == '__main__':
    main()
