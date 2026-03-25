#!/usr/bin/env python3
"""Fetch Plato's Crito Greek text from Perseus Digital Library, section by section."""
import html
import re
import time
import urllib.error
import urllib.request

BASE_URL = (
    "https://www.perseus.tufts.edu/hopper/text"
    "?doc=Perseus%3Atext%3A1999.01.0169%3Atext%3DCrito%3Asection%3D{section}"
)

GREEK_PATTERN = re.compile(r"([\u0370-\u03FF\u1F00-\u1FFF].{20,})")
TEXT_CONTAINER_PATTERN = re.compile(
    r'class="text_container"[^>]*>(.*?)</div>', re.DOTALL
)


def generar_seccions() -> list[str]:
    """Genera les seccions del Critó (43a-54e)."""
    seccions: list[str] = []
    for num in range(43, 55):
        for letter in "abcde":
            seccions.append(f"{num}{letter}")
    return seccions


def extreure_text_grec(contingut: str) -> str | None:
    """Extreu text grec del HTML de Perseus."""
    match = TEXT_CONTAINER_PATTERN.search(contingut)
    if match:
        chunk = re.sub(r"<[^>]+>", "", match.group(1))
        chunk = html.unescape(chunk).strip()
        if chunk:
            return chunk
        return None

    # Fallback: buscar qualsevol text grec substancial
    found = GREEK_PATTERN.findall(contingut)
    if found:
        return max(found, key=len)
    return None


def fetch_seccions() -> list[str]:
    """Descarrega totes les seccions del Critó de Perseus."""
    seccions = generar_seccions()
    tots_els_textos: list[str] = []

    for seccio in seccions:
        url = BASE_URL.format(section=seccio)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                contingut = resp.read().decode("utf-8", errors="replace")

            text = extreure_text_grec(contingut)
            if text:
                tots_els_textos.append(f"[{seccio}] {text}")
                print(f"OK {seccio}: {text[:80]}...")
            else:
                print(f"MISS {seccio}")

            time.sleep(0.5)  # Be polite
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            print(f"ERR {seccio}: {e}")

    return tots_els_textos


def main() -> None:
    """Punt d'entrada principal."""
    textos = fetch_seccions()
    print("\n\n========== FULL TEXT ==========\n")
    print("\n\n".join(textos))
    print(f"\n\nTotal sections found: {len(textos)}")


if __name__ == "__main__":
    main()
