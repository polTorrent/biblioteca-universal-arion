#!/usr/bin/env python3
import re

with open('/home/jo/biblioteca-universal-arion/wikisource_meditations.html', 'r') as f:
    html = f.read()

# Find all links in the page
links = re.findall(r'href="(/wiki/[^"]*?)"[^>]*>([^<]*)</a>', html)
for href, text in links:
    text = text.strip()
    if len(text) > 0:
        print(f'{text} -> {href}')
