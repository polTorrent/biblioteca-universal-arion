import re, html

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/boeci/de-consolatione-philosophiae-llibre-i/raw.html', 'r') as f:
    text = f.read()

match = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', text, re.DOTALL)
if not match:
    match = re.search(r'<div class="mw-parser-output">(.*?)</div>\s*<!--', text, re.DOTALL)

if match:
    content = match.group(1)
else:
    content = text

content = re.sub(r'<div class="catlinks.*?</div>', '', content, flags=re.DOTALL)
content = re.sub(r'<table.*?</table>', '', content, flags=re.DOTALL)
content = re.sub(r'<div class="mw-heading.*?</div>', '', content, flags=re.DOTALL)
content = re.sub(r'<br\s*/?>', '\n', content)
content = re.sub(r'</p>', '\n\n', content)
content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', content)
content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', content)
content = re.sub(r'<[^>]+>', '', content)
content = html.unescape(content)

lines = content.strip().split('\n')
cleaned = [line.strip() for line in lines]
result = '\n'.join(cleaned)
result = re.sub(r'\n{3,}', '\n\n', result)

print(result)
