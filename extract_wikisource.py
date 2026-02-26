#!/usr/bin/env python3
"""Extract Greek text of Plato's Crito from Wikisource HTML."""
import html
import re

with open('/home/jo/.claude/projects/-home-jo-biblioteca-universal-arion/f3dc1f59-49a8-4be2-ab33-c1e1af10fc98/tool-results/b4df65c.txt', 'r') as f:
    content = f.read()

# Extract the main content area from Wikisource
match = re.search(r'mw-parser-output(.*?)catlinks', content, re.DOTALL)

if match:
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
    print(text[:80000])
else:
    print('NO MATCH FOUND')
    greek_matches = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]{10,}', content)
    print(f'Found {len(greek_matches)} Greek text segments')
    for m in greek_matches[:5]:
        print(m[:200])
