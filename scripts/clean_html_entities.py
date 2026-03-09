#!/usr/bin/env python3
"""Clean HTML entities from original.md"""
import re
import sys

path = sys.argv[1]
with open(path, "r") as f:
    text = f.read()

text = text.replace("&nbsp;", " ").replace("&thinsp;", "").replace("&amp;", "&")
text = re.sub(r"&[a-z]+;", "", text)
text = re.sub(r"  +", " ", text)

with open(path, "w") as f:
    f.write(text)
print("OK - cleaned")
