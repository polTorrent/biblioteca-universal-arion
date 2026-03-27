#!/usr/bin/env python3
"""
Verificador anti-al·lucinació UNIVERSAL per traduccions.
Detecta unitats automàticament segons el gènere del text.
"""

import re
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# DETECCIÓ AUTOMÀTICA D'UNITATS SEGONS GÈNERE
# ═══════════════════════════════════════════════════════════════

PATRONS_UNITAT: dict[str, list[str]] = {
    "aforisme": [
        r'(?:^|\n)### (\d+)',              # ### 195
        r'(?:^|\n)\*\*(\d+)\.\*\*',        # **195.**
        r'(?:^|\n)(\d+)\.\s',              # 195. Text
        r'(?:^|\n)(\d+)\s*[—–\-]\s',       # 195 — Text
    ],
    "seccio": [
        r'(?:^|\n)§\s*(\d+)',              # § 28
        r'(?:^|\n)### §\s*(\d+)',          # ### § 28
        r'(?:^|\n)## Capítol\s+(\w+)',     # ## Capítol XII
        r'(?:^|\n)### Secció\s+(\w+)',     # ### Secció 5
    ],
    "capitol": [
        r'(?:^|\n)## Capítol\s+(\w+)',     # ## Capítol XII
        r'(?:^|\n)# Capítol\s+(\w+)',      # # Capítol XII
        r'(?:^|\n)## (\w+)\.',             # ## I. / ## XII.
        r'(?:^|\n)### (\w+)\.',            # ### 1. / ### XII.
    ],
    "escena": [
        r'(?:^|\n)## Escena\s+(\w+)',      # ## Escena 3
        r'(?:^|\n)### Acte\s+(\w+)',       # ### Acte II
        r'(?:^|\n)## Acte\s+(\w+)',        # ## Acte II
    ],
    "parlament": [
        r'(?:^|\n)\*\*([A-ZÀÈÉÍÒÓÚÇÑ][A-ZÀÈÉÍÒÓÚÇÑ\s]+)\*\*[:\.]',  # **ANTÍGONA:**
        r'(?:^|\n)([A-ZÀÈÉÍÒÓÚÇÑ][A-ZÀÈÉÍÒÓÚÇÑ]{2,})[:\.]',        # ANTÍGONA:
    ],
    "estrofa": [
        r'(?:^|\n)### Sonet\s+(\w+)',      # ### Sonet XIV
        r'(?:^|\n)### Poema\s+(\w+)',      # ### Poema 42
        r'(?:^|\n)## (\w+)\s*$',           # ## XIV
        r'(?:^|\n)### Oda\s+(\w+)',        # ### Oda III
    ],
    "vers_oriental": [
        r'(?:^|\n)### Vers\s+(\d+)',       # ### Vers 42
        r'(?:^|\n)### Sutra\s+(\d+)',      # ### Sutra 3
        r'(?:^|\n)(\d+)\s*[\.:\-]\s',      # 42. Text
    ],
    "paragraf": [
        # Fallback: paràgrafs separats per línia en blanc
        # Es compta diferent (veure funció dedicada)
    ],
}


def detectar_genere(text: str) -> str:
    """Detecta automàticament el gènere/unitat dominant del text."""
    resultats: dict[str, int] = {}
    for genere, patrons in PATRONS_UNITAT.items():
        if genere == "paragraf":
            continue
        total = 0
        for patro in patrons:
            total += len(re.findall(patro, text))
        if total > 0:
            resultats[genere] = total

    if not resultats:
        return "paragraf"

    return max(resultats, key=resultats.get)


def extreure_unitats(text: str, genere: str | None = None) -> list[dict]:
    """Extreu unitats del text segons el gènere."""
    if genere is None:
        genere = detectar_genere(text)

    if genere == "paragraf":
        return extreure_paragrafs(text)

    patrons = PATRONS_UNITAT.get(genere, [])
    unitats: list[dict] = []

    for patro in patrons:
        for match in re.finditer(patro, text):
            unitats.append({
                "id": match.group(1).strip(),
                "posicio": match.start(),
                "text_inici": text[match.start():match.start() + 80].strip(),
            })

    # Eliminar duplicats (mateixa posició)
    vistos: set[int] = set()
    uniques: list[dict] = []
    for u in sorted(unitats, key=lambda x: x["posicio"]):
        if u["posicio"] not in vistos:
            vistos.add(u["posicio"])
            uniques.append(u)

    return uniques


def extreure_paragrafs(text: str) -> list[dict]:
    """Extreu paràgrafs com a unitats (fallback per textos sense numeració)."""
    paragrafs = re.split(r'\n\s*\n', text)
    unitats: list[dict] = []
    pos = 0
    for i, p in enumerate(paragrafs):
        p = p.strip()
        if len(p) > 20:  # Ignorar línies molt curtes
            unitats.append({
                "id": str(i + 1),
                "posicio": pos,
                "text_inici": p[:80],
            })
        pos += len(p) + 2
    return unitats


def verificar(original_path: str, traduccio_path: str,
              genere: str | None = None) -> bool:
    """Verifica integritat original vs traducció."""

    original = Path(original_path).read_text(encoding="utf-8")
    traduccio = Path(traduccio_path).read_text(encoding="utf-8")

    # Detectar gènere si no s'especifica
    genere_orig = genere or detectar_genere(original)
    genere_trad = genere or detectar_genere(traduccio)

    print(f"📚 Gènere detectat (original): {genere_orig}")
    print(f"📝 Gènere detectat (traducció): {genere_trad}")

    if genere_orig != genere_trad:
        print("⚠️  ALERTA: gèneres diferents detectats!")

    genere_final = genere or genere_orig

    unitats_orig = extreure_unitats(original, genere_final)
    unitats_trad = extreure_unitats(traduccio, genere_final)

    ids_orig = [u["id"] for u in unitats_orig]
    ids_trad = [u["id"] for u in unitats_trad]

    print(f"\n📖 Original: {len(unitats_orig)} unitats ({genere_final})")
    print(f"📝 Traducció: {len(unitats_trad)} unitats ({genere_final})")

    problemes = False

    # ─── CHECK 1: Recompte ───
    if len(unitats_orig) != len(unitats_trad):
        print(f"\n⚠️  RECOMPTE DIFERENT:")
        print(f"   Original:  {len(unitats_orig)}")
        print(f"   Traducció: {len(unitats_trad)}")
        problemes = True

    # ─── CHECK 2: Unitats que falten ───
    falten = sorted(
        set(ids_orig) - set(ids_trad),
        key=lambda x: int(x) if x.isdigit() else x
    )
    if falten:
        print("\n❌ UNITATS QUE FALTEN a la traducció:")
        for f in falten:
            u = next((u for u in unitats_orig if u["id"] == f), None)
            inici = u["text_inici"][:50] if u else "?"
            print(f'   • {f}: "{inici}..."')
        problemes = True

    # ─── CHECK 3: Unitats inventades ───
    sobren = sorted(
        set(ids_trad) - set(ids_orig),
        key=lambda x: int(x) if x.isdigit() else x
    )
    if sobren:
        print("\n🚨 UNITATS POSSIBLEMENT INVENTADES a la traducció:")
        for s in sobren:
            u = next((u for u in unitats_trad if u["id"] == s), None)
            inici = u["text_inici"][:50] if u else "?"
            print(f'   • {s}: "{inici}..."')
        problemes = True

    # ─── CHECK 4: Ordre ───
    desalineacions = 0
    for i, (o, t) in enumerate(zip(ids_orig, ids_trad)):
        if o != t:
            if desalineacions == 0:
                print(f"\n🔀 DESALINEACIÓ a partir de posició {i}:")
            if desalineacions < 5:
                print(f"   Posició {i}: original='{o}', traducció='{t}'")
            desalineacions += 1
    if desalineacions > 5:
        print(f"   ... i {desalineacions - 5} desalineacions més")
    if desalineacions:
        problemes = True

    # ─── CHECK 5: Longituds sospitoses ───
    sospitosos: list[tuple[str, int, int, float]] = []
    for uo in unitats_orig:
        corresponent = [ut for ut in unitats_trad if ut["id"] == uo["id"]]
        if not corresponent:
            continue
        ut = corresponent[0]

        idx_o = unitats_orig.index(uo)
        idx_t = unitats_trad.index(ut)

        fi_o = (unitats_orig[idx_o + 1]["posicio"]
                if idx_o + 1 < len(unitats_orig) else len(original))
        fi_t = (unitats_trad[idx_t + 1]["posicio"]
                if idx_t + 1 < len(unitats_trad) else len(traduccio))

        len_o = fi_o - uo["posicio"]
        len_t = fi_t - ut["posicio"]

        ratio = len_t / len_o if len_o > 0 else 0

        if ratio > 3.0 or ratio < 0.2:
            sospitosos.append((uo["id"], len_o, len_t, ratio))

    if sospitosos:
        print("\n📏 LONGITUDS SOSPITOSES:")
        for uid, lo, lt, ratio in sospitosos:
            emoji = "🚨" if ratio > 3.5 or ratio < 0.15 else "⚠️"
            print(f"   {emoji} Unitat {uid}: orig={lo}ch, trad={lt}ch "
                  f"(×{ratio:.1f})")
        problemes = True

    # ─── CHECK 6: Detecció de zones post-cita ───
    cites_original = list(re.finditer(
        r'[«"„"\'](.*?)[»""\'"]', original, re.DOTALL
    ))
    if cites_original:
        print(f"\n🔍 Cites/cometes detectades a l'original: {len(cites_original)}")
        print("   (Zones de risc d'al·lucinació)")

    # ─── RESUM ───
    if not problemes:
        print(f"\n✅ VERIFICACIÓ ESTRUCTURAL OK — "
              f"{len(unitats_orig)} unitats verificades")
        return True
    else:
        print("\n❌ VERIFICACIÓ FALLIDA — Cal revisió manual")
        return False


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Verificador anti-al·lucinació universal per traduccions")
        print()
        print("Ús:")
        print("  python verificar_traduccio.py <original.md> <traduccio.md> [gènere]")
        print()
        print("Gèneres: aforisme, seccio, capitol, escena, parlament,")
        print("         estrofa, vers_oriental, paragraf (auto si no s'indica)")
        print()
        print("Exemples:")
        print("  python verificar_traduccio.py obres/.../original.md obres/.../traduccio.md")
        print("  python verificar_traduccio.py original.md traduccio.md aforisme")
        print("  python verificar_traduccio.py original.md traduccio.md escena")
        sys.exit(1)

    genere_arg = sys.argv[3] if len(sys.argv) > 3 else None
    ok = verificar(sys.argv[1], sys.argv[2], genere_arg)
    sys.exit(0 if ok else 1)
