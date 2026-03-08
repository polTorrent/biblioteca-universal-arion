#!/usr/bin/env python3
"""Extract clean Latin text from Virgil Eclogues HTML files (raw1-10.html)."""

import re
import os

BASE = os.path.expanduser(
    "~/biblioteca-universal-arion/obres/poesia/virgili/bucoliques"
)

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def extract(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    # Remove footer
    html = re.sub(
        r'<div class="footer">.*?</div>', "", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Skip to content after internal_navigation
    m = re.search(r'<p class="internal_navigation">\s*', html, re.IGNORECASE)
    if m:
        html = html[m.end() :]

    # Mark speaker names (font size=3) before stripping tags
    def mark_speaker(m: re.Match) -> str:
        name = m.group(1).strip()
        return "\n\nSPKR_" + name + "_SPKR\n\n"

    html = re.sub(
        r"&nbsp;[&nbsp;\s]*<(?:font|FONT)\s+[Ss]ize\s*=\s*3\s*>(.*?)</(?:font|FONT)>",
        mark_speaker,
        html,
    )

    # Remove line numbers (font size=2 with digits)
    html = re.sub(
        r"<(?:font|FONT)\s+[Ss]ize\s*=\s*2\s*>\s*\d+\s*</(?:font|FONT)>", "", html
    )

    # HTML entities
    html = html.replace("&nbsp;", " ")
    html = html.replace("&#151;", "\u2014")
    html = html.replace("&amp;", "&")

    # BR tags to newlines (also consume trailing whitespace/newline)
    html = re.sub(r"<[Bb][Rr]\s*/?>\s*", "\n", html)

    # Paragraph boundaries to newlines
    html = re.sub(r"</[Pp]>\s*<[Pp]\s*>", "\n", html)

    # Strip all remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Restore speaker markers
    html = re.sub(r"SPKR_(.*?)_SPKR", lambda m: m.group(1), html)

    # Process lines
    lines = html.split("\n")
    cleaned: list[str] = []
    for line in lines:
        line = re.sub(r"  +", " ", line).strip()
        # Skip leading blank lines
        if not line and not cleaned:
            continue
        # Skip footer remnants
        if line in ("Vergil", "The Latin Library", "The Classics Page"):
            continue
        # Skip page header
        if re.match(r"^P\.\s*VERGILI\s*MARONIS", line):
            continue
        cleaned.append(line)

    # Trim trailing blanks
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    # Collapse consecutive blank lines
    result: list[str] = []
    prev_blank = False
    for line in cleaned:
        if not line:
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            prev_blank = False
            result.append(line)

    return "\n".join(result)


def main() -> None:
    all_eclogues: list[tuple[int, str]] = []

    for i in range(1, 11):
        fp = os.path.join(BASE, f"raw{i}.html")
        if not os.path.exists(fp):
            print(f"WARNING: {fp} not found, skipping")
            continue

        text = extract(fp)
        all_eclogues.append((i, text))

        # Save individual file
        out = os.path.join(BASE, f"ecloga_{i}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")

        line_count = len(text.split("\n"))
        print(f"Eclogue {i}: {line_count} lines -> {out}")
        for pl in text.split("\n")[:3]:
            print(f"  {pl}")
        print()

    # Save combined markdown
    combined = os.path.join(BASE, "eclogae_latin.md")
    with open(combined, "w", encoding="utf-8") as f:
        f.write("# P. Vergili Maronis Bucolica\n\n")
        for i, text in all_eclogues:
            f.write(f"## Ecloga {ROMAN[i - 1]}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")

    print(f"Combined file saved to {combined}")


if __name__ == "__main__":
    main()
