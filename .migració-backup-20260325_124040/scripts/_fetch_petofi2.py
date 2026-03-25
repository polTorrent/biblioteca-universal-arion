#!/usr/bin/env python3
"""Search Wikisource for missing Petőfi poems."""
import urllib.request
import urllib.parse
import re
import html as h
import json

# Try different URL patterns for missing poems
attempts = [
    ('Befordultam a konyhára', [
        'Befordúltam_a_konyhára',
        'Befordultam_a_konyhára_(Petőfi_Sándor)',
        'Befordúltam_a_konyhára...',
    ]),
    ('Ha férfi vagy, légy férfi', [
        'Ha_férfi_vagy,_légy_férfi_(Petőfi_Sándor)',
        'Ha_férfi_vagy,_légy_férfi!',
    ]),
    ('Itt van az ősz, itt van újra', [
        'Itt_van_az_ősz,_itt_van_ujra',
        'Itt_van_az_ősz,_itt_van_újra_(Petőfi_Sándor)',
        'Itt_van_az_ősz,_itt_van_újra...',
    ]),
    ('Föltámadott a tenger', [
        'Föltámadott_a_tenger...',
        'Föltámadott_a_tenger!',
        'Feltámadott_a_tenger',
    ]),
    ('Az őrült', [
        'Az_őrült_(Petőfi_Sándor)',
        'Az_őrült_(Petőfi)',
    ]),
    ('István öcsémhez', [
        'István_öcsémhez_(Petőfi_Sándor)',
        'István_öcsémhez_(Petőfi)',
    ]),
]

# Also try Wikisource search API
for title, urls in attempts:
    found = False
    for slug in urls:
        url = f'https://hu.wikisource.org/wiki/{urllib.parse.quote(slug, safe="")}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            text = resp.read().decode('utf-8')
            m = re.search(r'class="mw-parser-output">(.*?)<div class="printfooter"', text, re.DOTALL)
            if m:
                c = m.group(1)
                c = re.sub(r'<br\s*/?>', '\n', c)
                c = re.sub(r'<[^>]+>', '', c)
                c = h.unescape(c)
                lines = [line.strip() for line in c.strip().split('\n')]
                while lines and not lines[0]:
                    lines.pop(0)
                while lines and not lines[-1]:
                    lines.pop()
                content = '\n'.join(lines)
                if len(content) > 50:
                    print(f'=== {title} === (found at {slug})')
                    print(content[:4000])
                    print()
                    found = True
                    break
        except Exception:
            continue

    if not found:
        # Try search API
        search_url = f'https://hu.wikisource.org/w/api.php?action=opensearch&search={urllib.parse.quote(title)}&limit=5&format=json'
        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            if len(data) > 1 and data[1]:
                print(f'=== {title} === SEARCH RESULTS: {data[1]}')
            else:
                print(f'=== {title} === NOT FOUND ANYWHERE')
        except Exception as e:
            print(f'=== {title} === SEARCH ERROR: {e}')
