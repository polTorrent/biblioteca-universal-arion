#!/usr/bin/env python3
"""Fetch Marcus Aurelius Meditations in original Ancient Greek."""

import urllib.request
import urllib.parse
import re
import os
import json
import subprocess

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marcus_aurelius_greek")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def fetch_url(url: str, timeout: int = 30) -> str | None:
    """Fetch URL handling Unicode properly."""
    try:
        # Parse and re-encode the URL to handle Unicode
        parsed = urllib.parse.urlparse(url)
        encoded_path = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=')
        encoded_query = parsed.query  # already encoded or ASCII
        clean_url = urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, encoded_path,
            parsed.params, encoded_query, parsed.fragment
        ))
        req = urllib.request.Request(clean_url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def strip_html(html_text: str) -> str:
    """Remove HTML tags."""
    text = re.sub(r'<br\s*/?>', '\n', html_text)
    text = re.sub(r'<p[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;|&#160;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def count_greek(text: str, n: int = 5000) -> int:
    """Count Greek characters in first n chars."""
    return len(re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]', text[:n]))


def main() -> None:
    # ========================================================================
    # WIKISOURCE
    # ========================================================================
    print("=" * 70)
    print("WIKISOURCE")
    print("=" * 70)

    # Use the API to get raw wikitext
    api_base = "https://el.wikisource.org/w/api.php"

    # First get the main page
    params = {
        "action": "parse",
        "page": "Τα εις εαυτόν",
        "prop": "text|links",
        "format": "json"
    }
    api_url = f"{api_base}?{urllib.parse.urlencode(params)}"
    print(f"API URL: {api_url}")
    result = fetch_url(api_url)

    if result:
        try:
            data = json.loads(result)
            if "parse" in data:
                html_content = data["parse"]["text"]["*"]
                text = strip_html(html_content)
                print(f"Main page text length: {len(text)}")
                print(f"Greek chars: {count_greek(text)}")
                print(f"Preview:\n{text[:1000]}\n")

                with open(os.path.join(OUTPUT_DIR, "wikisource_main.txt"), "w",
                          encoding="utf-8") as f:
                    f.write(text)

                links = data["parse"].get("links", [])
                print(f"Links found: {len(links)}")
                for link in links:
                    title = link.get("*", "")
                    if "εαυτόν" in title or "εαυτ" in title:
                        print(f"  -> {title}")
            else:
                print(f"No parse data. Keys: {list(data.keys())}")
                if "error" in data:
                    print(f"Error: {data['error']}")
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            print(f"Response preview: {result[:500]}")

    # Try to get individual book pages
    print("\nFetching individual books from Wikisource...")
    book_names_to_try = [
        "Τα εις εαυτόν/Βιβλίο Α",
        "Τα εις εαυτόν/Βιβλίον Α",
        "Τα εις εαυτόν/Α",
        "Τα εις εαυτόν/1",
        "Τα εις εαυτόν/Βιβλίο 1",
        "Τα εις εαυτόν/Βιβλίο Πρώτο",
    ]

    for test_name in book_names_to_try:
        params = {
            "action": "parse",
            "page": test_name,
            "prop": "text",
            "format": "json"
        }
        api_url = f"{api_base}?{urllib.parse.urlencode(params)}"
        result = fetch_url(api_url)
        if result:
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                print(f"  ERROR: Invalid JSON for '{test_name}'")
                continue
            if "parse" in data:
                text = strip_html(data["parse"]["text"]["*"])
                gc = count_greek(text)
                print(f"  FOUND: '{test_name}' -> {len(text)} chars, {gc} Greek")
                if gc > 50:
                    print(f"  Preview: {text[:200]}")
                break
            elif "error" in data:
                print(
                    f"  NOT FOUND: '{test_name}'"
                    f" -> {data['error'].get('info', 'unknown error')}"
                )

    # ========================================================================
    # PERSEUS DIGITAL LIBRARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("PERSEUS DIGITAL LIBRARY")
    print("=" * 70)

    url = (
        "https://www.perseus.tufts.edu/hopper/text"
        "?doc=Perseus%3Atext%3A2008.01.0641%3Abook%3D1%3Achapter%3D1"
    )
    print(f"Fetching: {url}")
    html = fetch_url(url, timeout=60)

    if html:
        print(f"HTML length: {len(html)}")

        with open(os.path.join(OUTPUT_DIR, "perseus_book1_ch1.html"), "w",
                  encoding="utf-8") as f:
            f.write(html)

        m = re.search(r'class="text_container"[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            text = strip_html(m.group(1))
            print(f"text_container: {len(text)} chars, {count_greek(text)} Greek")
            print(f"Preview: {text[:500]}")

        greek_spans = re.findall(
            r'>([\u0370-\u03FF\u1F00-\u1FFF][^<]{5,})</(?:span|p|div|td)', html
        )
        if greek_spans:
            print(f"\nGreek spans found: {len(greek_spans)}")
            for i, span in enumerate(greek_spans[:5]):
                print(f"  {i}: {span[:200]}")

        reading_match = re.search(
            r'<table class="text_body"[^>]*>(.*?)</table>', html, re.DOTALL
        )
        if reading_match:
            reading_text = strip_html(reading_match.group(1))
            gc = count_greek(reading_text, 10000)
            print(f"\ntext_body table: {len(reading_text)} chars, {gc} Greek")
            if gc > 20:
                print(f"Preview: {reading_text[:500]}")

        all_text = strip_html(html)
        gc = count_greek(all_text, len(all_text))
        print(f"\nTotal Greek chars in page: {gc}")

        greek_passages = re.findall(
            r'((?:[\u0370-\u03FF\u1F00-\u1FFF]'
            r'[\u0370-\u03FF\u1F00-\u1FFF\s\.,;·\u0300-\u036F\u1DC0-\u1DFF]{10,})+)',
            all_text,
        )
        if greek_passages:
            print(f"\nGreek passages found: {len(greek_passages)}")
            for i, passage in enumerate(greek_passages[:5]):
                print(f"  Passage {i} ({len(passage)} chars): {passage[:300]}")
    else:
        print("Failed to fetch Perseus")

    # Now try the XML/text version from Perseus
    print("\nTrying Perseus XML API...")
    xml_url = (
        "https://www.perseus.tufts.edu/hopper/xmlchunk"
        "?doc=Perseus%3Atext%3A2008.01.0641%3Abook%3D1"
    )
    html = fetch_url(xml_url, timeout=60)
    if html:
        print(f"XML response: {len(html)} chars")
        gc = count_greek(html, len(html))
        print(f"Greek chars: {gc}")
        text = strip_html(html)
        if gc > 50:
            print(f"Preview: {text[:500]}")
        with open(os.path.join(OUTPUT_DIR, "perseus_xml_book1.txt"), "w",
                  encoding="utf-8") as f:
            f.write(text)

    # ========================================================================
    # PROJECT GUTENBERG
    # ========================================================================
    print("\n" + "=" * 70)
    print("PROJECT GUTENBERG")
    print("=" * 70)

    search_url = "https://www.gutenberg.org/ebooks/search/?query=marcus+aurelius"
    print(f"Searching: {search_url}")
    html = fetch_url(search_url, timeout=30)
    if html:
        books = re.findall(r'href="/ebooks/(\d+)"[^>]*>\s*([^<]+)', html)
        seen: set[str] = set()
        for ebook_id, title in books:
            if ebook_id not in seen:
                seen.add(ebook_id)
                print(f"  #{ebook_id}: {title.strip()}")

    for ebook_id in ["2680"]:
        print(f"\nFetching Gutenberg #{ebook_id} metadata...")
        meta_url = f"https://www.gutenberg.org/ebooks/{ebook_id}"
        html = fetch_url(meta_url, timeout=30)
        if html:
            downloads = re.findall(
                r'href="([^"]*(?:\.txt|\.htm)[^"]*)"[^>]*>([^<]+)', html
            )
            for href, label in downloads:
                print(f"  {label.strip()} -> {href}")

    # ========================================================================
    # ALTERNATIVE SOURCES
    # ========================================================================
    print("\n" + "=" * 70)
    print("ALTERNATIVE SOURCES")
    print("=" * 70)

    alt_urls = [
        ("https://www.mikrosapoplous.gr/marco/marco1a.html", "mikrosapoplous Book 1"),
        (
            "http://www.poesialatina.it/_ns/Greek/tt2/MarcusAurelius/MedBook01.html",
            "poesialatina Book 1",
        ),
        (
            "https://www.hs-augsburg.de/~harsch/graeca/Chronologia"
            "/S_post02/Marcus_Aurelius/mar_me01.html",
            "Bibliotheca Augustana Book 1",
        ),
    ]

    for url, name in alt_urls:
        print(f"\nTrying {name}: {url}")
        html = fetch_url(url, timeout=30)
        if html:
            text = strip_html(html)
            gc = count_greek(text, len(text))
            print(f"  Length: {len(text)}, Greek chars: {gc}")
            if gc > 100:
                print(f"  Preview: {text[:500]}")
                with open(os.path.join(OUTPUT_DIR, f"alt_{name.replace(' ', '_')}.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(text)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"Output: {OUTPUT_DIR}")
    subprocess.run(["ls", "-la", OUTPUT_DIR], check=False)


if __name__ == "__main__":
    main()
