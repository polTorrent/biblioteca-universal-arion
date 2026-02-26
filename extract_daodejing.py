#!/usr/bin/env python3
"""Extract and clean the Dao De Jing text from downloaded HTML."""

from html.parser import HTMLParser
import re

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_content = False
        self.skip = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if attrs_dict.get('id') == 'mw-content-text':
            self.in_content = True
        if tag in ('script', 'style', 'noscript'):
            self.skip = True
        if tag == 'br' and self.in_content:
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = False
        if tag == 'p' and self.in_content:
            self.text.append('\n')
        if tag in ('h2', 'h3'):
            self.text.append('\n')

    def handle_data(self, data):
        if self.in_content and not self.skip:
            self.text.append(data)

with open('/home/jo/biblioteca-universal-arion/daodejing_huijiao.html', 'r', encoding='utf-8') as f:
    html = f.read()

parser = TextExtractor()
parser.feed(html)
raw_text = ''.join(parser.text)

lines = raw_text.split('\n')

output_lines = []
in_chapters = False
for line in lines:
    line = line.strip()
    if not line:
        continue
    if line.startswith('\u2190') or line.startswith('\u53e4\u6587'):
        continue
    if '\u7ef4\u57fa\u767e\u79d1' in line or '\u59ca\u59b9\u8ba1\u5212' in line or '\u6570\u636e\u9879' in line:
        continue
    if '\u7248\u672c\u4fe1\u606f' in line:
        continue
    if '\u4f5c\u8005\uff1a\u8001\u5b50' in line:
        continue
    if line.startswith('\u8001\u5b50') and '\u9053\u5fb7\u7d93' in line:
        continue
    if '[\u7f16\u8f91]' in line:
        line = line.replace('[\u7f16\u8f91]', '').strip()
    if '\u68c0\u7d22\u81ea' in line or '\u5206\u7c7b\uff1a' in line or '\u516c\u6709\u9886\u57df' in line:
        break
    if '\u2191\u8fd4\u56de\u9876\u90e8' in line:
        break
    if line.startswith('Public domain'):
        break
    if '\u6b64\u9875\u9762' in line:
        break
    if '\u3000' == line:
        continue

    if line in ('\u9053\u7d93', '\u5fb7\u7d93'):
        output_lines.append('')
        output_lines.append('## ' + line)
        output_lines.append('')
        in_chapters = True
        continue

    chapter_match = re.match(r'^((?:\u4e00|\u4e8c|\u4e09|\u56db|\u4e94|\u516d|\u4e03|\u516b|\u4e5d|\u5341|\u4e8c\u5341|\u4e09\u5341|\u56db\u5341|\u4e94\u5341|\u516d\u5341|\u4e03\u5341|\u516b\u5341)+\u7ae0)$', line)
    if chapter_match:
        output_lines.append('')
        output_lines.append('### ' + line)
        output_lines.append('')
        in_chapters = True
        continue

    if in_chapters and line:
        output_lines.append(line)

result = '\n'.join(output_lines)
result = re.sub(r'\n{3,}', '\n\n', result)
result = result.strip()

with open('/home/jo/biblioteca-universal-arion/daodejing_clean.txt', 'w', encoding='utf-8') as f:
    f.write(result)

chapters = re.findall(r'### .+\u7ae0', result)
print(f"Chapters extracted: {len(chapters)}")
print(f"Total characters: {len(result)}")
print()
print("First 1500 chars:")
print(result[:1500])
print()
print("=== LAST 500 CHARS ===")
print(result[-500:])
