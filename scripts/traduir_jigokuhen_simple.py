#!/usr/bin/env python3
"""Traducció directa de Jigokuhen capítol per capítol."""

import os
import sys
import re
import subprocess
import json
from pathlib import Path

os.environ["CLAUDECODE"] = "1"

def traduir_amb_claude(text_japones: str, capitol: str) -> str:
    """Tradueix un fragment usant el CLI de Claude."""

    prompt = f"""Tradueix aquest fragment de "El Biombo de l'Infern" (地獄変) d'Akutagawa Ryūnosuke del japonès al català.

INSTRUCCIONS:
- Tradueix de manera literària, preservant l'estil narratiu japonès clàssic
- Manté el to formal i elegant del narrador (un servent que recorda els fets)
- Conserva les referències culturals japoneses (budisme, període Heian, etc.)
- Usa un català literari i fluid

CAPÍTOL: {capitol}

TEXT JAPONÈS:
{text_japones}

TRADUCCIÓ CATALANA:"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  ⚠ Error: {result.stderr[:200]}")
            return f"[Error traduint capítol {capitol}]"
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Timeout al capítol {capitol}")
        return f"[Timeout traduint capítol {capitol}]"
    except Exception as e:
        print(f"  ⚠ Excepció: {e}")
        return f"[Excepció: {e}]"

def main():
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / "narrativa" / "akutagawa" / "biombo-infern"

    # Llegir text original
    with open(obra_dir / "original.md", "r", encoding="utf-8") as f:
        text = f.read()

    # Extreure text narratiu
    if "一\n" in text:
        idx = text.index("一\n")
        text = text[idx:]
    if "*Text de domini públic" in text:
        text = text.split("*Text de domini públic")[0].strip()

    print("═" * 60)
    print("  TRADUCCIÓ: El Biombo de l'Infern (地獄変)")
    print("  Akutagawa Ryūnosuke, 1918")
    print("═" * 60)
    print()

    # Dividir per capítols
    # Els números japonesos: 一二三四五六七八九十
    pattern = r'\n(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十)\n'
    parts = re.split(pattern, text)

    capitols = []
    i = 0
    while i < len(parts):
        if i == 0:
            # El primer element pot ser buit o tenir contingut abans del primer capítol
            if parts[i].strip():
                capitols.append(("一", parts[i].strip()))
            i += 1
        else:
            num = parts[i]
            contingut = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if contingut:
                capitols.append((num, contingut))
            i += 2

    print(f"Trobats {len(capitols)} capítols")
    print()

    # Mapa de números japonesos a aràbics
    num_map = {
        "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
        "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
        "十一": "11", "十二": "12", "十三": "13", "十四": "14", "十五": "15",
        "十六": "16", "十七": "17", "十八": "18", "十九": "19", "二十": "20"
    }

    traduccions = []

    for i, (num_jp, contingut) in enumerate(capitols):
        num_arab = num_map.get(num_jp, num_jp)
        print(f"[{i+1}/{len(capitols)}] Traduint capítol {num_arab} ({len(contingut)} caràcters)...")

        traduccio = traduir_amb_claude(contingut, num_arab)
        traduccions.append((num_arab, traduccio))

        print(f"  ✓ Completat ({len(traduccio)} caràcters)")

    # Construir document final
    print()
    print("Generant document final...")

    document = """# El Biombo de l'Infern
*Akutagawa Ryūnosuke (1918)*

Traduït del japonès per Biblioteca Arion

---

"""

    for num, trad in traduccions:
        document += f"## {num}\n\n{trad}\n\n"

    document += """---

*Traducció de domini públic. Font original: Aozora Bunko (青空文庫).*
"""

    # Guardar
    traduccio_path = obra_dir / "traduccio.md"
    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(document)

    print(f"✓ Traducció guardada a: {traduccio_path}")
    print()
    print("═" * 60)
    print("  TRADUCCIÓ COMPLETADA")
    print("═" * 60)

if __name__ == "__main__":
    main()
