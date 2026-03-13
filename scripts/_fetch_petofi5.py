#!/usr/bin/env python3
"""Use Wikisource API to get poem text."""
import urllib.request
import urllib.parse
import json
import re
import html as h

poems = {
    'Befordúltam a konyhára...': 'Befordúltam a konyhára...',
    'Az őrült': 'Az őrült',
    'István öcsémhez': 'István öcsémhez',
}

for title, page_title in poems.items():
    # Use MediaWiki API to get parsed content
    params = urllib.parse.urlencode({
        'action': 'parse',
        'page': page_title,
        'prop': 'wikitext',
        'format': 'json',
    })
    url = f'https://hu.wikisource.org/w/api.php?{params}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        if 'parse' in data and 'wikitext' in data['parse']:
            wikitext = data['parse']['wikitext']['*']
            # Extract poem from wikitext - remove templates and wiki markup
            # Remove {{...}} templates
            wikitext = re.sub(r'\{\{[^}]*\}\}', '', wikitext)
            # Remove [[Category:...]]
            wikitext = re.sub(r'\[\[Kategória:[^\]]*\]\]', '', wikitext)
            wikitext = re.sub(r'\[\[Category:[^\]]*\]\]', '', wikitext)
            # Remove <poem> tags but keep content
            wikitext = re.sub(r'</?poem>', '', wikitext)
            # Remove <section> tags
            wikitext = re.sub(r'<section[^>]*/?>', '', wikitext)
            wikitext = re.sub(r'</section>', '', wikitext)
            # Clean up
            wikitext = wikitext.strip()
            if len(wikitext) > 20:
                print(f'=== {title} ===')
                print(wikitext[:5000])
                print()
            else:
                print(f'=== {title} === TOO SHORT')
        elif 'error' in data:
            print(f'=== {title} === API ERROR: {data["error"].get("info", "unknown")}')
        else:
            print(f'=== {title} === UNEXPECTED RESPONSE')
    except Exception as e:
        print(f'=== {title} === ERROR: {e}')
