#!/usr/bin/env python3
"""
Verificador anti-al·lucinació UNIVERSAL per traduccions.
Detecta unitats automàticament segons el gènere del text.

Modes:
  --strict    Alerta per qualsevol discrepància (com l'antic comportament)
  (defecte)   Mode relaxat: només alerta si recompte difereix >20%
              o si hi ha IDs numèrics clarament inexistents a l'original
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
    "paragraf": [],
}

# Romans → àrabs
_ROMANS = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
    'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
    'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19,
    'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24,
    'XXV': 25, 'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29,
    'XXX': 30, 'XXXI': 31, 'XXXII': 32, 'XXXIII': 33, 'XXXIV': 34,
    'XXXV': 35, 'XXXVI': 36, 'XXXVII': 37, 'XXXVIII': 38, 'XXXIX': 39,
    'XL': 40, 'XLI': 41, 'XLII': 42, 'XLIII': 43, 'XLIV': 44,
    'XLV': 45, 'XLVI': 46, 'XLVII': 47, 'XLVIII': 48, 'XLIX': 49,
    'L': 50, 'LI': 51, 'LII': 52, 'LIII': 53, 'LIV': 54,
    'LV': 55, 'LVI': 56, 'LVII': 57, 'LVIII': 58, 'LIX': 59,
    'LX': 60, 'LXI': 61, 'LXII': 62, 'LXIII': 63, 'LXIV': 64,
    'LXV': 65, 'LXVI': 66, 'LXVII': 67, 'LXVIII': 68, 'LXIX': 69,
    'LXX': 70, 'LXXI': 71, 'LXXII': 72, 'LXXIII': 73, 'LXXIV': 74,
    'LXXV': 75, 'LXXVI': 76, 'LXXVII': 77, 'LXXVIII': 78,
    'LXXIX': 79, 'LXXX': 80, 'LXXXI': 81,
    'XC': 90, 'C': 100, 'CC': 200, 'CCC': 300,
    'D': 500, 'M': 1000,
}


def normalitzar_id(raw_id: str) -> str:
    """Normalitza un ID a forma canònica (numèrica si possible).

    ### 195, **195.**, 195., § 195 → "195"
    XIV, Sonet XIV → "14"
    ANTÍGONA → "ANTÍGONA" (sense canvi per noms)
    """
    s = raw_id.strip().rstrip('.')
    # Ja és numèric
    if s.isdigit():
        return s
    # Numeral romà
    upper = s.upper()
    if upper in _ROMANS:
        return str(_ROMANS[upper])
    # Text no numèric (noms de personatges, etc.) — retornar en majúscules
    return upper


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


def _tots_els_patrons() -> list[str]:
    """Retorna TOTS els patrons de tots els gèneres (sense duplicats)."""
    vistos: set[str] = set()
    tots: list[str] = []
    for patrons in PATRONS_UNITAT.values():
        for p in patrons:
            if p not in vistos:
                vistos.add(p)
                tots.append(p)
    return tots


def extreure_unitats_universal(text: str) -> list[dict]:
    """Extreu unitats aplicant TOTS els patrons de tots els gèneres.

    Normalitza els IDs perquè "### 195", "**195.**", "195." i "§ 195"
    siguin tots "195".
    """
    unitats: list[dict] = []

    for patro in _tots_els_patrons():
        for match in re.finditer(patro, text):
            raw_id = match.group(1).strip()
            unitats.append({
                "id_raw": raw_id,
                "id": normalitzar_id(raw_id),
                "posicio": match.start(),
                "text_inici": text[match.start():match.start() + 80].strip(),
            })

    # Eliminar duplicats per posició (diferents patrons poden capturar
    # el mateix lloc) — quedar-se amb el primer
    vistos: set[int] = set()
    uniques: list[dict] = []
    for u in sorted(unitats, key=lambda x: x["posicio"]):
        if u["posicio"] not in vistos:
            vistos.add(u["posicio"])
            uniques.append(u)

    # Eliminar duplicats per ID normalitzat al mateix voltant
    # (ex: "195" capturat per dos patrons a posicions molt properes)
    ids_vistos: dict[str, int] = {}
    finals: list[dict] = []
    for u in uniques:
        prev_pos = ids_vistos.get(u["id"])
        if prev_pos is not None and abs(u["posicio"] - prev_pos) < 10:
            continue  # duplicat proper, ignorar
        ids_vistos[u["id"]] = u["posicio"]
        finals.append(u)

    return finals


def extreure_paragrafs(text: str) -> list[dict]:
    """Extreu paràgrafs com a unitats (fallback per textos sense numeració)."""
    paragrafs = re.split(r'\n\s*\n', text)
    unitats: list[dict] = []
    pos = 0
    for i, p in enumerate(paragrafs):
        p = p.strip()
        if len(p) > 20:  # Ignorar línies molt curtes
            unitats.append({
                "id_raw": str(i + 1),
                "id": str(i + 1),
                "posicio": pos,
                "text_inici": p[:80],
            })
        pos += len(p) + 2
    return unitats


def verificar(original_path: str, traduccio_path: str,
              genere: str | None = None, strict: bool = False) -> bool:
    """Verifica integritat original vs traducció.

    Mode relaxat (defecte): només alerta si recompte difereix >20%
    o si hi ha IDs numèrics clarament inexistents a l'original.

    Mode strict: alerta per qualsevol discrepància.
    """

    original = Path(original_path).read_text(encoding="utf-8")
    traduccio = Path(traduccio_path).read_text(encoding="utf-8")

    # Detectar gènere per informació
    genere_orig = genere or detectar_genere(original)
    genere_trad = genere or detectar_genere(traduccio)

    print(f"📚 Gènere detectat (original): {genere_orig}")
    print(f"📝 Gènere detectat (traducció): {genere_trad}")
    if not strict:
        print("   (mode relaxat — usa --strict per alertes estrictes)")

    # Extreure unitats amb TOTS els patrons
    unitats_orig = extreure_unitats_universal(original)
    unitats_trad = extreure_unitats_universal(traduccio)

    # Si no s'han trobat unitats numerades, fallback a paràgrafs
    if not unitats_orig:
        unitats_orig = extreure_paragrafs(original)
    if not unitats_trad:
        unitats_trad = extreure_paragrafs(traduccio)

    ids_orig = [u["id"] for u in unitats_orig]
    ids_trad = [u["id"] for u in unitats_trad]
    ids_orig_set = set(ids_orig)
    ids_trad_set = set(ids_trad)

    print(f"\n📖 Original: {len(unitats_orig)} unitats")
    print(f"📝 Traducció: {len(unitats_trad)} unitats")

    problemes = False
    avisos = False

    # ─── CHECK 1: Recompte ───
    n_orig = len(unitats_orig)
    n_trad = len(unitats_trad)
    if n_orig > 0:
        diff_ratio = abs(n_orig - n_trad) / n_orig
    else:
        diff_ratio = 0.0

    if n_orig != n_trad:
        if strict or diff_ratio > 0.20:
            label = "⚠️  RECOMPTE DIFERENT" if strict else "⚠️  RECOMPTE DIFEREIX >20%"
            print(f"\n{label}:")
            print(f"   Original:  {n_orig}")
            print(f"   Traducció: {n_trad}")
            print(f"   Diferència: {diff_ratio:.0%}")
            problemes = True
        else:
            print(f"\n📊 Recompte diferent (dins marge 20%): "
                  f"{n_orig} vs {n_trad} ({diff_ratio:.0%})")
            avisos = True

    # ─── CHECK 2: Unitats que falten ───
    falten_ids = ids_orig_set - ids_trad_set
    if falten_ids:
        falten = sorted(
            falten_ids,
            key=lambda x: int(x) if x.isdigit() else x
        )
        if strict:
            print("\n❌ UNITATS QUE FALTEN a la traducció:")
            for f in falten:
                u = next((u for u in unitats_orig if u["id"] == f), None)
                inici = u["text_inici"][:50] if u else "?"
                print(f'   • {f}: "{inici}..."')
            problemes = True
        elif len(falten) > n_orig * 0.20 if n_orig > 0 else False:
            print(f"\n❌ FALTEN {len(falten)} unitats (>{20}% de l'original):")
            for f in falten[:10]:
                u = next((u for u in unitats_orig if u["id"] == f), None)
                inici = u["text_inici"][:50] if u else "?"
                print(f'   • {f}: "{inici}..."')
            if len(falten) > 10:
                print(f"   ... i {len(falten) - 10} més")
            problemes = True
        else:
            print(f"\n📊 {len(falten)} IDs de l'original no trobats a la traducció "
                  f"(dins marge, pot ser diferència de format)")
            avisos = True

    # ─── CHECK 3: Unitats inventades ───
    sobren_ids = ids_trad_set - ids_orig_set
    if sobren_ids:
        sobren = sorted(
            sobren_ids,
            key=lambda x: int(x) if x.isdigit() else x
        )
        if strict:
            print("\n🚨 UNITATS POSSIBLEMENT INVENTADES a la traducció:")
            for s in sobren:
                u = next((u for u in unitats_trad if u["id"] == s), None)
                inici = u["text_inici"][:50] if u else "?"
                print(f'   • {s}: "{inici}..."')
            problemes = True
        elif len(sobren) > n_orig * 0.20 if n_orig > 0 else False:
            print(f"\n🚨 {len(sobren)} unitats INVENTADES "
                  f"(>{20}% respecte l'original):")
            for s in sobren[:10]:
                u = next((u for u in unitats_trad if u["id"] == s), None)
                inici = u["text_inici"][:50] if u else "?"
                print(f'   • {s}: "{inici}..."')
            if len(sobren) > 10:
                print(f"   ... i {len(sobren) - 10} més")
            problemes = True
        else:
            print(f"\n📊 {len(sobren)} IDs a la traducció no trobats a l'original "
                  f"(dins marge, pot ser diferència de format)")
            avisos = True

    # ─── CHECK 4: Ordre (només en mode strict) ───
    if strict:
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

        # En mode relaxat, llindar més alt per evitar falsos positius
        llindar_alt = 3.0 if strict else 5.0
        llindar_baix = 0.2 if strict else 0.1

        if ratio > llindar_alt or ratio < llindar_baix:
            sospitosos.append((uo["id"], len_o, len_t, ratio))

    if sospitosos:
        print("\n📏 LONGITUDS SOSPITOSES:")
        for uid, lo, lt, ratio in sospitosos:
            emoji = "🚨" if ratio > 5.0 or ratio < 0.1 else "⚠️"
            print(f"   {emoji} Unitat {uid}: orig={lo}ch, trad={lt}ch "
                  f"(×{ratio:.1f})")
        if strict:
            problemes = True
        else:
            avisos = True

    # ─── CHECK 6: Detecció de zones post-cita ───
    cites_original = list(re.finditer(
        r'[«"„"\'](.*?)[»""\'"]', original, re.DOTALL
    ))
    if cites_original and strict:
        print(f"\n🔍 Cites/cometes detectades a l'original: {len(cites_original)}")
        print("   (Zones de risc d'al·lucinació)")

    # ─── RESUM ───
    if not problemes and not avisos:
        print(f"\n✅ VERIFICACIÓ OK — "
              f"{len(unitats_orig)} unitats verificades")
        return True
    elif not problemes:
        print(f"\n✅ VERIFICACIÓ OK (amb avisos menors) — "
              f"{len(unitats_orig)} unitats verificades")
        return True
    else:
        print("\n❌ VERIFICACIÓ FALLIDA — Cal revisió manual")
        return False


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    strict = '--strict' in sys.argv

    if len(args) < 2:
        print("Verificador anti-al·lucinació universal per traduccions")
        print()
        print("Ús:")
        print("  python verificar_traduccio.py <original.md> <traduccio.md> [gènere] [--strict]")
        print()
        print("Modes:")
        print("  (defecte)  Relaxat: alerta si recompte >20% o IDs clarament inventats")
        print("  --strict   Estricte: alerta per qualsevol discrepància")
        print()
        print("Gèneres: aforisme, seccio, capitol, escena, parlament,")
        print("         estrofa, vers_oriental, paragraf (auto si no s'indica)")
        print()
        print("Exemples:")
        print("  python verificar_traduccio.py obres/.../original.md obres/.../traduccio.md")
        print("  python verificar_traduccio.py original.md traduccio.md aforisme --strict")
        sys.exit(1)

    genere_arg = args[2] if len(args) > 2 else None
    ok = verificar(args[0], args[1], genere_arg, strict=strict)
    sys.exit(0 if ok else 1)
