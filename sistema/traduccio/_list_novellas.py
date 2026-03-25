#!/usr/bin/env python3
"""Llista les novel·les del Decameró des de Wikisource italiana."""

import json
import sys
import urllib.parse
import urllib.request
from http.client import HTTPResponse


def fetch_all_pages() -> list[dict[str, str]]:
    """Obté totes les pàgines amb prefix 'Decameron/' de it.wikisource.org."""
    cont = ""
    all_pages: list[dict[str, str]] = []
    for _ in range(10):
        p: dict[str, str] = {
            "action": "query",
            "list": "allpages",
            "apprefix": "Decameron/",
            "aplimit": "500",
            "format": "json",
        }
        if cont:
            p["apcontinue"] = cont
        params = urllib.parse.urlencode(p)
        url = "https://it.wikisource.org/w/api.php?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp: HTTPResponse = urllib.request.urlopen(req, timeout=15)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"Error de xarxa: {e}", file=sys.stderr)
            sys.exit(1)
        with resp:
            data: dict = json.loads(resp.read())
        pages = data.get("query", {}).get("allpages", [])
        all_pages.extend(pages)
        c = data.get("continue", {}).get("apcontinue", "")
        if not c:
            break
        cont = c
    return all_pages


def main() -> None:
    all_pages = fetch_all_pages()
    novellas = [p["title"] for p in all_pages if "Novella" in p["title"]]
    for n in novellas:
        print(n)
    print(f"\nTotal: {len(novellas)} novellas, {len(all_pages)} total pages")


if __name__ == "__main__":
    main()
