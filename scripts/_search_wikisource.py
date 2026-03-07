#!/usr/bin/env python3
"""Search Wikisource for Plutarch's Peri Euthymias."""
import urllib.request
import re

url = "https://el.wikisource.org/w/index.php?search=%CE%A0%CE%B5%CF%81%CE%AF+%CE%B5%CF%85%CE%B8%CF%85%CE%BC%CE%AF%CE%B1%CF%82&title=Special%3ASearch&ns0=1"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
content = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
links = re.findall(
    r'class="mw-search-result-heading">.*?<a href="(/wiki/[^"]+)".*?title="([^"]+)"',
    content,
)
for href, title in links[:15]:
    print(f"{title}: https://el.wikisource.org{href}")
