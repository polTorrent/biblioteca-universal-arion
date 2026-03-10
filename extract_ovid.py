#!/usr/bin/env python3
"""Extract selected myths from Ovid's Metamorphoses via The Latin Library."""

import urllib.request
import re
import sys


def fetch_book(book_num):
    url = f"https://www.thelatinlibrary.com/ovid/ovid.met{book_num}.shtml"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    html = resp.read().decode("latin-1")
    return html


def html_to_lines(html):
    html = re.sub(r"<head>.*?</head>", "", html, flags=re.DOTALL)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "", html)
    html = html.replace("&nbsp;", " ")
    html = html.replace("&amp;", "&")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    lines = html.split("\n")
    lines = [l.strip() for l in lines]
    return lines


def get_verse_lines(lines):
    """Parse lines into (ovid_line_number, text) tuples.

    The Latin Library format: each verse line may have a line number
    appended at the end (every 5 lines typically). We count verses
    sequentially starting from 1.
    """
    verses = []
    started = False

    for line in lines:
        if not line:
            continue
        # Skip header/footer
        if "METAMORPHOSEON" in line or "LIBER" in line:
            started = True
            continue
        if "The Latin Library" in line or "Ovid" == line.strip():
            continue
        if not started:
            continue

        # Check if this line has an Ovid line number appended at the end
        # Pattern: text followed by spaces and a number
        m = re.match(r"^(.+?)\s{2,}(\d+)\s*$", line)
        if m:
            text = m.group(1).strip()
            # The number is the Ovid line number for this or nearby line
            verses.append(text)
        else:
            # Pure line number alone on a line - skip
            if re.match(r"^\d+$", line):
                continue
            verses.append(line)

    return verses


def extract_range(verses, start, end):
    """Extract verses from start to end (1-indexed, Ovid line numbers).
    Verses list is 0-indexed where index 0 = line 1."""
    return verses[start - 1 : end]


def format_passage(verses, start_line):
    """Format verses with line numbers every 5 lines."""
    result = []
    for i, verse in enumerate(verses):
        ovid_num = start_line + i
        if ovid_num % 5 == 0:
            # Right-align line number
            result.append(f"{verse}    {ovid_num}")
        else:
            result.append(verse)
    return "\n".join(result)


if __name__ == "__main__":
    # Fetch all needed books
    print("Fetching books...", file=sys.stderr)

    books = {}
    for b in [1, 3, 4, 8, 10]:
        print(f"  Book {b}...", file=sys.stderr)
        html = fetch_book(b)
        lines = html_to_lines(html)
        verses = get_verse_lines(lines)
        books[b] = verses
        print(f"    Total verses: {len(verses)}", file=sys.stderr)

    # Verify by checking known line numbers
    # Book I line 452 should start "Primus amor Phoebi Daphne Peneia"
    print(f"\nVerification:", file=sys.stderr)
    print(f"  Book I, line 452: {books[1][451]}", file=sys.stderr)
    print(f"  Book I, line 567: {books[1][566]}", file=sys.stderr)

    # Extract passages
    myths = [
        (1, 452, 567, "Apollo i Dafne", "Apollo et Daphne", "I"),
        (4, 55, 166, "Piram i Tisbe", "Pyramus et Thisbe", "IV"),
        (3, 339, 510, "Eco i Narcis", "Echo et Narcissus", "III"),
        (8, 183, 235, "Dedal i Icar", "Daedalus et Icarus", "VIII"),
        (10, 1, 85, "Orfeu i Euridice", "Orpheus et Eurydice", "X"),
    ]

    for book, start, end, cat_name, lat_name, roman in myths:
        passage = extract_range(books[book], start, end)
        formatted = format_passage(passage, start)
        print(f"\n=== {cat_name} ({lat_name}) - Book {roman}, {start}-{end} ===")
        print(f"Lines extracted: {len(passage)}", file=sys.stderr)
        print(formatted)
        print(f"=== END ===")
