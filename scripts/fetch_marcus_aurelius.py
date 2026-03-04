#!/usr/bin/env python3
"""Fetch Marcus Aurelius Meditations in original Ancient Greek from multiple sources."""

from __future__ import annotations

import html as html_mod
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

OUTPUT_DIR = str(Path(__file__).resolve().parent / "marcus_aurelius_greek")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def fetch_url(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL and return the HTML content."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def strip_html(html_text: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    text = re.sub(r'<br\s*/?>', '\n', html_text)
    text = re.sub(r'<p[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html_mod.unescape(text)
    # Clean up excessive whitespace but keep newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    text = re.sub(r' \n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ============================================================================
# SOURCE 1: Wikisource (el.wikisource.org)
# ============================================================================
def fetch_wikisource() -> str | None:
    print("=" * 70)
    print("SOURCE 1: Wikisource (el.wikisource.org)")
    print("=" * 70)

    # First, get the main page to find links to individual books
    main_url = "https://el.wikisource.org/wiki/Τα_εις_εαυτόν"
    print(f"Fetching main page: {main_url}")
    html = fetch_url(main_url)
    if not html:
        print("Failed to fetch Wikisource main page")
        return None

    # Save raw HTML for debugging
    with open(os.path.join(OUTPUT_DIR, "wikisource_main.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # Find links to individual books
    # Wikisource might have them as subpages or on one page
    book_links = re.findall(r'href="(/wiki/[^"]*εαυτόν[^"]*)"[^>]*>([^<]+)', html)
    print(f"Found {len(book_links)} links matching 'εαυτόν':")
    for href, text in book_links:
        print(f"  {text.strip()} -> {href}")

    # Also look for any book numbering patterns
    all_links = re.findall(r'href="(/wiki/[^"]+)"[^>]*>([^<]+)', html)
    book_pattern_links = []
    for href, text in all_links:
        t = text.strip()
        if any(x in t for x in ['Βιβλίο', 'βιβλίο', 'Βιβλ', 'Α΄', 'Β΄', 'Γ΄', 'Δ΄']):
            book_pattern_links.append((href, t))
            print(f"  BOOK: {t} -> {href}")

    # Check if text is directly on the main page (extract from content area)
    content_match = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', html, re.DOTALL)
    if content_match:
        content = content_match.group(1)
        text = strip_html(content)
        if len(text) > 500:
            print(f"\nFound text on main page: {len(text)} chars")
            print(f"Preview: {text[:500]}...")
            with open(os.path.join(OUTPUT_DIR, "wikisource_text.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            return text

    # Try individual book pages if the main page is just a TOC
    # Common Wikisource URL patterns
    book_urls_to_try = [
        # Pattern 1: /wiki/Τα_εις_εαυτόν/Βιβλίο_Α
        [f"https://el.wikisource.org/wiki/Τα_εις_εαυτόν/Βιβλίο_{num}"
         for num in ["Α", "Β", "Γ", "Δ", "Ε", "ΣΤ", "Ζ", "Η", "Θ", "Ι", "ΙΑ", "ΙΒ"]],
        # Pattern 2: /wiki/Τα_εις_εαυτόν/Α
        [f"https://el.wikisource.org/wiki/Τα_εις_εαυτόν/{num}"
         for num in ["Α", "Β", "Γ", "Δ", "Ε", "ΣΤ", "Ζ", "Η", "Θ", "Ι", "ΙΑ", "ΙΒ"]],
        # Pattern 3: Numbered
        [f"https://el.wikisource.org/wiki/Τα_εις_εαυτόν/{num}"
         for num in range(1, 13)],
    ]

    for pattern_set in book_urls_to_try:
        print(f"\nTrying URL pattern: {pattern_set[0]}")
        test_html = fetch_url(pattern_set[0])
        if test_html and "mw-parser-output" in test_html:
            print("  Pattern works! Fetching all books...")
            all_text = ""
            for i, url in enumerate(pattern_set):
                book_html = fetch_url(url)
                if book_html:
                    content = re.search(r'<div class="mw-parser-output">(.*?)<div class="printfooter"', book_html, re.DOTALL)
                    if content:
                        text = strip_html(content.group(1))
                        if len(text) > 100:
                            all_text += f"\n\n{'='*60}\nBook {i+1}\n{'='*60}\n{text}"
                            print(f"  Book {i+1}: {len(text)} chars")
                time.sleep(0.5)
            if all_text:
                with open(os.path.join(OUTPUT_DIR, "wikisource_text.txt"), "w", encoding="utf-8") as f:
                    f.write(all_text)
                return all_text
        elif test_html:
            print("  Page exists but no content found")
        else:
            print("  Pattern doesn't work")

    # Try the Wikisource API
    print("\nTrying Wikisource API...")
    api_url = "https://el.wikisource.org/w/api.php?action=parse&page=Τα_εις_εαυτόν&prop=text&format=json"
    api_html = fetch_url(api_url)
    if api_html:
        try:
            data = json.loads(api_html)
            if "parse" in data and "text" in data["parse"]:
                text = strip_html(data["parse"]["text"]["*"])
                print(f"API returned {len(text)} chars")
                if len(text) > 500:
                    with open(os.path.join(OUTPUT_DIR, "wikisource_api_text.txt"), "w", encoding="utf-8") as f:
                        f.write(text)
                    # Check for subpages
                    subpage_links = re.findall(r'href="[^"]*(/wiki/Τα_εις_εαυτόν/[^"]+)"', data["parse"]["text"]["*"])
                    print(f"Found subpage links: {subpage_links}")
                    return text
        except json.JSONDecodeError:
            print("  API returned non-JSON response")

    return None


# ============================================================================
# SOURCE 2: Perseus Digital Library
# ============================================================================
def fetch_perseus() -> str | None:
    print("\n" + "=" * 70)
    print("SOURCE 2: Perseus Digital Library")
    print("=" * 70)

    base_url = "https://www.perseus.tufts.edu/hopper/text"

    all_text = ""

    for book_num in range(1, 13):
        print(f"\nFetching Book {book_num}...")
        # Perseus URL pattern for Marcus Aurelius
        url = f"{base_url}?doc=Perseus%3Atext%3A2008.01.0641%3Abook%3D{book_num}"
        html = fetch_url(url, timeout=60)

        if not html:
            print(f"  Failed to fetch book {book_num}")
            continue

        # Extract the Greek text from the page
        # Perseus puts text in the text_container div
        text_container = re.search(r'class="text_container"[^>]*>(.*?)</div>\s*(?:</div>|<div class="[^"]*side)', html, re.DOTALL)
        if not text_container:
            # Try broader pattern
            text_container = re.search(r'<div\s+class="text_container"[^>]*>(.*?)</div>', html, re.DOTALL)

        if text_container:
            text = strip_html(text_container.group(1))
            if len(text) > 50:
                all_text += f"\n\n{'='*60}\nΒΙΒΛΙΟΝ {book_num}\n{'='*60}\n{text}"
                print(f"  Found {len(text)} chars")
            else:
                print(f"  Text too short: {text[:100]}")
        else:
            # Try to find any Greek text on the page
            # Look for the main content area
            main = re.search(r'<div id="main_col">(.*?)<div id="footer"', html, re.DOTALL)
            if main:
                # Find Greek text sections
                greek = re.findall(r'<span class="greek"[^>]*>(.*?)</span>', main.group(1), re.DOTALL)
                if greek:
                    combined = "\n".join(strip_html(g) for g in greek if strip_html(g))
                    all_text += f"\n\n{'='*60}\nΒΙΒΛΙΟΝ {book_num}\n{'='*60}\n{combined}"
                    print(f"  Found {len(combined)} chars in Greek spans")
                else:
                    # Just extract everything from the reading area
                    reading = re.search(r'<td class="(?:text|reading)"[^>]*>(.*?)</td>', main.group(1), re.DOTALL)
                    if reading:
                        text = strip_html(reading.group(1))
                        all_text += f"\n\n{'='*60}\nΒΙΒΛΙΟΝ {book_num}\n{'='*60}\n{text}"
                        print(f"  Found {len(text)} chars in reading area")

        # Try chapter-by-chapter if whole-book doesn't work
        if not text_container:
            print(f"  Trying chapter-by-chapter for book {book_num}...")
            book_text = ""
            for ch in range(1, 100):  # Max chapters
                ch_url = f"{base_url}?doc=Perseus%3Atext%3A2008.01.0641%3Abook%3D{book_num}%3Achapter%3D{ch}"
                ch_html = fetch_url(ch_url, timeout=30)
                if not ch_html or "The document you requested" in ch_html:
                    break
                # Extract text
                ch_text_match = re.search(r'class="text_container"[^>]*>(.*?)</div>', ch_html, re.DOTALL)
                if ch_text_match:
                    ch_text = strip_html(ch_text_match.group(1))
                    if ch_text:
                        book_text += f"\n[{ch}] {ch_text}"
                time.sleep(0.3)

            if book_text:
                all_text += f"\n\n{'='*60}\nΒΙΒΛΙΟΝ {book_num}\n{'='*60}\n{book_text}"
                print(f"  Found {len(book_text)} chars across chapters")

        time.sleep(1)

    if all_text:
        with open(os.path.join(OUTPUT_DIR, "perseus_text.txt"), "w", encoding="utf-8") as f:
            f.write(all_text)
        print(f"\nTotal Perseus text: {len(all_text)} chars")

    return all_text or None


# ============================================================================
# SOURCE 3: Project Gutenberg
# ============================================================================
def fetch_gutenberg() -> str | None:
    print("\n" + "=" * 70)
    print("SOURCE 3: Project Gutenberg")
    print("=" * 70)

    # Search for Marcus Aurelius on Gutenberg
    search_url = "https://www.gutenberg.org/ebooks/search/?query=marcus+aurelius+meditations"
    print(f"Searching: {search_url}")
    search_html = fetch_url(search_url)

    if search_html:
        # Find ebook links
        books = re.findall(r'href="/ebooks/(\d+)"[^>]*>([^<]+)', search_html)
        print(f"Found {len(books)} results:")
        for ebook_id, title in books[:20]:
            print(f"  #{ebook_id}: {title}")

    # Known Gutenberg ID for Greek Meditations: try 2680 (English) and search for Greek
    # The Greek text might be at different IDs
    greek_candidates = ["55317", "2680"]  # Try known IDs

    for ebook_id in greek_candidates:
        print(f"\nTrying Gutenberg #{ebook_id}...")
        # Try plain text version
        txt_url = f"https://www.gutenberg.org/files/{ebook_id}/{ebook_id}-0.txt"
        text = fetch_url(txt_url)
        if not text:
            txt_url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"
            text = fetch_url(txt_url)

        if text:
            # Check if it contains Greek characters
            greek_chars = len(re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]', text[:5000]))
            print(f"  Greek chars in first 5000: {greek_chars}")
            print(f"  Total length: {len(text)}")
            print(f"  Preview: {text[:500]}")

            if greek_chars > 50:
                with open(os.path.join(OUTPUT_DIR, f"gutenberg_{ebook_id}.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
                return text

    # Also try the raw Greek text from a known mirror
    print("\nTrying alternative sources...")
    alt_urls = [
        "https://www.gutenberg.org/ebooks/55317",  # Possible Greek text
    ]
    for url in alt_urls:
        alt_html = fetch_url(url)
        if alt_html:
            # Find download links
            downloads = re.findall(r'href="([^"]+\.txt[^"]*)"', alt_html)
            print(f"  Downloads from {url}: {downloads[:10]}")

    return None


# ============================================================================
# SOURCE 4: Alternative - Sacred Texts / other archives
# ============================================================================
def fetch_alternative() -> str | None:
    print("\n" + "=" * 70)
    print("SOURCE 4: Alternative sources")
    print("=" * 70)

    # Try Internet Archive / other sources
    urls = [
        # Hathi Trust
        "https://catalog.hathitrust.org/api/volumes/brief/oclc/3685919.json",
        # Try a direct raw text from a known academic source
        "https://el.wikisource.org/w/index.php?title=Τα_εις_εαυτόν&action=raw",
    ]

    for url in urls:
        print(f"\nTrying: {url}")
        text = fetch_url(url)
        if text:
            greek_chars = len(re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]', text[:10000]))
            print(f"  Response length: {len(text)}, Greek chars in first 10k: {greek_chars}")
            if greek_chars > 100:
                with open(os.path.join(OUTPUT_DIR, "alternative_text.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
                return text
            elif len(text) < 2000:
                print(f"  Content: {text[:500]}")

    return None


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching Marcus Aurelius - Τὰ εἰς ἑαυτόν (Meditations) in original Ancient Greek")
    print("=" * 70)

    ws_text = fetch_wikisource()
    perseus_text = fetch_perseus()
    gutenberg_text = fetch_gutenberg()
    alt_text = fetch_alternative()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Wikisource:  {'YES' if ws_text else 'NO'} - {len(ws_text) if ws_text else 0} chars")
    print(f"Perseus:     {'YES' if perseus_text else 'NO'} - {len(perseus_text) if perseus_text else 0} chars")
    print(f"Gutenberg:   {'YES' if gutenberg_text else 'NO'} - {len(gutenberg_text) if gutenberg_text else 0} chars")
    print(f"Alternative: {'YES' if alt_text else 'NO'} - {len(alt_text) if alt_text else 0} chars")
    print(f"\nOutput directory: {OUTPUT_DIR}")
