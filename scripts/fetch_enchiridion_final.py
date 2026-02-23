#!/usr/bin/env python3
"""Descarrega i processa el text grec complet de l'Enchiridion d'Epíctet.

Font: Greek Wikisource (el.wikisource.org)
Genera el fitxer original.md net per la biblioteca.
"""

import re
import urllib.request


def fetch_raw_text():
    """Fetch raw wikitext from Greek Wikisource."""
    url = (
        'https://el.wikisource.org/w/index.php?'
        'title=%CE%95%CE%B3%CF%87%CE%B5%CE%B9%CF%81%CE%AF%CE%B4%CE%B9%CE%BF%CE%BD'
        '&action=raw'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 BibliotecaArion/1.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read().decode('utf-8')


def clean_wikitext(raw):
    """Convert wikitext to clean markdown."""
    # Remove the header template
    text = re.sub(r'\{\{Κεφαλίδα.*?\}\}', '', raw, flags=re.DOTALL)

    # Remove <div> tags
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)

    # Remove <br> and <br/> tags - replace with newline
    text = re.sub(r'<br\s*/?>', '\n', text)

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

    # Convert chapter headers: ==αʹ== -> ## I
    greek_to_arabic = {
        'αʹ': 1, 'βʹ': 2, 'γʹ': 3, 'δʹ': 4, 'εʹ': 5,
        'στʹ': 6, 'ζʹ': 7, 'ηʹ': 8, 'θʹ': 9, 'ιʹ': 10,
        'ιαʹ': 11, 'ιβʹ': 12, 'ιγʹ': 13, 'ιδʹ': 14, 'ιεʹ': 15,
        'ιστʹ': 16, 'ιζʹ': 17, 'ιηʹ': 18, 'ιθʹ': 19, 'κʹ': 20,
        'καʹ': 21, 'κβʹ': 22, 'κγʹ': 23, 'κδʹ': 24, 'κεʹ': 25,
        'κστʹ': 26, 'κζʹ': 27, 'κηʹ': 28, 'κθʹ': 29, 'λʹ': 30,
        'λαʹ': 31, 'λβʹ': 32, 'λγʹ': 33, 'λδʹ': 34, 'λεʹ': 35,
        'λστʹ': 36, 'λζʹ': 37, 'ληʹ': 38, 'λθʹ': 39, 'μʹ': 40,
        'μαʹ': 41, 'μβʹ': 42, 'μγʹ': 43, 'μδʹ': 44, 'μεʹ': 45,
        'μστʹ': 46, 'μζʹ': 47, 'μηʹ': 48, 'μθʹ': 49, 'νʹ': 50,
        'ναʹ': 51, 'νβʹ': 52, 'νγʹ': 53,
    }

    def convert_header(match):
        greek_num = match.group(1).strip()
        num = greek_to_arabic.get(greek_num, greek_num)
        return f'\n## {num}\n'

    text = re.sub(r'^==\s*(.+?)\s*==$', convert_header, text, flags=re.MULTILINE)

    # Remove wiki-style numbered list markers (#) at the start of paragraphs
    # These are used in the wikitext for sub-sections within chapters
    # Use negative lookahead to avoid stripping markdown ## headers
    text = re.sub(r'^#(?!#)', '', text, flags=re.MULTILINE)

    # Remove indentation markers (::)
    text = re.sub(r'^:+', '', text, flags=re.MULTILINE)

    # Remove bold/italic wiki markup
    text = re.sub(r"'''(.+?)'''", r'\1', text)
    text = re.sub(r"''(.+?)''", r'\1', text)

    # Remove interwiki links at the end
    text = re.sub(r'\n[a-z]{2}:.+$', '', text, flags=re.MULTILINE)

    # Remove trailing "Εγχειριδιον" footer lines
    text = re.sub(r'\n?Εγχειριδιον\s*', '', text)

    # Normalize double spaces to single (wiki artifact)
    text = re.sub(r'  +', ' ', text)

    # Remove trailing spaces on lines
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)

    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def main():
    print("Descarregant text grec de l'Enchiridion d'Epíctet...")
    raw = fetch_raw_text()
    print(f"Descarregat: {len(raw)} caràcters")

    # Count chapters
    chapters = re.findall(r'^==\s*(.+?)\s*==$', raw, re.MULTILINE)
    print(f"Capítols trobats: {len(chapters)}")

    # Clean the text
    clean = clean_wikitext(raw)

    # Add header matching project convention
    header = """# Ἐγχειρίδιον

"""

    full_text = header + clean

    # Save to the project location
    output_path = '/home/jo/biblioteca-universal-arion/obres/epictetus/enchiridion/original.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"\nGuardat a: {output_path}")
    print(f"Mida final: {len(full_text)} caràcters")

    # Verify
    out_chapters = re.findall(r'^## \d+$', full_text, re.MULTILINE)
    print(f"Capítols al fitxer final: {len(out_chapters)}")

    # Count words
    words = len(full_text.split())
    print(f"Paraules: {words}")


if __name__ == '__main__':
    main()
