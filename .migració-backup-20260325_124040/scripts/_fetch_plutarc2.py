#!/usr/bin/env python3
"""Fetch Plutarch's Peri Euthymias from el.wikisource.org."""
import os
import sys
import urllib.error
import urllib.request
import html
import re

url = "https://el.wikisource.org/wiki/%CE%A0%CE%B5%CF%81%CE%AF_%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82_(%CE%A0%CE%BB%CE%BF%CF%8D%CF%84%CE%B1%CF%81%CF%87%CE%BF%CF%82)"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
    print(f"Error fetching URL: {e}", file=sys.stderr)
    sys.exit(1)

title = re.search(r"<title>(.*?)</title>", content)
if title:
    print(f"Title: {title.group(1)}")

# Extract main content
match = re.search(
    r'mw-parser-output[^>]*>(.*?)(?:<div class="printfooter"|<div class="catlinks"|<noscript>)',
    content,
    re.DOTALL,
)

if match:
    raw = match.group(1)
    # Remove style tags and their content
    raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL)
    # Remove script tags
    raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
    # Remove header template tables
    raw = re.sub(r'<table[^>]*headertemplate[^>]*>.*?</table>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<div[^>]*headertemplate[^>]*>.*?</div>', '', raw, flags=re.DOTALL)
    # Remove table of contents
    raw = re.sub(r'<div[^>]*id="toc"[^>]*>.*?</div>\s*</div>', '', raw, flags=re.DOTALL)
    # Remove sup/ref tags
    raw = re.sub(r'<sup[^>]*>.*?</sup>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<div class="reflist.*?</div>', '', raw, flags=re.DOTALL)
    # Remove navigation/edit links
    raw = re.sub(r'<div class="mw-heading.*?</div>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<span class="mw-editsection.*?</span>', '', raw, flags=re.DOTALL)
    # Convert paragraphs to double newlines
    raw = re.sub(r'</p>\s*<p[^>]*>', '\n\n', raw)
    raw = re.sub(r'<br\s*/?>', '\n', raw)
    # Keep heading tags but convert them
    raw = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', raw)
    raw = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', raw)
    # Remove remaining HTML
    text = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(text)
    # Remove CSS that leaked through
    text = re.sub(r'\.mw-parser-output[^}]+\}', '', text)
    text = re.sub(r'@media[^}]+\{[^}]*\}', '', text)
    text = re.sub(r'html\.[^}]+\}', '', text)
    # Clean whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    # Remove leading empty lines / CSS remnants
    lines = text.split('\n')
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        skip_prefixes = ('.', '@', '{', '}')
        if stripped and not any(stripped.startswith(p) for p in skip_prefixes) and len(stripped) > 5:
            # Check if it looks like Greek text or a heading
            if any(c in stripped for c in 'αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩάέήίόύώ') or stripped.startswith('#'):
                start = i
                break
    text = '\n'.join(lines[start:])
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    outpath = "obres/assaig/plutarc/sobre-la-tranquillitat-de-lanima/original.md"
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    header = "# Περὶ εὐθυμίας\n## Plutarc (Πλούταρχος)\n\n"
    header += "**Font**: [Wikisource (el)](https://el.wikisource.org/wiki/%CE%A0%CE%B5%CF%81%CE%AF_%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82_(%CE%A0%CE%BB%CE%BF%CF%8D%CF%84%CE%B1%CF%81%CF%87%CE%BF%CF%82))\n\n---\n\n"

    with open(outpath, "w") as f:
        f.write(header + text)

    print(f"\nSaved {len(text)} chars to {outpath}")
    print(f"\nFirst 1500 chars:\n{text[:1500]}")
    print(f"\nLast 500 chars:\n{text[-500:]}")
else:
    print("Could not extract text")
    print(f"Page length: {len(content)}")
