#!/usr/bin/env python3
"""Genera original.md per al Tirukkural a partir del JSON descarregat."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SELECTED_NUMBERS: list[int] = [
    # Book 1: Aram (Virtue) - 38 kurals
    1, 2, 10, 11, 15, 21, 25, 31, 34, 41, 45, 50,
    51, 56, 61, 67, 71, 76, 80, 81, 86, 91, 95, 100,
    101, 105, 110, 111, 115, 121, 125, 130, 131, 133,
    141, 151, 155, 160,
    # Book 2: Porul (Wealth) - 38 kurals
    381, 383, 390, 391, 395, 400, 421, 423, 430,
    431, 436, 471, 475, 491, 495, 521, 525,
    541, 545, 550, 591, 594, 600, 611, 615, 620,
    631, 636, 691, 695, 721, 725, 751, 755, 760,
    781, 785, 790,
    # Book 3: Inbam (Love) - 27 kurals
    1081, 1085, 1090, 1091, 1095, 1100,
    1101, 1105, 1110, 1141, 1145,
    1171, 1175, 1180, 1191, 1195, 1200,
    1241, 1245, 1271, 1275,
    1291, 1295, 1300, 1321, 1325, 1330,
]

CHAPTER_INFO: dict[int, tuple[str, str, str]] = {
    1: ("கடவுள் வாழ்த்து", "Lloanca de Deu", "Aram"),
    2: ("வான்சிறப்பு", "Excellencia de la pluja", "Aram"),
    3: ("நீத்தார் பெருமை", "Grandesa dels ascetes", "Aram"),
    4: ("அறன்வலியுறுத்தல்", "Afirmacio de la virtut", "Aram"),
    5: ("இல்வாழ்க்கை", "Vida domestica", "Aram"),
    6: ("வாழ்க்கைத் துணைநலம்", "L'esposa", "Aram"),
    7: ("புதல்வரைப் பெறுதல்", "Els fills", "Aram"),
    8: ("அன்புடைமை", "Amor i bondat", "Aram"),
    9: ("விருந்தோம்பல்", "Hospitalitat", "Aram"),
    10: ("இனியவைகூறல்", "Paraules dolces", "Aram"),
    11: ("செய்ந்நன்றி அறிதல்", "Gratitud", "Aram"),
    12: ("நடுவு நிலைமை", "Imparcialitat", "Aram"),
    13: ("அடக்கமுடைமை", "Autocontrol", "Aram"),
    14: ("ஒழுக்கமுடைமை", "Propietat moral", "Aram"),
    15: ("பிறனில் விழையாமை", "No cobejar la dona aliena", "Aram"),
    16: ("பொறையுடைமை", "Paciencia", "Aram"),
    39: ("இறைமாட்சி", "Grandesa del rei", "Porul"),
    40: ("கல்வி", "L'aprenentatge", "Porul"),
    43: ("அறிவுடைமை", "El coneixement", "Porul"),
    44: ("குற்றங்கடிதல்", "Evitar les faltes", "Porul"),
    48: ("வலியறிதல்", "Jutjar la forca", "Porul"),
    50: ("இடனறிதல்", "Jutjar el lloc", "Porul"),
    53: ("சுற்றந்தழால்", "Vinculacio als grans", "Porul"),
    55: ("செங்கோன்மை", "Govern just", "Porul"),
    60: ("ஊக்கமுடைமை", "Energia", "Porul"),
    62: ("ஆள்வினையுடைமை", "Esforc", "Porul"),
    64: ("அமைச்சு", "Saviesa en l'accio", "Porul"),
    70: ("மானம்", "Esforc viril", "Porul"),
    73: ("அரண்", "La fortalesa", "Porul"),
    76: ("பொருள்செயல்வகை", "La riquesa", "Porul"),
    80: ("நட்பு", "L'amistat", "Porul"),
    109: ("தகையணங்குறுத்தல்", "Atraccio mental", "Inbam"),
    110: ("குறிப்பறிதல்", "Reconeixement de signes", "Inbam"),
    111: ("புணர்ச்சி மகிழ்தல்", "Joia de la unio", "Inbam"),
    115: ("அலரறிவுறுத்தல்", "Lament de la separacio", "Inbam"),
    118: ("கண்விதுப்பழிதல்", "Ulls llanguint", "Inbam"),
    120: ("தனிப்படர் மிகுதி", "Consumir-se", "Inbam"),
    125: ("நெஞ்சொடு கிளத்தல்", "Enyoranca", "Inbam"),
    128: ("குறிப்பறிவுறுத்தல்", "Signes de passio", "Inbam"),
    130: ("நெஞ்சொடு புலத்தல்", "Enuig fingit", "Inbam"),
    133: ("ஊடலுவகை", "Joies del joc amoros", "Inbam"),
}

BOOK_NAMES: dict[str, str] = {
    "Aram": "## Llibre I: அறம் (Aram — Virtut)",
    "Porul": "## Llibre II: பொருள் (Porul — Riquesa)",
    "Inbam": "## Llibre III: இன்பம் (Inbam — Amor)",
}


def get_chapter(num: int) -> int:
    return ((num - 1) // 10) + 1


def generar_original(json_path: Path, outpath: Path) -> None:
    with open(json_path) as f:
        d = json.load(f)

    kurals: list[dict[str, object]] = d["kural"]
    kural_map: dict[int, dict[str, object]] = {k["Number"]: k for k in kurals}

    lines: list[str] = [
        "# திருக்குறள் — Tirukkuṛaḷ",
        "",
        "**Thiruvalluvar** (திருவள்ளுவர்)",
        "",
        f"Selecció de {len(SELECTED_NUMBERS)} kurals dels tres llibres:"
        " Aram (அறம், Virtut), Porul (பொருள், Riquesa) i Inbam (இன்பம், Amor).",
        "",
        "Text original en tàmil (domini públic, c. segle III aC – segle V dC).",
        "",
        "---",
        "",
    ]

    current_book: str | None = None
    current_chapter: int | None = None
    missing: list[int] = []

    for num in SELECTED_NUMBERS:
        k = kural_map.get(num)
        if k is None:
            missing.append(num)
            continue

        ch = get_chapter(num)

        if ch in CHAPTER_INFO:
            ch_tamil, ch_catalan, book = CHAPTER_INFO[ch]

            if book != current_book:
                current_book = book
                lines.append(BOOK_NAMES[book])
                lines.append("")

            if ch != current_chapter:
                current_chapter = ch
                lines.append(f"### Capitol {ch}: {ch_tamil} — {ch_catalan}")
                lines.append("")

        lines.append(f"**Kural {k['Number']}**")
        lines.append("")
        lines.append(f"> {k['Line1']}")
        lines.append(f"> {k['Line2']}")
        lines.append("")
        t1 = k.get("transliteration1", "")
        t2 = k.get("transliteration2", "")
        if t1 and t2:
            lines.append(f"*{t1} / {t2}*")
            lines.append("")
        explanation = k.get("Translation", k.get("explanation", ""))
        lines.append(f"[EN: {explanation}]")
        lines.append("")

    if missing:
        print(f"AVÍS: {len(missing)} kurals no trobats al JSON: {missing}", file=sys.stderr)

    content = "\n".join(lines)
    generated = len(SELECTED_NUMBERS) - len(missing)
    print(f"Generated {generated} kurals, {len(content)} chars")

    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w") as f:
        f.write(content)
    print(f"Written to {outpath}")


def main() -> None:
    json_path = Path("/tmp/tirukkural.json")
    if not json_path.exists():
        print(f"ERROR: No s'ha trobat {json_path}", file=sys.stderr)
        print("Descarrega'l primer amb: curl -o /tmp/tirukkural.json <url>", file=sys.stderr)
        sys.exit(1)

    outpath = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/tirukkural_original.md")
    generar_original(json_path, outpath)


if __name__ == "__main__":
    main()
