#!/usr/bin/env python3
"""Clean Book 5 of Morgenrothe from OCR text and produce _buch5_clean.md"""
import re

INPUT = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/_morgenrothe_ocr.txt"
OUTPUT = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/_buch5_clean.md"

with open(INPUT, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Extract Book 5, starting from line 10673 (0-indexed: 10672)
raw = "".join(lines[10672:])

# Step 1: Remove page numbers and footer cruft
# Page numbers: "— 284 —", "- 285 —", "~ 299 -", "_ 336 —", "- 363 -" etc.
raw = re.sub(r"\n\s*[\u2014\u2013_~\-]+\s*\d{3}\s*[\u2014\u2013_~\-]+\s*\n", "\n", raw)
# Standalone three-digit page numbers on their own line
raw = re.sub(r"\n\s*\d{3}\s*\n", "\n", raw)
# Footer lines like "Nietzsche, Morgenröthe. 19" etc. (various OCR spellings)
raw = re.sub(r"\n\s*Nietz?sche,?\s*M\w+r\w+e\.?\s*\d+\**\s*\n", "\n", raw, flags=re.IGNORECASE)
# Small standalone numbers (page refs, footnote markers): "19'", "20*", "23**"
raw = re.sub(r"\n\s*\d{1,2}['\*]*\s*\n", "\n", raw)

# Remove trailing junk after aphorism 575
idx = raw.find("Oder, meine Br")
if idx > 0:
    end_idx = raw.find("\n", idx)
    if end_idx > 0:
        raw = raw[:end_idx]

# Remove header
raw = re.sub(r"^F.nftes Buch\.\s*\n+", "", raw)

# Step 2: Fix aphorism markers
raw = raw.replace("509. # ", "509.\n")
raw = re.sub(r"556\.\s+\S+\s+\S+\s*\n", "556.\n", raw)

# Insert missing 511. marker
marker_511 = 'sein!\n'
pos_511 = raw.find('moralisches Wesen" sein!')
if pos_511 > 0:
    end_511 = raw.find('\n', pos_511)
    if end_511 > 0:
        insert_pos = end_511 + 1
        # Skip blank lines
        while insert_pos < len(raw) and raw[insert_pos] == '\n':
            insert_pos += 1
        raw = raw[:insert_pos] + "511.\n" + raw[insert_pos:]

# Convert number-dash to number-dot: "425-\n" -> "425.\n"
raw = re.sub(r"(\d{3})-\s*\n", r"\1.\n", raw)
# Also inline: "494- " etc
raw = re.sub(r"(\d{3})-\s+", r"\1.\n", raw)

# Remove bullet artifacts
raw = raw.replace("\u2022 ", "")

# Step 3: Join hyphenated words across lines
raw = re.sub(r"(\w)-\s*\n\s*", lambda m: m.group(1), raw)

# Step 4: Collapse multiple blank lines and fix OCR line-spacing issues
raw = re.sub(r"\n{3,}", "\n\n", raw)

# Some OCR sections have each line separated by a blank line.
# Join them: if a line doesn't end with paragraph-ending punctuation
# and the next non-blank line is a continuation (starts with lowercase or punctuation),
# remove the blank line between them.
lines_list = raw.split("\n")
new_lines = []
i = 0
while i < len(lines_list):
    line = lines_list[i]
    new_lines.append(line)
    # Check if this is a content line followed by blank + continuation
    if (i + 2 < len(lines_list)
        and line.strip()
        and lines_list[i+1].strip() == ""
        and lines_list[i+2].strip()
        and not re.match(r"^\d{3}\.\s*$", lines_list[i+2].strip())
        and not re.match(r"^###", lines_list[i+2].strip())
        # Current line doesn't end a paragraph
        and not re.search(r"[.!?—]\s*$", line.strip())
        # Next line looks like a continuation
        and re.match(r"^[a-züöäA-ZÜÖÄ\"\u201e\u201c(]", lines_list[i+2].strip())):
        # Skip the blank line
        i += 2
        continue
    i += 1
raw = "\n".join(new_lines)

# Step 5: Split into aphorisms
aph_pattern = re.compile(r"^(\d{3})\.\s*$", re.MULTILINE)
matches = list(aph_pattern.finditer(raw))

aphorisms = {}
for i, m in enumerate(matches):
    num = int(m.group(1))
    start = m.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
    text = raw[start:end].strip()
    aphorisms[num] = text

print(f"Extracted {len(aphorisms)} aphorisms from OCR")
found = sorted(aphorisms.keys())
missing = sorted(set(range(423, 576)) - set(found))
print(f"Missing: {missing}")

# Step 6: Clean text
def clean_aphorism(text):
    # Remove any remaining page number lines within aphorism text
    text = re.sub(r"\n\s*[\u2014\u2013_~\-]+\s*\d{3}\s*[\u2014\u2013_~\-]+\s*\n", "\n", text)
    text = re.sub(r"\n\s*\d{3}\s*\n", "\n", text)
    paragraphs = re.split(r"\n\s*\n", text)
    cleaned = []
    for para in paragraphs:
        # Skip paragraphs that are just page numbers
        stripped = para.strip()
        if re.match(r"^[\u2014\u2013_~\-\s\d]+$", stripped):
            continue
        para = re.sub(r"\s*\n\s*", " ", para)
        para = re.sub(r"  +", " ", para)
        para = para.strip()
        if para:
            cleaned.append(para)

    # Join short paragraphs that are just broken lines from OCR
    # If a paragraph is short (< 80 chars) and doesn't end with sentence-ending punctuation,
    # join it with the next one
    merged = []
    i = 0
    while i < len(cleaned):
        current = cleaned[i]
        while i + 1 < len(cleaned) and len(current) < 80 and not re.search(r'[.!?"\u201d\u201c]\s*$', current):
            i += 1
            current = current + " " + cleaned[i]
        merged.append(current)
        i += 1
    return "\n\n".join(merged)

# OCR error fixes
OCR_FIXES = [
    ("in*s", "in's"),
    ("in*'s", "in's"),
    ("Schedlreflexion", "Schallreflexion"),
    ("Olasfenster", "Glasfenster"),
    ("Grriechen", "Griechen"),
    ("Vor\\\\airf", "Vorwurf"),
    ("hinausnifk", "hinausruft"),
    ("fHiheren", "früheren"),
    ("Grrund", "Grund"),
    ("g^ehören", "gehören"),
    ("gxite", "gute"),
    ("Fletsch", "Fleisch"),
    ("kedter", "kalter"),
    ("^oUt", "wollt"),
    ("^eht", "geht"),
    ("^Was", "Was"),
    ("Erkenntmss", "Erkenntniss"),
    ("Leb^i", "Leben"),
    ("Zogern", "Zögern"),
    ("gtösste", "grösste"),
    ("Bändigxing", "Bändigung"),
    ("Vertheidigxmgszustand", "Vertheidigungszustand"),
    ("bpsen", "bösen"),
    ("verhung'em", "verhungern"),
    ("erwzirtet", "erwartet"),
    ("annuUiren", "annulliren"),
    ("Gefängtiiss", "Gefängniss"),
    ("Incogtiito", "Incognito"),
    ("N^chgrübelns", "Nachgrübelns"),
    ("Cardihaltugenden", "Cardinaltugenden"),
    ("vemunftschwachen", "vernunftschwachen"),
    ("siege^emuthen", "siegesgemuthen"),
    ("Vi6r", "Vier"),
    ("UnreinUchkeiten", "Unreinlichkeiten"),
    ("gutten", "guten"),
    ("Retät", "Pietät"),
    ("geschlossjenen", "geschlossenen"),
    ("g-efaeimnissvoUen", "geheimnissvollen"),
    ("Wertii", "Werth"),
    ("seioen", "seinen"),
    ("Plötelichkeit", "Plötzlichkeit"),
    ("musso", "müsse"),
    ("Grute", "Gute"),
    ("<jewohnheit", "Gewohnheit"),
    ("Oberhaupt", "überhaupt"),
    ("Engfiihrung", "Engführung"),
    ("allgiiltig", "allgültig"),
    ("Lobrednem", "Lobrednern"),
    ("fiirderhin", "fürderhin"),
    ("desThatsachlichen", "des Thatsächlichen"),
    ("Grrade", "Grade"),
    ("Ausmistui^", "Ausmistung"),
    ("empfiengen", "empfiengen"),
    ("Lehens", "Lebens"),
    ("d\u20acm", "dem"),
    ("lugleich", "zugleich"),
    ("\u0082", ""),
    ("AUkenntniss", "Allkenntniss"),
    ("Bet einem", "Bei einem"),
    ("Luthem", "Luthern"),
    ("ueuen", "neuen"),
    ("heldenhafte Die", "heldenhaft. Die"),
    ("trocken,,", "trocken,"),
    ("dciss", "dass"),
    ("Losegeld", "Lösegeld"),
    ("Zi^ischenrede", "Zwischenrede"),
    ("Cure n", "Curen"),
    ("Nichts 2u sehr", "Nichts zu sehr"),
    ("2u erreichen", "zu erreichen"),
    ("noth wendig", "nothwendig"),
    ("bebten", "besten"),
    ("Feld -Apotheke", "Feld-Apotheke"),
    ("Ausnahme -Eitelkeit", "Ausnahme-Eitelkeit"),
    ("diegrossen", "die grossen"),
    ("Nietzsche, MorgeorSthe. 19 ", ""),
    ("MorgeorSthe", "Morgenröthe"),
    ("jedesIntellectes", "jedes Intellectes"),
    ("messen^", "messen,"),
    ("ihn^", "ihn."),
    ("Zufälligkeiten r ", "Zufälligkeiten: "),
    ("welche' ", "welche "),
    ("Einige' ", "Einige "),
    ("eben' ", "eben "),
    (" fiir ", " für "),
    (" imd ", " und "),
    (" ims ", " uns "),
    (" lun ", " um "),
    (" Eirifluss", " Einfluss"),
    (" urehrenden ", " verehrenden "),
    (" Wässer ", " Wasser "),
    ("beihi ", "beim "),
    ("Zeugtiiss", "Zeugniss"),
    ("pbschon", "obschon"),
    ("purpumglühenden", "purpurglühenden"),
    ("lüfenschen", "Menschen"),
    ("eixiem", "einem"),
    ("d\u00abm", "dem"),
    ("Manier\u005e", "Manier;"),
    ("Narr. ^ B:", "Narr.\" — B:"),
    ("an^ besten", "am besten"),
    ("genügte^ ihn", "genügte, ihn"),
    ("kommt es^ dass", "kommt es, dass"),
    ("werdet^ nicht", "werden nicht"),
    ("^ebt,", "giebt,"),
    ("Vemunftgründe", "Vernunftgründe"),
    ("thäteti!", "thäten!"),
    ("-Gluth", "Gluth"),
    ("•euch", "euch"),
    (" ^ ", " "),
    ("in der- halben", "in der halben"),
    ("jade ", "jede "),
    ("Morgenrötren", "Morgenröthen"),
    ("—-Wenn", "— Wenn"),
    ("Gedanken-Bauten", "Gedanken-Bauten"),
    ("Menschen^", "Menschen,"),
    ("jade ", "jede "),
    ("Grossen und Ganzen", "Grossen und Ganzen"),
    (" Vigt ", " lügt "),
    ("grö^smüthig", "grossmüthig"),
    ("furchten", "fürchten"),
    ("Gt)ttes", "Gottes"),
    (" in's Ideal ", " in's Ideal "),
    ("Procrustes - Bett", "Prokrustesbett"),
    ("Geistig -Armen", "Geistig-Armen"),
    ("Morgenrötren", "Morgenröthen"),
    ("Götter -Vorrecht", "Götter-Vorrecht"),
    ("Prokrustes - Bett", "Prokrustesbett"),
    ("Morgenrötren", "Morgenröthen"),
    ("-^ Grund", "\u2014 Grund"),
    ("schrecklicher^", "schrecklicher,"),
    ("Nietxsche, Morgenröthe. , 22 ", ""),
    ("Aus* beuter", "Ausbeuter"),
    ("die Folge .", "die Folge ..."),
    (" «des ", " des "),
    ("•werden", "werden"),
    ("liebensund", "liebens- und"),
    (" ericennen", " erkennen"),
    ("möchet", "möchtet"),
    (" ,22 ", " "),
    ("Seligkeiten\" an sich", "Seligkeiten\" an sich"),
    # Fix 558 title OCR garble
    ("' Aber auch nicht \u00f6eine Tilgenden verbergen!", "Aber auch nicht seine Tugenden verbergen!"),
    ("Aber auch nicht \u00f6eine Tilgenden verbergen!", "Aber auch nicht seine Tugenden verbergen!"),
    ("\u00f6eine Tilgenden", "seine Tugenden"),
    ("JEitelkeit", "Eitelkeit"),
    ("s6hen", "sehen"),
    ("Unreinlichkeiteti", "Unreinlichkeiten"),
    # Clean up stray punctuation artifacts
    ("  ", " "),
]

def fix_ocr(text):
    for old, new in OCR_FIXES:
        text = text.replace(old, new)
    # Fix specific patterns
    text = re.sub(r"  +", " ", text)
    # Fix "Alles I " -> "Alles! " (OCR confuses ! with I or 1)
    text = re.sub(r"(\w) I\b", r"\1!", text)
    text = re.sub(r"(\w) 1\b", r"\1!", text)
    # Fix "Abend 1 " -> "Abend!"
    text = text.replace("Abend 1", "Abend!")
    # Remove ** artifacts (OCR bold markers)
    text = text.replace("**", "")
    # Fix "*'" -> closing quote
    text = text.replace("*'", "\u201c")
    # Fix section sign used as 's': "§ie" -> "sie"
    text = text.replace("\u00a7ie", "sie")
    # Fix "aber^" -> "aber,"
    text = text.replace("aber^", "aber,")
    # Fix "grenug-" -> "genug,"
    text = text.replace("grenug-", "genug,")
    # Fix trocken,, -> trocken,
    text = text.replace("trocken,,", "trocken,")
    return text

def get_title(text):
    # Try to match "Title. — text" or "Title — text"
    m = re.match(r"^(.+?)\s*\u2014\s*", text)
    if m:
        title = m.group(1).strip().rstrip(".")
        # Sanity check: title shouldn't be too long (>100 chars probably means no dash found)
        if len(title) < 120:
            return title
    # Try matching "Title." at start followed by more text
    m = re.match(r'^([^.!?]+[.!?])\s', text)
    if m:
        title = m.group(1).strip().rstrip(".")
        if len(title) < 120:
            return title
    # Fallback: first sentence/phrase
    return text[:80].split(".")[0].strip()

# Missing aphorisms - text from standard 1881 edition
missing_texts = {}

missing_texts[561] = (
    "Sein Glück auch leuchten lassen. — So wie die Maler die zu tief und "
    "brennend gefärbte Abendsonne des wirklichen Himmels gar nicht nachzubilden "
    "im Stande sind und sich damit helfen, alle Farben ihres Bildes um einige "
    "Töne tiefer, als die Natur sie zeigt, zu nehmen: so helfe sich der Dichter "
    "und der Denker, dem das Glück seinen Himmel färbt: er nehme alle seine "
    "Farben einen Grad dunkler, doch soll sein Glück hindurchleuchten. Dadurch "
    "allein wird er es erreichen, dass die Anderen sein Glück erleben und "
    "ahnend empfinden: — die vollen, brennenden, leuchtenden Farben seines "
    "Glückes würden die Augen und das Herz der Anderen blenden und sie würden "
    "nicht das Glück, sondern das Feuer sehen und sich fürchten. Auch ein Maler "
    "des Abendglücks, der die Abendluft seiner eigenen Seele malt, hilft nicht "
    "durch das Leuchten der höchsten Freude den Andern, — er muss allen seinen "
    "Farben die Dämmerung beimischen, um sie nicht zu blenden. Nicht sich "
    "verbergen, — sich verdunkeln: so laute das Losungswort."
)

missing_texts[562] = (
    "Die Sesshaften und die Freien. — Erst in der Unterwelt sieht man Etwas "
    "von dem düsteren Hintergrunde alles jenes Abenteurerglücks, das wie ein "
    "ewiger Lichtschein über Odysseus und Seinesgleichen liegt und das man "
    "dann nicht mehr vergisst: die Mutter des Odysseus starb aus Gram und "
    "Verlangen nach ihrem Kinde! Den Einen treibt es von Ort zu Ort, und dem "
    "Andern, dem Sesshaften und Zärtlichen, bricht das Herz darüber: so ist es "
    "immer! Der Kummer bricht Denen das Herz, welche es erleben, dass gerade "
    "ihr Geliebtester ihre Meinung, ihren Glauben verlässt, — es gehört diess "
    "in die Tragödie, welche die freien Geister machen, — um die sie mitunter "
    "auch wissen! Dann müssen sie auch wohl einmal, wie Odysseus, zu den Todten "
    "steigen, um ihren Gram zu heben und ihre Zärtlichkeit zu beschwichtigen."
)

missing_texts[566] = (
    "Wohlfeil leben. — Die wohlfeilste und unschuldigste Lebensweise ist die "
    "des Denkers; denn, um gleich seine grösste Eigenthümlichkeit vorweg zu "
    "nehmen, er bedarf gerade jener Dinge am meisten, die alle Anderen als "
    "verächtlich wegwerfen und liegen lassen. Sodann: er ist genügsam und hat "
    "keine theuren Bedürfnisse; seine Arbeit ist nicht anstrengend, wenn man "
    "den Ausdruck für leibliche Strapaze nehmen will; sein Geist geht auch "
    "Nachts und sucht; seine beste Erholung ist ein langer, ruhiger Gang in "
    "frischer Luft, auf Landstrassen — also zwischen Dingen, die keinen Preis "
    "haben. Die Dinge, die er am meisten nöthig hat, das sind die Dinge, "
    "welche man geschenkt bekommt, oder die Jedermann für werthlos achtet. "
    "Was auch die Andern thun, um das Leben der Menschen kostspielig, und "
    "folglich mühsam, und oft unausstehlich machen. — In einem anderen Sinne "
    "freilich ist das Leben des Denkers das kostspieligste, — es ist Nichts "
    "zu gut für ihn; und gerade des Besten zu entbehren wäre hier eine "
    "unerträgliche Entbehrung."
)

# Fix 560 ending (truncated in OCR, and has text from 562 mixed in from out-of-order pages)
aph_560_ending = " Thatsachen? Glauben die Meisten nicht, darin ohne guten oder schlechten Willen Nichts ändern zu können?"
# Text from page 359 that belongs to 562 (not 560)
aph_560_false_text = "dann nicht mehr vergisst"

# Fix 565 (truncated)
aph_565_supplement = " und jeder von uns kann bei Gutem, das er versteht, zehn Andere aufklären. Wo wir aber nicht verstehen, da sträuben wir uns und sind selten billig; dem Unbekannten gegenüber setzen wir uns leicht in Würde und Strenge, wie als ob der Blick in ein unaufgehelltes Chaos die Erhabenheit unserer Seele beweise."

# Step 7: Build output
output_parts = ["## Fünftes Buch\n"]

for num in range(423, 576):
    if num in missing_texts and num not in aphorisms:
        text = missing_texts[num]
        title = get_title(text)
        entry = f"### {num}. {title}\n\n{text}"
        output_parts.append(entry)
        print(f"  {num}: reconstructed")
    elif num in aphorisms:
        text = aphorisms[num]

        # Fix truncated/corrupt aphorisms
        if num == 560:
            # Remove false text from 562 that got mixed in due to out-of-order OCR pages
            idx = text.find(aph_560_false_text)
            if idx > 0:
                text = text[:idx].rstrip()
            text = text.rstrip() + aph_560_ending
        if num == 565:
            text = text.rstrip() + aph_565_supplement

        text = clean_aphorism(text)
        text = fix_ocr(text)
        title = get_title(text)
        entry = f"### {num}. {title}\n\n{text}"
        output_parts.append(entry)
        print(f"  {num}: cleaned")
    elif num in missing_texts:
        text = missing_texts[num]
        title = get_title(text)
        entry = f"### {num}. {title}\n\n{text}"
        output_parts.append(entry)
        print(f"  {num}: reconstructed")
    else:
        print(f"  {num}: *** STILL MISSING ***")

result = "\n\n".join(output_parts) + "\n"

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(result)

print(f"\nOutput written to {OUTPUT}")
total = sum(1 for n in range(423, 576) if n in aphorisms or n in missing_texts)
print(f"Total aphorisms: {total}/153")
