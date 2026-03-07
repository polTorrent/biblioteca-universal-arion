#!/usr/bin/env python3
"""Descarrega les Odes d'Horaci (Carmina) de The Latin Library i selecciona 20 odes."""

import re
import urllib.request
from pathlib import Path


def descarrega_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def html_a_text(html: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<h[1-6][^>]*>", "\n\n## ", text)
    text = re.sub(r"</h[1-6]>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extreure_contingut(text: str) -> str:
    lines = text.split("\n")
    content = []
    started = False
    for line in lines:
        s = line.strip().upper()
        if not started and ("CARMINVM" in s or "CARMINUM" in s or "LIBER" in s):
            started = True
        if started:
            if "The Latin Library" in line or "The Classics Page" in line:
                break
            content.append(line)
    return "\n".join(content) if content else text


def main():
    base = "https://www.thelatinlibrary.com/horace/"
    books = [
        ("carm1.shtml", "I"),
        ("carm2.shtml", "II"),
        ("carm3.shtml", "III"),
        ("carm4.shtml", "IV"),
    ]

    all_text = []
    for fname, num in books:
        url = base + fname
        print(f"Descarregant Liber {num}...")
        html = descarrega_html(url)
        text = html_a_text(html)
        content = extreure_contingut(text)
        all_text.append(content)
        print(f"  {len(content)} caràcters")

    full = "\n\n---\n\n".join(all_text)
    print(f"\nTotal: {len(full)} caràcters")

    obra_dir = Path("obres/poesia/horaci/odes-seleccio-20-odes")
    obra_dir.mkdir(parents=True, exist_ok=True)

    header = """# Odes (Carmina) — Selecció de 20 Odes
**Autor:** Quintus Horatius Flaccus (Horaci)
**Font:** [The Latin Library](https://www.thelatinlibrary.com/hor.html)
**Llengua:** llatí

---

"""
    original_path = obra_dir / "original.md"
    original_path.write_text(header + full, encoding="utf-8")
    print(f"Guardat a {original_path}")


if __name__ == "__main__":
    main()
