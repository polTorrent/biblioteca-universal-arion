#!/usr/bin/env python3
"""Fetch Makura no Sōshi sections from Japanese Wikisource."""
import re
import html
import urllib.request
import urllib.parse
import time

BASE = "https://ja.wikisource.org/wiki/"
PAGE = "%E6%9E%95%E8%8D%89%E5%AD%90_(Wikisource)"

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')

def extract_text(html_content):
    """Extract main text from Wikisource HTML."""
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)

    # Find the mw-parser-output div
    match = re.search(r'<div class="mw-parser-output">(.*?)</div>\s*<!--', text, re.DOTALL)
    if match:
        text = match.group(1)

    # Remove HTML tags but keep text
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)

    # Clean up whitespace
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if l and not l.startswith('[') and 'Wikipedia' not in l
             and 'Wikisource' not in l and 'カテゴリ' not in l and '即時削除' not in l
             and 'トークページ' not in l and '免責事項' not in l]
    return '\n'.join(lines)

# First, get the main page which may contain text directly
print("Fetching main page...")
main_html = fetch(f"{BASE}{PAGE}")

# Extract section URLs
section_links = re.findall(
    r'href="(/wiki/%E6%9E%95%E8%8D%89%E5%AD%90_\(Wikisource\)/[^"]+)"',
    main_html
)
section_links = list(dict.fromkeys(section_links))  # deduplicate preserving order

# Map section number in kanji to arabic
kanji_nums = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17,
    '十八': 18, '十九': 19, '二十': 20, '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24,
    '二十五': 25, '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30,
    '三十四': 34, '九十二': 92, '百五十一': 151, '二百六十九': 269,
}

sections = {}
for link in section_links:
    url = f"https://ja.wikisource.org{link}"
    # Extract section name
    section_name = urllib.parse.unquote(link.split('/')[-1])

    # Extract number
    m = re.search(r'第(.+)段', section_name)
    if m:
        num_str = m.group(1)
        num = kanji_nums.get(num_str, 0)
    else:
        num = 0

    print(f"  Fetching section {section_name} (#{num})...")
    try:
        section_html = fetch(url)
        text = extract_text(section_html)
        if text.strip():
            sections[num] = (section_name, text.strip())
        time.sleep(0.5)
    except Exception as e:
        print(f"    Error: {e}")

# Also extract text from the main page itself
main_text = extract_text(main_html)

# Build the output
output_lines = []
output_lines.append("# 枕草子 (Makura no Sōshi / El llibre del coixí)")
output_lines.append("")
output_lines.append("**Autora**: 清少納言 (Sei Shōnagon)")
output_lines.append("**Època**: c. 1002 dC (període Heian)")
output_lines.append("**Llengua**: japonès clàssic")
output_lines.append("**Font**: [Wikisource japonès](https://ja.wikisource.org/wiki/%E6%9E%95%E8%8D%89%E5%AD%90_(Wikisource))")
output_lines.append("")
output_lines.append("---")
output_lines.append("")

# Sort and add sections
for num in sorted(sections.keys()):
    name, text = sections[num]
    output_lines.append(f"## {name}")
    output_lines.append("")
    output_lines.append(text)
    output_lines.append("")
    output_lines.append("---")
    output_lines.append("")

output = '\n'.join(output_lines)

outpath = '/home/jo/biblioteca-universal-arion/obres/assaig/sei-shonagon/makura-no-soshi-el-llibre-del-coixi/original.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\nWritten {len(output)} chars, {len(sections)} sections to {outpath}")
