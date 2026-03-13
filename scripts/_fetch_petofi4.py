#!/usr/bin/env python3
"""Fetch remaining Petőfi poems - try with different regex."""
import urllib.request
import urllib.parse
import re
import html as h

poems = {
    'Befordúltam a konyhára': 'Befordúltam_a_konyhára...',
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
        # Try broader regex
        m = re.search(r'mw-parser-output">(.*?)(<div class="printfooter"|<noscript>)', text, re.DOTALL)
        if m:
            c = m.group(1)
            # Check for poem class
            if 'vers' in c.lower() or 'poem' in c.lower():
                print(f'=== {title} === HAS POEM CLASS')
            c = re.sub(r'<br\s*/?>', '\n', c)
            c = re.sub(r'<[^>]+>', '', c)
            c = h.unescape(c)
            c = c.strip()
            if len(c) > 30:
                print(f'=== {title} ===')
                print(c[:5000])
                print()
            else:
                print(f'=== {title} === TOO SHORT: "{c}"')
        else:
            # Debug: show first 2000 chars
            print(f'=== {title} === NO MATCH. First 500 chars of page:')
            print(text[:500])
    except Exception as e:
        print(f'=== {title} === ERROR: {e}')
