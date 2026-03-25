#!/usr/bin/env python3
"""Fetch Rostam & Sohrab from Persian Wikisource."""
import html as html_mod
import json
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path

SECTIONS = [
    "شاهنامه (تصحیح ژول مل)/آغاز داستان سهراب",
    "شاهنامه (تصحیح ژول مل)/زادن سهراب از مادرش تهمینه",
    "شاهنامه (تصحیح ژول مل)/گرفتن سهراب دژ سفید را",
    "شاهنامه (تصحیح ژول مل)/فرستادن افراسیاب بارمان و هومان را به نزدیک سهراب",
    "شاهنامه (تصحیح ژول مل)/تاختن سهراب بر لشکر کاوس",
    "شاهنامه (تصحیح ژول مل)/رزم رستم با سهراب",
    "شاهنامه (تصحیح ژول مل)/افگندن سهراب رستم را",
    "شاهنامه (تصحیح ژول مل)/کشته شدن سهراب از رستم",
    "شاهنامه (تصحیح ژول مل)/زاری کردن رستم بر سهراب",
    "شاهنامه (تصحیح ژول مل)/بازگشت رستم و سهراب به لشکرگاه",
]

BASE = "https://fa.wikisource.org/w/api.php"
OBRA_DIR = Path("obres/narrativa/firdawsi/shahnameh-rostam-i-sohrab")


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_section(page_title: str) -> str:
    params = {"action": "parse", "page": page_title, "prop": "text", "format": "json"}
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw_html = data.get("parse", {}).get("text", {}).get("*", "")
        if raw_html:
            return html_to_text(raw_html)
    return ""


def main() -> None:
    all_parts: list[str] = []
    for sec in SECTIONS:
        short = sec.split("/")[-1]
        print(f"Fetching: {short}...", end=" ", flush=True)
        try:
            text = fetch_section(sec)
            if len(text) > 100:
                all_parts.append(f"## {short}\n\n{text}")
                print(f"OK ({len(text)} chars)")
            else:
                print(f"too short ({len(text)})")
        except Exception as e:
            print(f"ERROR: {e}")

    if not all_parts:
        print("ERROR: No sections fetched!")
        sys.exit(1)

    combined = "\n\n---\n\n".join(all_parts)

    header = """# شاهنامه — داستان رستم و سهراب
# Shahnameh — Rostam i Sohrab
**Autor:** Abolqasem Firdawsí (ابوالقاسم فردوسی)
**Font:** [Wikisource persa](https://fa.wikisource.org/wiki/%D8%B4%D8%A7%D9%87%D9%86%D8%A7%D9%85%D9%87_(%D8%AA%D8%B5%D8%AD%DB%8C%D8%AD_%DA%98%D9%88%D9%84_%D9%85%D9%84))
**Edició:** Tashih-e Jules Mohl (تصحیح ژول مل)
**Llengua:** persa (فارسی)

---

"""
    OBRA_DIR.mkdir(parents=True, exist_ok=True)
    out = OBRA_DIR / "original.md"
    out.write_text(header + combined, encoding="utf-8")
    print(f"\nSaved: {out} ({len(combined)} chars, {len(all_parts)} sections)")

    font_info = {
        "font": "wikisource",
        "url": "https://fa.wikisource.org/wiki/شاهنامه_(تصحیح_ژول_مل)",
        "qualitat": 9,
        "caracters": len(combined),
        "seccions": len(all_parts),
    }
    (OBRA_DIR / ".font_info.json").write_text(
        json.dumps(font_info, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
