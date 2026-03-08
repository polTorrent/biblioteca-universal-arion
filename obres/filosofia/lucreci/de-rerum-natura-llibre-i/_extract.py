import re
import html as htmlmod

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/lucreci/de-rerum-natura-llibre-i/_raw.html', 'r') as f:
    raw = f.read()

body_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL)
text = body_match.group(1) if body_match else raw

text = re.sub(r'<p class=pagehead>.*?</p>', '', text, flags=re.DOTALL)
text = re.sub(r'<table.*?</table>', '', text, flags=re.DOTALL)
text = re.sub(r'<br\s*/?>', '\n', text)
text = re.sub(r'</?p[^>]*>', '\n', text)
text = re.sub(r'<[^>]+>', '', text)
text = htmlmod.unescape(text)

lines = [l.strip() for l in text.split('\n')]
while lines and not lines[0]:
    lines.pop(0)
while lines and not lines[-1]:
    lines.pop()

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/lucreci/de-rerum-natura-llibre-i/original.md', 'w') as f:
    f.write('# De rerum natura — Liber I\n\n')
    f.write('**Titus Lucretius Carus** (c. 99–55 aC)\n\n')
    f.write('---\n\n')
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                f.write('\n')
                prev_empty = True
        else:
            f.write(line + '\n')
            prev_empty = False

print('Done. Lines:', len(lines))
