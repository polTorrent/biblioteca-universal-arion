#!/usr/bin/env python3
"""Fetch Plutarch's Peri Euthymias from Wikisource."""
import urllib.request
import html
import re
import sys
import json

URLS = [
    ("el.wikisource", "https://el.wikisource.org/wiki/%CE%A0%CE%B5%CF%81%CE%AF_%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82"),
    ("el.wikisource_plutarc", "https://el.wikisource.org/wiki/%CE%A0%CE%BB%CE%BF%CF%8D%CF%84%CE%B1%CF%81%CF%87%CE%BF%CF%82/%CE%97%CE%B8%CE%B9%CE%BA%CE%AC/%CE%A0%CE%B5%CF%81%CE%AF_%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82"),
    ("grc.wikisource", "https://el.wikisource.org/w/index.php?search=%CE%A0%CE%B5%CF%81%CE%AF+%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82&title=Special%3ASearch&ns0=1"),
    ("perseus", "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A2008.01.0371"),
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except Exception as e:
        return f"ERROR: {e}"

def extract_text(content):
    match = re.search(r'mw-parser-output[^>]*>(.*?)(?:<div class="printfooter"|<div class="catlinks")', content, re.DOTALL)
    if not match:
        match = re.search(r'mw-content-text[^>]*>(.*?)(?:<div class="printfooter"|<div class="catlinks")', content, re.DOTALL)
    if match:
        text = match.group(1)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text.strip())
        return text
    return None

for name, url in URLS:
    print(f"\n=== Trying {name} ===")
    content = fetch(url)
    if content.startswith("ERROR"):
        print(content)
        continue

    title = re.search(r"<title>(.*?)</title>", content)
    if title:
        print(f"Title: {title.group(1)}")

    text = extract_text(content)
    if text and len(text) > 500:
        print(f"Found text: {len(text)} chars")
        print(text[:500])
        print("...")

        with open("obres/assaig/plutarc/sobre-la-tranquillitat-de-lanima/_raw_text.txt", "w") as f:
            f.write(text)
        print(f"\nSaved to _raw_text.txt")
        sys.exit(0)
    else:
        print(f"Text too short or not found: {len(text) if text else 0} chars")
        if text:
            print(text[:300])

print("\nTrying Perseus...")
content = fetch("https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A2008.01.0371")
if not content.startswith("ERROR"):
    title = re.search(r"<title>(.*?)</title>", content)
    if title:
        print(f"Title: {title.group(1)}")
    print(f"Page length: {len(content)} chars")

    text = re.sub(r"<[^>]+>", "", content)
    text = html.unescape(text)
    greek = re.findall(r"[α-ωά-ώΑ-Ωἀ-ῷ\s,.·;]+", text)
    greek_text = "\n".join(g.strip() for g in greek if len(g.strip()) > 50)
    if greek_text and len(greek_text) > 500:
        print(f"Found Greek text: {len(greek_text)} chars")
        with open("obres/assaig/plutarc/sobre-la-tranquillitat-de-lanima/_raw_text.txt", "w") as f:
            f.write(greek_text)
        print("Saved to _raw_text.txt")
        sys.exit(0)

print("\n❌ Could not find the text automatically")
sys.exit(1)
