import re

with open('obres/teatre/chikamatsu-monzaemon/sonezaki-shinju/_source.html', 'r') as f:
    html = f.read()

match = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', html, re.DOTALL)
if not match:
    match = re.search(r'<div class="mw-parser-output">(.*)', html, re.DOTALL)

if match:
    content = match.group(1)
    text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<sup[^>]*>.*?</sup>', '', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&[a-z]+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l.strip() for l in text.split('\n')]
    result = '\n'.join(lines).strip()
    print(result[:5000])
    print('---END PREVIEW---')
    print(f'Total chars: {len(result)}')

    with open('obres/teatre/chikamatsu-monzaemon/sonezaki-shinju/_extracted.txt', 'w') as f:
        f.write(result)
else:
    print('NO MATCH')
