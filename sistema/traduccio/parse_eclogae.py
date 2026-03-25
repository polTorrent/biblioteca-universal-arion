#!/usr/bin/env python3
"""Parse downloaded HTML eclogues into original.md."""
import html
import re
import sys
from pathlib import Path


def parse_eclogae(base: Path) -> str:
    """Parseja els HTML d'eclogues i retorna el contingut Markdown."""
    result: list[str] = [
        "# Bucòliques (Eclogae)",
        "",
        "**Publius Vergilius Maro**",
        "",
        "Text llatí original (domini públic). Font: The Latin Library.",
        "",
        "---",
        "",
    ]

    for i in range(1, 11):
        f = base / f"raw{i}.html"
        if not f.exists():
            print(f"Avís: {f} no existeix, s'omet.", file=sys.stderr)
            continue
        raw = f.read_text(encoding="latin-1")

        title_m = re.search(r"<title>\s*(.*?)\s*</title>", raw, re.S)
        title = title_m.group(1).strip() if title_m else f"ECLOGA {i}"

        body_m = re.search(r"<body>(.*?)</body>", raw, re.S | re.I)
        if not body_m:
            print(f"Avís: {f} no té <body>, s'omet.", file=sys.stderr)
            continue
        body = body_m.group(1)

        body = re.sub(r'<p class="pagehead">.*?</p>', "", body, flags=re.S)
        body = re.sub(r'<p class="internal_navigation">.*?</p>', "", body, flags=re.S)
        body = re.sub(r'<p class="border">.*?</p>', "", body, flags=re.S)
        body = re.sub(r"</?font[^>]*>", "", body, flags=re.I)
        body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
        body = re.sub(r"<[^>]+>", "", body)

        body = html.unescape(body)

        lines = [line.strip() for line in body.split("\n") if line.strip()]
        text = "\n".join(lines)

        result.append(f"## {title}")
        result.append("")
        result.append(text)
        result.append("")
        result.append("---")
        result.append("")

    return "\n".join(result)


if __name__ == "__main__":
    base = Path("obres/poesia/virgili/bucoliques")
    output = parse_eclogae(base)
    (base / "original.md").write_text(output, encoding="utf-8")
    print(f"Generated original.md: {len(output)} chars, {len(output.splitlines())} lines")
