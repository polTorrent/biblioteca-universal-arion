#!/usr/bin/env python3
"""Parse downloaded HTML eclogues into original.md."""
import re
from pathlib import Path

base = Path("obres/poesia/virgili/bucoliques")
result = []
result.append("# Bucòliques (Eclogae)")
result.append("")
result.append("**Publius Vergilius Maro**")
result.append("")
result.append("Text llatí original (domini públic). Font: The Latin Library.")
result.append("")
result.append("---")
result.append("")

for i in range(1, 11):
    f = base / f"raw{i}.html"
    html = f.read_text(encoding="latin-1")

    title_m = re.search(r"<title>\s*(.*?)\s*</title>", html, re.S)
    title = title_m.group(1).strip() if title_m else f"ECLOGA {i}"

    body_m = re.search(r"<body>(.*?)</body>", html, re.S | re.I)
    if not body_m:
        continue
    body = body_m.group(1)

    body = re.sub(r'<p class="pagehead">.*?</p>', "", body, flags=re.S)
    body = re.sub(r'<p class="internal_navigation">.*?</p>', "", body, flags=re.S)
    body = re.sub(r'<p class="border">.*?</p>', "", body, flags=re.S)
    body = re.sub(r"</?FONT[^>]*>", "", body, flags=re.I)
    body = re.sub(r"</?font[^>]*>", "", body, flags=re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "", body)

    body = body.replace("&nbsp;", " ")
    body = body.replace("&amp;", "&")
    body = body.replace("&lt;", "<")
    body = body.replace("&gt;", ">")

    lines = []
    for line in body.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    text = "\n".join(lines)

    result.append(f"## {title}")
    result.append("")
    result.append(text)
    result.append("")
    result.append("---")
    result.append("")

output = "\n".join(result)
(base / "original.md").write_text(output, encoding="utf-8")
print(f"Generated original.md: {len(output)} chars, {len(output.splitlines())} lines")
