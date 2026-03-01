#!/usr/bin/env python3
"""Extract and clean OCR text for Aurora aphorisms 183-422."""
import re
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open('_morgenrothe_ocr.txt', 'r') as f:
    lines = f.readlines()

# Extract lines for aphorisms 183 to end of Book IV (before Fünftes Buch)
raw = ''.join(lines[6470:10672])

# Remove page numbers like '— 170 —'
raw = re.sub(r'\n\n+— \d+ —\n\n+', '\n', raw)

# Fix hyphenated words across lines
raw = re.sub(r'(\w)-\s*\n(\w)', r'\1\2', raw)

# Fix OCR artifacts
raw = raw.replace('^', '')

# Join continuation lines into paragraphs
paragraphs = []
current = []
for line in raw.split('\n'):
    stripped = line.strip()
    if re.match(r'^\d+\.\s*$', stripped):
        if current:
            paragraphs.append(' '.join(current))
            current = []
        paragraphs.append('')
        paragraphs.append(stripped)
    elif stripped == '':
        if current:
            paragraphs.append(' '.join(current))
            current = []
        paragraphs.append('')
    else:
        current.append(stripped)

if current:
    paragraphs.append(' '.join(current))

result = '\n'.join(paragraphs)
result = re.sub(r'\n{3,}', '\n\n', result)

# Format as markdown
formatted = []
p_lines = result.split('\n')
i = 0
while i < len(p_lines):
    line = p_lines[i].strip()
    m = re.match(r'^(\d+)\.\s*$', line)
    if m:
        num = m.group(1)
        i += 1
        while i < len(p_lines) and p_lines[i].strip() == '':
            i += 1
        if i < len(p_lines):
            text = p_lines[i].strip()
            title_match = re.match(r'^(.+?)\s*—\s*', text)
            if title_match:
                title = title_match.group(1).strip().rstrip('.')
                formatted.append(f'### {num}. {title}')
                formatted.append('')
                formatted.append(text)
            else:
                formatted.append(f'### {num}. {text}')
                formatted.append('')
                formatted.append(text)
        formatted.append('')
    else:
        if line:
            if formatted and formatted[-1] != '':
                formatted[-1] = formatted[-1] + ' ' + line
            else:
                formatted.append(line)
        else:
            if formatted and formatted[-1] != '':
                formatted.append('')
    i += 1

with open('_buch3_4_clean.md', 'w') as f:
    f.write('\n'.join(formatted))

print(f'Done. {len(formatted)} lines written.')
