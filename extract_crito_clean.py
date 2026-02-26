#!/usr/bin/env python3
"""Extract and clean Greek text of Plato's Crito from Wikisource HTML."""
import html
import re

with open('/home/jo/.claude/projects/-home-jo-biblioteca-universal-arion/f3dc1f59-49a8-4be2-ab33-c1e1af10fc98/tool-results/b4df65c.txt', 'r') as f:
    content = f.read()

# Extract the main content area from Wikisource
match = re.search(r'mw-parser-output(.*?)catlinks', content, re.DOTALL)
if not match:
    print("ERROR: Could not find content")
    exit(1)

text = match.group(1)

# Remove HTML tags but keep text
text = re.sub(r'<br\s*/?>', '\n', text)
text = re.sub(r'<p>', '\n', text)
text = re.sub(r'</p>', '', text)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)

# Clean up whitespace
text = re.sub(r'\n{3,}', '\n\n', text)
text = text.strip()

# Remove the CSS/header cruft at the beginning
# Find where the actual dialogue starts
lines = text.split('\n')
start_idx = 0
for i, line in enumerate(lines):
    if 'ΚΡΙΤΩΝ' in line and len(line.strip()) < 20:
        start_idx = i
        break

# Find where it ends (remove Wikisource footer)
end_idx = len(lines)
for i in range(len(lines) - 1, -1, -1):
    line = lines[i].strip()
    if line.startswith('Ανακτήθηκε') or 'wikisource.org' in line:
        end_idx = i
        break
    if line == 'ΣΩ.' or line.startswith('ΣΩ. Ἔα') or line.startswith('e  ΣΩ. Ἔα'):
        end_idx = i + 1
        break

# Clean lines
clean_lines = []
for line in lines[start_idx:end_idx]:
    stripped = line.strip()
    # Skip empty lines that are just whitespace
    if not stripped:
        if clean_lines and clean_lines[-1] != '':
            clean_lines.append('')
        continue
    # Skip header/metadata lines
    if stripped.startswith('.mw-parser'):
        continue
    if 'Συγγραφέας:' in stripped:
        continue
    if stripped.startswith('ed.John Burnet'):
        continue
    if 'St.I' in stripped:
        continue
    # Clean Stephanus page markers - keep them but clean up
    # Remove leading page markers like "p.43" at start of standalone lines
    stripped = re.sub(r'^p\.\d+\s*$', '', stripped)
    if not stripped:
        continue
    clean_lines.append(stripped)

# Remove trailing empty lines
while clean_lines and clean_lines[-1] == '':
    clean_lines.pop()

# Remove the Wikisource footer line
final_lines = []
for line in clean_lines:
    if 'Ανακτήθηκε' in line:
        continue
    if 'wikisource.org' in line:
        continue
    final_lines.append(line)

result = '\n'.join(final_lines)
print(result)
