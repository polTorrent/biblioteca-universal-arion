import html, re

with open("/home/jo/biblioteca-universal-arion/.tmp_sonezaki.html", "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', content, re.DOTALL)
if not match:
    match = re.search(r'<div class="mw-parser-output">(.*?)</div>\s*<!--\s*NewPP', content, re.DOTALL)

if match:
    text = match.group(1)
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div id="toc".*?</div>\s*</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    lines = text.split('\n')
    lines = [l.strip() for l in lines]
    result = []
    prev_empty = False
    for l in lines:
        if not l:
            if not prev_empty:
                result.append('')
            prev_empty = True
        else:
            result.append(l)
            prev_empty = False
    final = '\n'.join(result).strip()
    print(final[:500])
    print("---")
    print(f"Total chars: {len(final)}")
else:
    print("Content div not found")
    title_match = re.search(r'<title>(.*?)</title>', content)
    if title_match:
        print(f"Page title: {title_match.group(1)}")
