#!/usr/bin/env python3
"""Fetch Tsurezuregusa from Japanese Wikisource - extract 50 selected dan."""
import urllib.request
import re
import html as html_mod

BASE = "https://ja.wikisource.org"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BibliotecaArion/1.0)"})
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read().decode("utf-8")

def extract_text(raw_html):
    """Extract main content text from Wikisource page."""
    match = re.search(r'<div class="mw-parser-output">(.*?)<div[^>]*class="[^"]*printfooter', raw_html, re.DOTALL)
    if not match:
        match = re.search(r'<div class="mw-parser-output">(.*)', raw_html, re.DOTALL)
    content = match.group(1) if match else raw_html

    # Remove navigation, categories, tables, etc.
    content = re.sub(r'<div[^>]*class="[^"]*catlinks[^"]*".*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*navbox[^"]*".*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*".*?</div>', '', content, flags=re.DOTALL)

    # Convert <br> to newlines
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'<p[^>]*>', '', content)

    # Remove remaining tags
    content = re.sub(r'<[^>]+>', '', content)
    content = html_mod.unescape(content)

    # Clean up
    lines = [l.rstrip() for l in content.split('\n')]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return '\n'.join(lines)


# Fetch the full text
url = BASE + "/wiki/%E5%BE%92%E7%84%B6%E8%8D%89_(%E6%A0%A1%E8%A8%BB%E6%97%A5%E6%9C%AC%E6%96%87%E5%AD%B8%E5%A4%A7%E7%B3%BB)"
print("Fetching full text...")
html_content = fetch(url)
text = extract_text(html_content)

# Parse into sections by number
sections = {}
current_num = None
current_text = []

for line in text.split('\n'):
    stripped = line.strip()
    # Check if this is a section number (standalone number)
    if re.match(r'^\d+$', stripped) and 1 <= int(stripped) <= 243:
        if current_num is not None:
            sections[current_num] = '\n'.join(current_text).strip()
        current_num = int(stripped)
        current_text = []
    elif current_num is not None:
        current_text.append(line)

# Don't forget the last section
if current_num is not None:
    sections[current_num] = '\n'.join(current_text).strip()

print(f"Parsed {len(sections)} sections")

# Selected 50 most representative dan
# Mix of: philosophy of impermanence, aesthetics, nature, human nature, humor, Buddhism
SELECTED = [
    1, 2, 7, 10, 11, 13, 14, 19, 21, 25,
    29, 32, 35, 39, 45, 52, 53, 55, 59, 67,
    72, 74, 75, 82, 92, 95, 102, 108, 109, 117,
    120, 127, 131, 137, 138, 142, 148, 150, 155, 157,
    167, 170, 175, 188, 189, 211, 215, 231, 241, 243,
]

# Build output
output_lines = []
output_lines.append(f"**Autor:** Yoshida Kenkō (吉田兼好)")
output_lines.append(f"**Font:** [wikisource_ja](https://ja.wikisource.org/wiki/%E5%BE%92%E7%84%B6%E8%8D%89_(%E6%A0%A1%E8%A8%BB%E6%97%A5%E6%9C%AC%E6%96%87%E5%AD%B8%E5%A4%A7%E7%B3%BB))")
output_lines.append(f"**Llengua:** japonès clàssic")
output_lines.append(f"**Edició:** 校註日本文學大系 (Kōchū Nihon Bungaku Taikei)")
output_lines.append(f"**Selecció:** 50 capítols de 243")
output_lines.append("")
output_lines.append("---")
output_lines.append("")
output_lines.append("# 徒然草 — Tsurezuregusa")
output_lines.append("")
output_lines.append("吉田兼好 (Yoshida Kenkō)")
output_lines.append("")

missing = []
for num in SELECTED:
    if num in sections:
        output_lines.append(f"## 第{num}段")
        output_lines.append("")
        output_lines.append(sections[num])
        output_lines.append("")
        output_lines.append("")
    else:
        missing.append(num)

if missing:
    print(f"WARNING: Missing sections: {missing}")

output = '\n'.join(output_lines)

# Write to file
outpath = "obres/oriental/yoshida-kenko/tsurezuregusa/original.md"
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Written {len(output)} chars to {outpath}")
print(f"Sections included: {len([n for n in SELECTED if n in sections])}/{len(SELECTED)}")
