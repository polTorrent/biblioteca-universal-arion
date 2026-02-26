#!/usr/bin/env python3
import html, re

with open('/home/jo/biblioteca-universal-arion/verwandlung_temp.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract body content
body = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
if body:
    text = body.group(1)
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
    text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)
    # Replace br and p with newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'</div>', '\n', text)
    text = re.sub(r'<h[1-6][^>]*>', '\n\n### ', text)
    text = re.sub(r'</h[1-6]>', '\n', text)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    # Clean up
    lines = text.split('\n')
    lines = [l.strip() for l in lines]
    # Remove empty lines at start
    while lines and not lines[0]:
        lines.pop(0)
    result = '\n'.join(lines)
    # Collapse multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    print(result[:2000])
    print('...')
    print(f'Total length: {len(result)} chars')
