#!/usr/bin/env python3
"""Descarrega els 7 capítols de Micromégas de Wikisource FR."""
import urllib.request
import re
import html
import sys

def fetch_chapter(num):
    url = f'https://fr.wikisource.org/wiki/Microm%C3%A9gas/Chapitre_{num}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (BibliotecaArion/1.0)'})
    resp = urllib.request.urlopen(req, timeout=30)
    page = resp.read().decode('utf-8')
    # Extract parser output div
    m = re.search(r'class="mw-parser-output"[^>]*>(.*?)(?:<div class="printfooter|<!--\s*\nNewPP)', page, re.DOTALL)
    if not m:
        return f'[ERROR fetching chapter {num}]'
    content = m.group(1)
    # Remove styles, tables, noexport divs
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div class="ws-noexport"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    # Convert headers
    content = re.sub(r'<h[23][^>]*>(.*?)</h[23]>', r'\n## \1\n', content)
    # Convert br and p
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'<p[^>]*>', '\n', content)
    content = re.sub(r'</p>', '\n', content)
    # Strip remaining tags
    content = re.sub(r'<[^>]+>', '', content)
    content = html.unescape(content)
    # Clean lines
    lines = [l.strip() for l in content.split('\n')]
    lines = [l for l in lines if l]
    return '\n\n'.join(lines)

chapters_nums = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
chapters = []
for num in chapters_nums:
    print(f'Fetching chapter {num}...', flush=True)
    text = fetch_chapter(num)
    chapters.append(text)
    print(f'  Got {len(text)} chars')

full = '\n\n---\n\n'.join(chapters)
print(f'\nTotal: {len(full)} chars')

outpath = 'obres/narrativa/voltaire/micromegas/original.md'
header = """# Micromégas
**Autor:** Voltaire
**Font:** [Wikisource](https://fr.wikisource.org/wiki/Microm%C3%A9gas)
**Llengua:** francès

---

"""

with open(outpath, 'w', encoding='utf-8') as f:
    f.write(header + full)
print(f'Saved to {outpath}')
