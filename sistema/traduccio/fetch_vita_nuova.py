#!/usr/bin/env python3
"""Descarrega la Vita Nuova de Dante des de Wikisource italià."""

import re
from pathlib import Path

import httpx


ROMANS = [
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII",
    "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV", "XXXV", "XXXVI",
    "XXXVII", "XXXVIII", "XXXIX", "XL", "XLI", "XLII",
]


def fetch_raw(title: str) -> str:
    url = f"https://it.wikisource.org/w/index.php?title={title}&action=raw"
    r = httpx.get(url, timeout=15)
    r.raise_for_status()
    return r.text


def clean_wikitext(text: str) -> str:
    # Remove wiki templates
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    # Remove section/pages/poem tags
    text = re.sub(r"<section[^>]*/?>", "", text)
    text = re.sub(r"</section>", "", text)
    text = re.sub(r"</?poem>", "", text)
    text = re.sub(r"<pages[^/]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^/]*/>", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Wiki links
    text = re.sub(r"\[\[[^\]]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    # Bold/italic wiki markup
    text = text.replace("'''", "**")
    text = text.replace("''", "*")
    # Page markers
    text = re.sub(r"\[p\.\s*\d+\s*modifica\]", "", text)
    # Multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    base = Path(__file__).parent.parent
    obra_dir = base / "obres" / "narrativa" / "dante-alighieri" / "vita-nuova-vida-nova"
    obra_dir.mkdir(parents=True, exist_ok=True)

    output = "# Vita Nuova\n\n**Autor:** Dante Alighieri\n**Font:** Wikisource italià\n**Llengua:** italià\n\n---\n\n"
    errors: list[str] = []

    for r in ROMANS:
        title = f"Vita_nuova/{r}"
        try:
            raw = fetch_raw(title)
        except Exception as e:
            print(f"ERROR {r}: {e}")
            errors.append(r)
            continue

        if "<html" in raw.lower() or "Error" in raw[:200]:
            print(f"SKIP {r}: HTML error")
            errors.append(r)
            continue

        cleaned = clean_wikitext(raw)
        if cleaned:
            output += f"## {r}\n\n{cleaned}\n\n---\n\n"
            print(f"OK: {r} ({len(cleaned)} chars)")
        else:
            errors.append(r)
            print(f"EMPTY: {r}")

    outpath = obra_dir / "original.md"
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\nTotal: {len(output)} chars -> {outpath}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
