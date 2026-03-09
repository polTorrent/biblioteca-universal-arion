import re
from urllib.parse import unquote

with open('liaozhai_toc.html', 'r') as f:
    content = f.read()

links = re.findall(r'href="/wiki/%E8%81%8A%E9%BD%8B%E8%AA%8C%E7%95%B0/([^"]+)"', content)
seen = []
for l in links:
    decoded = unquote(l)
    if decoded not in seen:
        seen.append(decoded)

for s in seen[:50]:
    print(s)
print(f'--- Total unique links: {len(seen)}')
