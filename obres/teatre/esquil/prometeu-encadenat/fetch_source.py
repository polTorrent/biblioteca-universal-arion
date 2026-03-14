#!/usr/bin/env python3
"""Fetch Prometheus Bound Greek text from Wikisource and Perseus."""
import json
import re
import html
import urllib.request
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def fetch_wikisource():
    """Fetch from Greek Wikisource API."""
    url = ("https://el.wikisource.org/w/api.php?action=parse"
           "&page=%CE%A0%CF%81%CE%BF%CE%BC%CE%B7%CE%B8%CE%B5%CF%8D%CF%82"
           "_%CE%94%CE%B5%CF%83%CE%BC%CF%8E%CF%84%CE%B7%CF%82"
           "&prop=text&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw_html = data.get("parse", {}).get("text", {}).get("*", "")
    if not raw_html:
        return None

    # Remove style/script blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', raw_html, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    # Convert <br> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)

    # Clean up
    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)

    return '\n'.join(lines)


def fetch_perseus():
    """Fetch from Perseus Digital Library."""
    base = "https://www.perseus.tufts.edu/hopper/xmlchunk?doc=Perseus%3Atext%3A1999.01.0010"
    req = urllib.request.Request(base, headers={"User-Agent": "BibliotecaArion/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        # Extract text content
        text = re.sub(r'<[^>]+>', '\n', raw)
        text = html.unescape(text)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"Perseus error: {e}")
        return None


def main():
    print("Fetching from Greek Wikisource...")
    text = fetch_wikisource()

    if not text or len(text) < 1000:
        print("Wikisource failed or too short, trying Perseus...")
        text = fetch_perseus()

    if not text or len(text) < 1000:
        print("ERROR: Could not fetch text from any source")
        return False

    # Write original.md
    output = os.path.join(OUTPUT_DIR, "original.md")
    with open(output, "w", encoding="utf-8") as f:
        f.write("# Προμηθεὺς Δεσμώτης\n")
        f.write("## Αἰσχύλος\n\n")
        f.write("*Font: Wikisource / Perseus Digital Library*\n")
        f.write("*Edició: Herbert Weir Smyth, Loeb Classical Library (1926)*\n\n")
        f.write("---\n\n")
        f.write(text)

    size = os.path.getsize(output)
    print(f"Written: {output} ({size} bytes)")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
