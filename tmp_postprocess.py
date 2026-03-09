import re

with open('/home/jo/biblioteca-universal-arion/tmp_sonnets.md') as f:
    text = f.read()

text = re.sub(r'(## [^\n]+\n)\n\n', r'\1\n', text)
text = text.rstrip() + '\n'

with open('/home/jo/biblioteca-universal-arion/tmp_sonnets_final.md', 'w') as f:
    f.write(text)

print('Done')
