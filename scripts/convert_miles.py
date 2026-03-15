#!/usr/bin/env python3
"""Descarrega i converteix Miles Gloriosus de The Latin Library a markdown."""
import re
import html
import urllib.request
from pathlib import Path

url = "https://www.thelatinlibrary.com/plautus/miles.shtml"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    content = resp.read().decode("latin-1")

# HTML to markdown conversion
content = re.sub(r'<br\s*/?>', '\n', content)
content = re.sub(r'<p[^>]*>', '\n\n', content)
content = re.sub(r'</p>', '', content)
content = re.sub(r'<b>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)
content = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', content, flags=re.DOTALL)
content = re.sub(r'<[^>]+>', '', content)
content = html.unescape(content)
content = re.sub(r'\n{3,}', '\n\n', content)
content = content.strip()

# Extract just the play text
lines = content.split('\n')
start = 0
end = len(lines)
for i, line in enumerate(lines):
    if 'MILES GLORIOSVS' in line or 'MILES GLORIOSUS' in line:
        start = i
        break
for i in range(len(lines) - 1, -1, -1):
    if 'The Latin Library' in lines[i] or 'thelatinlibrary' in lines[i].lower():
        end = i
        break

result = '\n'.join(lines[start:end]).strip()

# Add markdown header
header = "# Miles Gloriosus\n\n**Autor:** Titus Maccius Plautus\n**Llengua:** llatí\n**Font:** [The Latin Library](https://www.thelatinlibrary.com/plautus/miles.shtml)\n\n---\n\n"

outpath = Path("obres/teatre/plaut/miles-gloriosus/original.md")
outpath.write_text(header + result, encoding="utf-8")
print(f"Escrit {outpath} ({len(result)} caràcters, {result.count(chr(10))} línies)")
