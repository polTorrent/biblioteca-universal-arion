import re, html

with open('/home/jo/biblioteca-universal-arion/.tmp_makura_index.html') as f:
    content = f.read()

# Find all internal links
links = re.findall(r'href="(/wiki/[^"]+)"[^>]*title="([^"]+)"', content)
seen = set()
results = []
for href, title in links:
    t = html.unescape(title)
    if '\u6795\u8349\u5b50' in t and t not in seen and t != '\u6795\u8349\u5b50':
        seen.add(t)
        results.append((t, href))
        print(f"{t} -> https://ja.wikisource.org{href}")

print(f"\nTotal: {len(results)} sections found")
