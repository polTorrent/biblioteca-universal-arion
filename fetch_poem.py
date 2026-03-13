import sys, re, html, urllib.request, urllib.parse, json

title = sys.argv[1]

api_url = 'https://hu.wikisource.org/w/api.php?action=parse&format=json&prop=text&page=' + urllib.parse.quote(title)
req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))

if 'error' in data:
    # Try search API to find the correct page
    search_url = 'https://hu.wikisource.org/w/api.php?action=opensearch&format=json&search=' + urllib.parse.quote(title.replace('_', ' '))
    req2 = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
    resp2 = urllib.request.urlopen(req2)
    sdata = json.loads(resp2.read().decode('utf-8'))
    if len(sdata) > 1 and sdata[1]:
        print(f"PAGE NOT FOUND: {title}")
        print(f"SUGGESTIONS: {sdata[1][:5]}")
    else:
        print(f"PAGE NOT FOUND: {title} (no suggestions)")
    sys.exit(0)

text = data['parse']['text']['*']

# Remove style/script tags
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

# For bilingual poems (table with two columns), extract only left column (Hungarian)
table_match = re.search(r'<table[^>]*width="100%"[^>]*>(.*?)</table>', text, flags=re.DOTALL)
if table_match:
    rows = re.findall(r'<td[^>]*>(.*?)</td>', table_match.group(1), flags=re.DOTALL)
    if rows:
        text = rows[0]

# Remove navigation/header divs
text = re.sub(r'<div[^>]*class="fejsablon[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
text = re.sub(r'<div[^>]*class="ws-noexport[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)

# Extract poem lines from dd elements
parts = re.split(r'</dl>\s*(?:<p>\s*(?:<br\s*/?>)?\s*</p>\s*)?<dl>', text)
final_lines = []
for i, part in enumerate(parts):
    dd_in_part = re.findall(r'<dd>(.*?)</dd>', part, flags=re.DOTALL)
    for dd in dd_in_part:
        clean = re.sub(r'<br\s*/?>', '\n', dd)
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = html.unescape(clean).strip()
        if clean:
            final_lines.append(clean)
    if i < len(parts) - 1 and dd_in_part:
        final_lines.append('')

if final_lines:
    print('\n'.join(final_lines))
else:
    # Fallback: strip HTML
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    lines_out = [l.strip() for l in text.split('\n')]
    result_out = []
    prev_blank = False
    for l in lines_out:
        if l == '':
            if not prev_blank:
                result_out.append(l)
            prev_blank = True
        else:
            result_out.append(l)
            prev_blank = False
    print('\n'.join(result_out).strip())
