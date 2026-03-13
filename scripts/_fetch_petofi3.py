#!/usr/bin/env python3
"""Fetch remaining missing Petőfi poems."""
import urllib.request
import urllib.parse
import re
import html as h

poems = {
    'Befordúltam a konyhára': 'Befordúltam_a_konyhára...',
    'Ha férfi vagy, légy férfi': 'Ha_férfi_vagy,_légy_férfi...',
    'Az őrült': 'Az_őrült',
    'István öcsémhez': 'István_öcsémhez',
}

for title, slug in poems.items():
    encoded = urllib.parse.quote(slug, safe='')
    url = f'https://hu.wikisource.org/wiki/{encoded}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode('utf-8')
        m = re.search(r'class="mw-parser-output">(.*?)<div class="printfooter"', text, re.DOTALL)
        if m:
            c = m.group(1)
            c = re.sub(r'<br\s*/?>', '\n', c)
            c = re.sub(r'<[^>]+>', '', c)
            c = h.unescape(c)
            lines = [l.strip() for l in c.strip().split('\n')]
            while lines and not lines[0]:
                lines.pop(0)
            while lines and not lines[-1]:
                lines.pop()
            content = '\n'.join(lines)
            print(f'=== {title} ===')
            print(content[:5000])
            print()
        else:
            print(f'=== {title} === CONTENT NOT FOUND IN PAGE')
    except Exception as e:
        print(f'=== {title} === ERROR: {e}')
