import html, re

with open('obres/narrativa/vishnu-sharma/panchatantra-llibre-i/_temp.html') as f:
    content = f.read()

match = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', content, re.DOTALL)
if not match:
    match = re.search(r'<div id="mw-content-text"[^>]*>(.*?)<!--\s*NewPP', content, re.DOTALL)

if match:
    text = match.group(1)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines:
        print(l)
else:
    print('NO MATCH')
    if 'मित्रभेद' in content:
        idx = content.index('मित्रभेद')
        print(content[idx:idx+1000])
