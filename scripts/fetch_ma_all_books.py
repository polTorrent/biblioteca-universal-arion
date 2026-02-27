#!/usr/bin/env python3
"""
Fetch ALL 12 books of Marcus Aurelius' Meditations (Τὰ εἰς ἑαυτόν)
in original Ancient Greek from multiple sources.

Sources tried in order:
1. Greek Wikisource (el.wikisource.org)
2. Perseus Digital Library
3. Project Gutenberg
"""

import re
import html as htmlmod
import urllib.request
import urllib.parse
import json
import os
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "marcus_aurelius_greek")

HEADERS: dict[str, str] = {"User-Agent": "Mozilla/5.0 (compatible; BibliotecaArion/1.0)"}

BOOK_NAMES: dict[int, str] = {
    1: "Α", 2: "Β", 3: "Γ", 4: "Δ", 5: "Ε", 6: "ΣΤ",
    7: "Ζ", 8: "Η", 9: "Θ", 10: "Ι", 11: "ΙΑ", 12: "ΙΒ"
}


def fetch_url(url: str, timeout: int = 60) -> str | None:
    """Fetch URL content."""
    try:
        parsed = urllib.parse.urlparse(url)
        encoded_path = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=')
        clean_url = urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, encoded_path,
            parsed.params, parsed.query, parsed.fragment
        ))
        req = urllib.request.Request(clean_url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def strip_html(html_text: str) -> str:
    """Remove HTML tags and clean up text."""
    # Remove style/script blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    # Remove header templates (navigation)
    text = re.sub(r'<table[^>]*id="headertemplate".*?</table>', '', text, flags=re.DOTALL)
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL)
    # Convert line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode entities
    text = htmlmod.unescape(text)
    text = re.sub(r'\xa0', ' ', text)
    # Clean CSS that leaks through
    text = re.sub(r'\.mw-parser-output[^{]*\{[^}]*\}', '', text)
    text = re.sub(r'@media[^{]*\{[^}]*\{[^}]*\}[^}]*\}', '', text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def count_greek(text: str) -> int:
    """Count Greek characters."""
    return len(re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]', text))


def _fetch_wikisource() -> dict[int, str]:
    """Fetch all books from Greek Wikisource."""
    print("=" * 70)
    print("SOURCE 1: WIKISOURCE (el.wikisource.org)")
    print("=" * 70)

    api_base = "https://el.wikisource.org/w/api.php"
    books: dict[int, str] = {}

    for book_num in range(1, 13):
        page_title = f"Τα εις εαυτόν/{book_num}"
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
            "disablelimitreport": "1",
        }
        api_url = f"{api_base}?{urllib.parse.urlencode(params)}"
        print(f"\nBook {book_num} (Βιβλίον {BOOK_NAMES[book_num]}): {page_title}")

        result = fetch_url(api_url)
        if result:
            try:
                data = json.loads(result)
                if "parse" in data:
                    html_content = data["parse"]["text"]["*"]
                    text = strip_html(html_content)
                    gc = count_greek(text)
                    print(f"  -> {len(text)} chars, {gc} Greek characters")
                    if gc > 100:
                        books[book_num] = text
                        book_file = os.path.join(OUTPUT_DIR, f"wikisource_book_{book_num:02d}.txt")
                        with open(book_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        print(f"  -> Saved: {book_file}")
                        print(f"  -> Preview: {text[:150]}...")
                    else:
                        print(f"  -> WARNING: Too few Greek chars. Preview: {text[:200]}")
                else:
                    err = data.get("error", {}).get("info", "unknown")
                    print(f"  -> API error: {err}")
            except json.JSONDecodeError as e:
                print(f"  -> JSON parse error: {e}")
        time.sleep(0.5)

    if books:
        output_lines = [
            "ΜΑΡΚΟΥ ΑΥΡΗΛΙΟΥ ΑΝΤΩΝΙΝΟΥ",
            "ΤΑ ΕΙΣ ΕΑΥΤΟΝ",
            "",
            "Πηγή: https://el.wikisource.org/wiki/Τα_εις_εαυτόν",
            "=" * 70,
        ]
        for book_num in sorted(books.keys()):
            output_lines.append("")
            output_lines.append(f"{'=' * 60}")
            output_lines.append(f"ΒΙΒΛΙΟΝ {BOOK_NAMES[book_num]} (Book {book_num})")
            output_lines.append(f"{'=' * 60}")
            output_lines.append("")
            output_lines.append(books[book_num])
        combined = '\n'.join(output_lines)
        combined_file = os.path.join(OUTPUT_DIR, "wikisource_all_books.txt")
        with open(combined_file, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"\n*** Wikisource: {len(books)}/12 books saved ({len(combined)} chars total)")

    return books


def _fetch_perseus() -> dict[int, str]:
    """Fetch all books from Perseus Digital Library."""
    print("\n" + "=" * 70)
    print("SOURCE 2: PERSEUS DIGITAL LIBRARY")
    print("=" * 70)

    books: dict[int, str] = {}

    for book_num in range(1, 13):
        print(f"\nBook {book_num} (Βιβλίον {BOOK_NAMES[book_num]}):")
        xml_url = (
            "https://www.perseus.tufts.edu/hopper/xmlchunk"
            f"?doc=Perseus%3Atext%3A2008.01.0641%3Abook%3D{book_num}"
        )

        html = fetch_url(xml_url, timeout=60)
        if html:
            text = strip_html(html)
            gc = count_greek(text)
            print(f"  -> {len(text)} chars, {gc} Greek characters")
            if gc > 100:
                books[book_num] = text
                book_file = os.path.join(OUTPUT_DIR, f"perseus_book_{book_num:02d}.txt")
                with open(book_file, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  -> Saved: {book_file}")
                print(f"  -> Preview: {text[:150]}...")
            else:
                print(f"  -> Not enough Greek. Preview: {text[:200]}")
        else:
            print("  -> Failed to fetch")
        time.sleep(1)

    if books:
        output_lines = [
            "ΜΑΡΚΟΥ ΑΥΡΗΛΙΟΥ ΑΝΤΩΝΙΝΟΥ",
            "ΤΑ ΕΙΣ ΕΑΥΤΟΝ",
            "",
            "Πηγή: Perseus Digital Library (A.S.L. Farquharson edition)",
            "Text ID: 2008.01.0641",
            "=" * 70,
        ]
        for book_num in sorted(books.keys()):
            output_lines.append("")
            output_lines.append(f"{'=' * 60}")
            output_lines.append(f"ΒΙΒΛΙΟΝ {BOOK_NAMES[book_num]} (Book {book_num})")
            output_lines.append(f"{'=' * 60}")
            output_lines.append("")
            output_lines.append(books[book_num])
        combined = '\n'.join(output_lines)
        combined_file = os.path.join(OUTPUT_DIR, "perseus_all_books.txt")
        with open(combined_file, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"\n*** Perseus: {len(books)}/12 books saved ({len(combined)} chars total)")

    return books


def _fetch_gutenberg() -> bool:
    """Fetch from Project Gutenberg. Returns True if Greek text found."""
    print("\n" + "=" * 70)
    print("SOURCE 3: PROJECT GUTENBERG")
    print("=" * 70)

    for ebook_id in ["55317", "2680"]:
        print(f"\nTrying Gutenberg #{ebook_id}...")
        for url_pattern in [
            f"https://www.gutenberg.org/ebooks/{ebook_id}.txt.utf-8",
            f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt",
            f"https://www.gutenberg.org/files/{ebook_id}/{ebook_id}-0.txt",
        ]:
            text = fetch_url(url_pattern, timeout=30)
            if text:
                gc = count_greek(text)
                print(f"  {url_pattern}: {len(text)} chars, {gc} Greek")
                if gc > 500:
                    gutenberg_file = os.path.join(OUTPUT_DIR, f"gutenberg_{ebook_id}.txt")
                    with open(gutenberg_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"  -> GREEK TEXT FOUND! Saved to {gutenberg_file}")
                    print(f"  -> Preview: {text[:300]}")
                    return True
                else:
                    print("  -> English translation (no Greek text)")
                    break

    print("  No Greek text found on Gutenberg")
    return False


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    wikisource_books = _fetch_wikisource()
    perseus_books = _fetch_perseus()
    gutenberg_found = _fetch_gutenberg()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(f"\nWikisource: {len(wikisource_books)}/12 books")
    total_ws_greek = 0
    for b in sorted(wikisource_books.keys()):
        gc = count_greek(wikisource_books[b])
        total_ws_greek += gc
        print(f"  Book {b:2d} ({BOOK_NAMES[b]:>2s}): {gc:5d} Greek chars")
    print(f"  Total: {total_ws_greek} Greek characters")

    print(f"\nPerseus: {len(perseus_books)}/12 books")
    total_p_greek = 0
    for b in sorted(perseus_books.keys()):
        gc = count_greek(perseus_books[b])
        total_p_greek += gc
        print(f"  Book {b:2d} ({BOOK_NAMES[b]:>2s}): {gc:5d} Greek chars")
    print(f"  Total: {total_p_greek} Greek characters")

    print(f"\nGutenberg: {'Found' if gutenberg_found else 'Not found'}")

    print(f"\nOutput directory: {OUTPUT_DIR}")
    for fname in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, fname)
        size = os.path.getsize(fpath)
        print(f"  {fname}: {size:,} bytes")


if __name__ == "__main__":
    main()
