import re, html as html_mod, json, urllib.request, urllib.parse

poems = [
    ("Befordúltam a konyhára...", "Befordultam a konyhára"),
    ("A XIX. század költői", "A XIX. század költői"),
    ("Ha férfi vagy, légy férfi...", "Ha férfi vagy, légy férfi"),
    ("Itt van az ősz, itt van újra\u2026", "Itt van az ősz, itt van újra"),
    ("Föltámadott a tenger...", "Föltámadott a tenger"),
    ("Dalaim", "Dalaim"),
    ("Az őrült", "Az őrült"),
    ("István öcsémhez", "István öcsémhez"),
    ("Szabadság, szerelem!", "Szabadság, szerelem"),
    ("Pató Pál úr", "Pató Pál úr"),
]

for i, (wiki_title, display_title) in enumerate(poems, 1):
    encoded = urllib.parse.quote(wiki_title, safe='')
    url = f'https://hu.wikisource.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
        data = json.loads(resp)
        wikitext = data.get('parse', {}).get('wikitext', {}).get('*', '')
        if not wikitext:
            err = data.get('error', {}).get('info', 'Unknown error')
            print(f'===== {i}. {display_title} =====')
            print(f'ERROR: {err}')
            print()
            continue
        # Clean wikitext: remove templates, formatting
        text = wikitext
        # Remove header templates
        text = re.sub(r'\{\{[^}]*\}\}', '', text)
        # Remove [[ ]] links, keep display text
        text = re.sub(r'\[\[[^\]]*\|([^\]]*)\]\]', r'\1', text)
        text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
        # Remove '' and ''' (bold/italic)
        text = re.sub(r"'{2,3}", '', text)
        # Remove <poem> tags but keep content
        text = re.sub(r'</?poem>', '', text)
        # Remove other XML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up
        text = text.strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
    except Exception as e:
        text = f'ERROR: {e}'

    print(f'===== {i}. {display_title} =====')
    print(text[:5000])
    print()
