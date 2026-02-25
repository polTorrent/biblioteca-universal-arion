#!/usr/bin/env python3
"""Fetch Marcus Aurelius Meditations from Greek Wikisource."""

import re
import html as htmlmod
import urllib.request
import urllib.parse
import sys
import time

BASE = "https://el.wikisource.org/wiki/"
PAGE = "%CE%A4%CE%B1_%CE%B5%CE%B9%CF%82_%CE%B5%CE%B1%CF%85%CF%84%CF%8C%CE%BD"

def fetch_book(book_num):
    url = f"{BASE}{PAGE}/{book_num}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching book {book_num}: {e}", file=sys.stderr)
        return None

    # Extract main content - try multiple patterns
    match = re.search(r'mw-parser-output"[^>]*>(.*?)<div class="printfooter"', data, re.DOTALL)
    if not match:
        match = re.search(r'mw-parser-output"[^>]*>(.*?)<!--\s*NewPP', data, re.DOTALL)
    if not match:
        match = re.search(r'mw-parser-output"[^>]*>(.*?)<noscript', data, re.DOTALL)
    if not match:
        match = re.search(r'mw-parser-output"[^>]*>(.*?)</div>\s*</div>\s*</div>', data, re.DOTALL)
    if not match:
        print(f"Content not found for book {book_num}", file=sys.stderr)
        # Debug: show what's near mw-parser-output
        idx = data.find("mw-parser-output")
        if idx >= 0:
            snippet = data[idx:idx+500]
            print(f"Debug snippet: {snippet[:300]}", file=sys.stderr)
        return None

    content = match.group(1)
    # Clean HTML
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'</p>', '\n', content)
    content = re.sub(r'<[^>]+>', '', content)
    content = htmlmod.unescape(content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    return content


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Fetch all books and print summary
        for i in range(1, 13):
            text = fetch_book(i)
            if text:
                lines = text.strip().split('\n')
                non_empty = [l for l in lines if l.strip()]
                print(f"Book {i}: {len(text)} chars, {len(non_empty)} non-empty lines")
                # Count sections (paragraphs starting with Greek text)
                print(f"  First 100 chars: {text[:100]}")
            else:
                print(f"Book {i}: FAILED")
            time.sleep(0.5)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        # Fetch all and save to file
        import os
        outpath = os.path.join(os.path.dirname(__file__), "wikisource_meditations.txt")
        with open(outpath, "w") as f:
            for i in range(1, 13):
                text = fetch_book(i)
                if text:
                    f.write(f"\n## Book {i}\n\n")
                    f.write(text)
                    f.write("\n\n")
                    print(f"Book {i}: {len(text)} chars saved")
                else:
                    print(f"Book {i}: FAILED")
                time.sleep(0.5)
        print(f"Saved to {outpath}")
        return

    if len(sys.argv) > 1:
        book_num = int(sys.argv[1])
        text = fetch_book(book_num)
        if text:
            print(text)
        return

    for i in range(1, 13):
        print(f"\n{'='*60}")
        print(f"BOOK {i}")
        print(f"{'='*60}")
        text = fetch_book(i)
        if text:
            # Show first 500 chars and length
            print(text[:500])
            print(f"\n... [Total: {len(text)} chars]")
        time.sleep(1)  # Be polite


if __name__ == "__main__":
    main()
