import re, html

with open("/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/_vorrede_raw.html") as f:
    content = f.read()

match = re.search(r'<article[^>]*>(.*?)</article>', content, re.DOTALL)
if match:
    text = match.group(1)
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    print(text.strip())
else:
    print("NO ARTICLE FOUND")
    match2 = re.search(r'class="markdown">(.*?)</div>', content, re.DOTALL)
    if match2:
        text = match2.group(1)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        print(text.strip())
    else:
        tags = re.findall(r'<(div|article|section|main)[^>]*class="([^"]*)"', content)
        print("Available classes:", tags[:20])
