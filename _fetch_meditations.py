#!/usr/bin/env python3
"""Download all 12 books of Meditations from Greek Wikisource and extract text."""
import os
import re
import time
import urllib.request
import urllib.parse

base_url = "https://el.wikisource.org/wiki/%CE%A4%CE%B1_%CE%B5%CE%B9%CF%82_%CE%B5%CE%B1%CF%85%CF%84%CF%8C%CE%BD/"
output_dir = "/home/jo/biblioteca-universal-arion"

for book_num in range(1, 13):
    url = f"{base_url}{book_num}"
    outfile = os.path.join(output_dir, f"_wikisource_book_{book_num}.html")
    print(f"Downloading Book {book_num} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
            with open(outfile, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Saved to {outfile} ({len(html)} bytes)")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1)  # Be polite

print("\nDone downloading all books.")
