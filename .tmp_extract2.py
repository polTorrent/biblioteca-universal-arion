import re, html, urllib.request, urllib.parse

# Try the Wikisource version
url = "https://ja.wikisource.org/wiki/%E6%9E%95%E8%8D%89%E5%AD%90_(Wikisource)"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    content = resp.read().decode('utf-8')

with open('/home/jo/biblioteca-universal-arion/.tmp_makura_ws.html', 'w') as f:
    f.write(content)

print(f"Downloaded {len(content)} bytes")

# Check for section links
links = re.findall(r'href="(/wiki/[^"]+)"[^>]*>([^<]+)', content)
for href, title in links[:50]:
    t = html.unescape(title.strip())
    if t and len(t) > 1:
        print(f"  {t}")
