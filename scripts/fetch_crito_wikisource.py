#!/usr/bin/env python3
"""Fetch complete Greek text of Plato's Crito from Wikisource (Burnet 1903 ed.)"""

import urllib.request
import re
import html as htmlmod

def fetch_and_process():
    # Fetch full Wikisource page
    url = 'https://el.wikisource.org/wiki/%CE%9A%CF%81%CE%AF%CF%84%CF%89%CE%BD'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    raw_html = resp.read().decode('utf-8', errors='replace')

    # Extract the main content area
    content_start = raw_html.find('prp-pages-output')
    content_end = raw_html.find('class="printfooter"')
    if content_end < 0:
        content_end = len(raw_html)

    content = raw_html[content_start:content_end]

    # Replace <br> and block elements with newlines
    text = content
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'</div>', '\n', text)
    text = re.sub(r'<div[^>]*>', '', text)

    # Convert Stephanus page markers to visible labels
    def replace_stephanus(match):
        full = match.group(0)
        num_match = re.search(r'id="p\.(\d+[a-e]?)"', full)
        if num_match:
            num = num_match.group(1)
            # Only use lettered markers (43a, 43b, etc.), skip bare page nums
            if re.match(r'^\d+$', num):
                return ''
            return '\n[' + num + '] '
        return ''

    text = re.sub(r'<span[^>]*id="p\.\d+[a-e]?"[^>]*>.*?</span>', replace_stephanus, text)

    # Handle St.I markers - remove them
    text = re.sub(r'<span[^>]*id="St\.[^"]*"[^>]*>.*?</span>', '', text)

    # Remove page number spans
    text = re.sub(r'<span[^>]*class="pagenum"[^>]*>.*?</span>', '', text)

    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    text = htmlmod.unescape(text)

    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Remove the initial wrapping text
    if text.startswith('prp-pages-output'):
        text = text[text.find('\n'):]
    text = text.strip()

    # Build the final organized markdown
    lines = text.split('\n')
    output = []
    output.append('# \u039a\u03c1\u03af\u03c4\u03c9\u03bd')
    output.append('')
    output.append('Plat\u00f3, *Crit\u00f3* (ed. John Burnet, 1903, Oxford Classical Texts)')
    output.append('')
    output.append('Font: [Greek Wikisource](https://el.wikisource.org/wiki/%CE%9A%CF%81%CE%AF%CF%84%CF%89%CE%BD)')
    output.append('')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for Stephanus marker at start of line
        m = re.match(r'^\[(\d+[a-e])\]\s*(.*)', line)
        if m:
            section = m.group(1)
            rest = m.group(2).strip()
            output.append('## ' + section)
            output.append('')
            if rest:
                output.append(rest)
                output.append('')
        elif line in ('\u039a\u03a1\u0399\u03a4\u03a9\u039d',
                      '\u03a3\u03a9\u039a\u03a1\u0391\u03a4\u0397\u03a3\u039a\u03a1\u0399\u03a4\u03a9\u039d',
                      '\u03a3\u03a9\u039a\u03a1\u0391\u03a4\u0397\u03a3 \u039a\u03a1\u0399\u03a4\u03a9\u039d'):
            continue
        else:
            output.append(line)
            output.append('')

    final = '\n'.join(output)
    final = re.sub(r'\n{3,}', '\n\n', final)
    final = final.strip() + '\n'

    # Write to file
    outpath = '/home/jo/biblioteca-universal-arion/obres/plato/criton/original.md'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(final)

    # Report stats
    sections = re.findall(r'^## (\d+[a-e])$', final, re.MULTILINE)
    print("Written {} chars to {}".format(len(final), outpath))
    print("Stephanus sections: {}".format(len(sections)))
    print("Sections: {}".format(', '.join(sections)))
    print()
    print("First 500 chars:")
    print(final[:500])
    print()
    print("Last 500 chars:")
    print(final[-500:])

if __name__ == '__main__':
    fetch_and_process()
