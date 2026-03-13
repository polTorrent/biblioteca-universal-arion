#!/usr/bin/env python3
"""Fetch 10 Petőfi poems from Hungarian Wikisource."""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request

poems: dict[str, str] = {
    'Befordultam a konyhára': 'Befordultam_a_konyh%C3%A1ra',
    'A XIX. század költői': 'A_XIX._sz%C3%A1zad_k%C3%B6lt%C5%91i',
    'Ha férfi vagy, légy férfi': 'Ha_f%C3%A9rfi_vagy,_l%C3%A9gy_f%C3%A9rfi',
    'Itt van az ősz, itt van újra': 'Itt_van_az_%C5%91sz,_itt_van_%C3%BAjra',
    'Föltámadott a tenger': 'F%C3%B6lt%C3%A1madott_a_tenger',
    'Dalaim': 'Dalaim',
    'Az őrült': 'Az_%C5%91r%C3%BClt',
    'István öcsémhez': 'Istv%C3%A1n_%C3%B6cs%C3%A9mhez',
    'Szabadság, szerelem!': 'Szabads%C3%A1g,_szerelem!',
    'Pató Pál úr': 'Pat%C3%B3_P%C3%A1l_%C3%BAr',
}

def main() -> None:
    for title, slug in poems.items():
        url = f'https://hu.wikisource.org/wiki/{slug}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode('utf-8')
            match = re.search(
                r'class="mw-parser-output">(.*?)<div class="printfooter"',
                text,
                re.DOTALL,
            )
            if match:
                body = match.group(1)
                body = re.sub(r'<br\s*/?>', '\n', body)
                body = re.sub(r'<[^>]+>', '', body)
                body = html.unescape(body)
                lines = [line.strip() for line in body.strip().split('\n')]
                while lines and not lines[0]:
                    lines.pop(0)
                while lines and not lines[-1]:
                    lines.pop()
                content = '\n'.join(lines)
                print(f'=== {title} ===')
                print(content[:4000])
                print()
            else:
                print(f'=== {title} === NOT FOUND')
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f'=== {title} === ERROR: {e}')


if __name__ == '__main__':
    main()
