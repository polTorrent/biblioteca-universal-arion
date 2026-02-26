#!/usr/bin/env python3
"""Save clean Greek text of Plato's Crito."""
import html
import re

with open('/home/jo/.claude/projects/-home-jo-biblioteca-universal-arion/f3dc1f59-49a8-4be2-ab33-c1e1af10fc98/tool-results/b4df65c.txt', 'r') as f:
    content = f.read()

match = re.search(r'mw-parser-output(.*?)catlinks', content, re.DOTALL)
text = match.group(1)
text = re.sub(r'<br\s*/?>', '\n', text)
text = re.sub(r'<p>', '\n', text)
text = re.sub(r'</p>', '', text)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = text.strip()

lines = text.split('\n')

# Find start
start_idx = 0
for i, line in enumerate(lines):
    if 'ΚΡΙΤΩΝ' in line and len(line.strip()) < 20:
        start_idx = i
        break

# Find end - remove Wikisource footer
end_idx = len(lines)
for i in range(len(lines) - 1, -1, -1):
    line = lines[i].strip()
    if line.startswith('Ανακτήθηκε') or 'wikisource.org' in line:
        end_idx = i
        break

# Clean
clean_lines = []
for line in lines[start_idx:end_idx]:
    stripped = line.strip()
    if not stripped:
        if clean_lines and clean_lines[-1] != '':
            clean_lines.append('')
        continue
    if stripped.startswith('.mw-parser'):
        continue
    if 'Συγγραφέας:' in stripped:
        continue
    if stripped.startswith('ed.John Burnet'):
        continue
    if 'St.I' in stripped:
        continue
    stripped = re.sub(r'^p\.\d+\s*$', '', stripped)
    if not stripped:
        continue
    clean_lines.append(stripped)

while clean_lines and clean_lines[-1] == '':
    clean_lines.pop()

final_lines = [l for l in clean_lines if 'Ανακτήθηκε' not in l and 'wikisource.org' not in l]

result = '\n'.join(final_lines)

# Write the file
output_path = '/home/jo/biblioteca-universal-arion/crito_original_greek.md'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(result + '\n')

print(f"Written to {output_path}")
print(f"Lines: {len(final_lines)}")
print(f"Characters: {len(result)}")

# Count Greek characters
greek_chars = sum(1 for c in result if '\u0370' <= c <= '\u03FF' or '\u1F00' <= c <= '\u1FFF')
print(f"Greek characters: {greek_chars}")
