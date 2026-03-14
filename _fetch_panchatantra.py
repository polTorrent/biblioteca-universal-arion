#!/usr/bin/env python3
"""Fetch Panchatantra Book I from Wikisource."""
import urllib.request
import re
import html as html_mod

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode()

# Step 1: Find the table of contents
base = "https://en.wikisource.org"
toc_url = base + "/wiki/The_Panchatantra_(Purnabhadra%27s_Recension_of_1199_CE)"
html = fetch(toc_url)

# Find all subpage links
links = re.findall(r'href="(/wiki/The_Panchatantra_\(Purnabhadra[^"]*)"', html)
unique_links = sorted(set(links))
print("Found links:")
for l in unique_links:
    print(f"  {l}")

# Find Book I links
book1_links = [l for l in unique_links if "Book_I" in l or "Book_1" in l or "book_1" in l.lower()]
print(f"\nBook I links: {book1_links}")

# If no specific Book I link, check for numbered chapters
if not book1_links:
    # Try the main page content for TOC structure
    # Look for links containing numbers or chapter references
    all_links = re.findall(r'href="(/wiki/The_Panchatantra[^"]*)"[^>]*>([^<]+)', html)
    print("\nAll Panchatantra links with text:")
    for href, text in all_links:
        print(f"  {text.strip()} -> {href}")
