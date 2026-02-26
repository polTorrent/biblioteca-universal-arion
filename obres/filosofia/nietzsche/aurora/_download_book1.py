"""Download all aphorisms of Erstes Buch from textlog.de and extract text."""
import re
import html
import urllib.request
import time
import os

BASE = "https://www.textlog.de/nietzsche/schriften/morgenroete/"
OUT_DIR = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/"

APHORISMS = [
    ("1", "Nachträgliche Vernünftigkeit", "nachtraegliche-vernuenftigkeit"),
    ("2", "Vorurteil der Gelehrten", "vorurteil-der-gelehrten"),
    ("3", "Alles hat seine Zeit", "alles-hat-seine-zeit"),
    ("4", "Gegen die erträumte Disharmonie der Sphären", "gegen-die-ertraeumte-disharmonie-der-sphaeren"),
    ("5", "Seid dankbar", "seid-dankbar"),
    ("6", "Der Taschenspieler und sein Widerspiel", "der-taschenspieler-und-sein-widerspiel"),
    ("7", "Umlernen des Raumgefühls", "umlernen-des-raumgefuehls"),
    ("8", "Transfiguration", "transfiguration"),
    ("9", "Begriff der Sittlichkeit der Sitte", "begriff-der-sittlichkeit-der-sitte"),
    ("10", "Gegenbewegung zwischen Sinn der Sittlichkeit und Sinn der Kausalität", "gegenbewegung-zwischen-sinn-der-sittlichkeit-und-sinn-der-kausalitaet"),
    ("11", "Volksmoral und Volksmedizin", "volksmoral-und-volksmedizin"),
    ("12", "Die Folge als Zutat", "die-folge-als-zutat"),
    ("13", "Zur neuen Erziehung des Menschengeschlechts", "zur-neuen-erziehung-des-menschengeschlechts"),
    ("14", "Bedeutung des Wahnsinns in der Geschichte der Moralität", "bedeutung-des-wahnsinns-in-der-geschichte-der-moralitaet"),
    ("15", "Die ältesten Trostmittel", "die-aeltesten-trostmittel"),
    ("16", "Erster Satz der Zivilisation", "erster-satz-der-zivilisation"),
    ("17", "Die gute und die böse Natur", "die-gute-und-die-boese-natur"),
    ("18", "Die Moral des freiwilligen Leidens", "die-moral-des-freiwilligen-leidens"),
    ("19", "Sittlichkeit und Verdummung", "sittlichkeit-und-verdummung"),
    ("20", "Freitäter und Freidenker", "freitaeter-und-freidenker"),
    ("21", "Erfüllung des Gesetzes", "erfuellung-des-gesetzes"),
    ("22", "Werke und Glaube", "werke-und-glaube"),
    ("23", "Worin wir am feinsten sind", "worin-wir-am-feinsten-sind"),
    ("24", "Der Beweis einer Vorschrift", "der-beweis-einer-vorschrift"),
    ("25", "Sitte und Schönheit", "sitte-und-schoenheit"),
    ("26", "Die Tiere und die Moral", "die-tiere-und-die-moral"),
    ("27", "Der Wert im Glauben an übermenschliche Leidenschaften", "der-wert-im-glauben-an-uebermenschliche-leidenschaften"),
    ("28", "Die Stimmung als Argument", "die-stimmung-als-argument"),
    ("29", "Die Schauspieler der Tugend und der Sünde", "die-schauspieler-der-tugend-und-der-suende"),
    ("30", "Die verfeinerte Grausamkeit als Tugend", "die-verfeinerte-grausamkeit-als-tugend"),
    ("31", "Der Stolz auf den Geist", "der-stolz-auf-den-geist"),
    ("32", "Der Hemmschuh", "der-hemmschuh"),
    ("33", "Die Verachtung der Ursachen, der Folgen und der Wirklichkeit", "die-verachtung-der-ursachen-der-folgen-und-der-wirklichkeit"),
    ("34", "Moralische Gefühle und moralische Begriffe", "moralische-gefuehle-und-moralische-begriffe"),
    ("35", "Gefühle und deren Abkunft von Urteilen", "gefuehle-und-deren-abkunft-von-urteilen"),
    ("36", "Eine Narrheit der Pietät mit Hintergedanken", "eine-narrheit-der-pietaet-mit-hintergedanken"),
    ("37", "Falsche Schlüsse aus der Nützlichkeit", "falsche-schluesse-aus-der-nuetzlichkeit"),
    ("38", "Die Triebe durch die moralischen Urteile umgestaltet", "die-triebe-durch-die-moralischen-urteile-umgestaltet"),
    ("39", "Das Vorurteil vom «reinen Geiste»", "das-vorurteil-vom-reinen-geiste"),
    ("40", "Das Grübeln über Gebräuche", "das-gruebeln-ueber-gebraeuche"),
    ("41", "Zur Wertbestimmung der vita contemplativa", "zur-wertbestimmung-der-vita-contemplativa"),
    ("42", "Herkunft der vita contemplativa", "herkunft-der-vita-contemplativa"),
    ("43", "Wie viele Kräfte jetzt im Denker zusammenkommen müssen", "wie-viele-kraefte-jetzt-im-denker-zusammenkommen-muessen"),
    ("44", "Ursprung und Bedeutung", "ursprung-und-bedeutung"),
    ("45", "Ein Tragödien-Ausgang der Erkenntnis", "ein-tragoedien-ausgang-der-erkenntnis"),
    ("46", "Zweifel am Zweifel", "zweifel-am-zweifel"),
    ("47", "Die Worte liegen uns im Wege", "die-worte-liegen-uns-im-wege"),
    ("48", "«Erkenne dich selbst» ist die ganze Wissenschaft", "erkenne-dich-selbst-ist-die-ganze-wissenschaft"),
    ("49", "Das neue Grundgefühl: unsere endgültige Vergänglichkeit", "das-neue-grundgefuehl-unsere-endgueltige-vergaenglichkeit"),
    ("50", "Der Glaube an den Rausch", "der-glaube-an-den-rausch"),
    ("51", "So wie wir noch sind!", "so-wie-wir-noch-sind"),
    ("52", "Wo sind die neuen Ärzte der Seele?", "wo-sind-die-neuen-aerzte-der-seele"),
    ("53", "Missbrauch der Gewissenhaften", "missbrauch-der-gewissenhaften"),
    ("54", "Die Gedanken über die Krankheit", "die-gedanken-ueber-die-krankheit"),
    ("55", "Die «Wege»", "die-wege"),
    ("56", "Der Apostat des freien Geistes", "der-apostat-des-freien-geistes"),
    ("57", "Andere Furcht, andere Sicherheit", "andere-furcht-andere-sicherheit"),
    ("58", "Das Christentum und die Affekte", "das-christentum-und-die-affekte"),
    ("59", "Irrtum als Labsal", "irrtum-als-labsal"),
    ("60", "Aller Geist wird endlich leiblich sichtbar", "aller-geist-wird-endlich-leiblich-sichtbar"),
    ("61", "Das Opfer, das not tut", "das-opfer-das-not-tut"),
    ("62", "Vom Ursprung der Religionen", "vom-ursprung-der-religionen"),
    ("63", "Nächsten-Hass", "naechsten-hass"),
    ("64", "Die Verzweifelnden", "die-verzweifelnden"),
    ("65", "Brahmanen- und Christentum", "brahmanen-und-christentum"),
    ("66", "Fähigkeit der Vision", "faehigkeit-der-vision"),
    ("67", "Preis der Gläubigen", "preis-der-glaeubigen"),
    ("68", "Der erste Christ", "der-erste-christ"),
    ("69", "Unnachahmlich", "unnachahmlich"),
    ("70", "Wozu ein grober Intellekt nütze ist", "wozu-ein-grober-intellekt-nuetze-ist"),
    ("71", "Die christliche Rache an Rom", "die-christliche-rache-an-rom"),
    ("72", "Das «Nach-dem-Tode»", "das-nach-dem-tode"),
    ("73", "Für die «Wahrheit»", "fuer-die-wahrheit"),
    ("74", "Christlicher Hintergedanke", "christlicher-hintergedanke"),
    ("75", "Nicht europäisch und nicht vornehm", "nicht-europaeisch-und-nicht-vornehm"),
    ("76", "Böse denken heißt böse machen", "boese-denken-heisst-boese-machen"),
    ("77", "Von den Seelen-Martern", "von-den-seelen-martern"),
    ("78", "Die strafende Gerechtigkeit", "die-strafende-gerechtigkeit"),
    ("79", "Ein Vorschlag", "ein-vorschlag"),
    ("80", "Der mitleidige Christ", "der-mitleidige-christ"),
    ("81", "Humanität des Heiligen", "humanitaet-des-heiligen"),
    ("82", "Der geistliche Überfall", "der-geistliche-ueberfall"),
    ("83", "Arme Menschheit", "arme-menschheit"),
    ("84", "Die Philologie des Christentums", "die-philologie-des-christentums"),
    ("85", "Feinheit im Mangel", "feinheit-im-mangel"),
    ("86", "Die christlichen Interpreten des Leibes", "die-christlichen-interpreten-des-leibes"),
    ("87", "Das sittliche Wunder", "das-sittliche-wunder"),
    ("88", "Luther der große Wohltäter", "luther-der-grosse-wohltaeter"),
    ("89", "Zweifel als Sünde", "zweifel-als-suende"),
    ("90", "Egoismus gegen Egoismus", "egoismus-gegen-egoismus"),
    ("91", "Die Redlichkeit Gottes", "die-redlichkeit-gottes"),
    ("92", "Am Sterbebette des Christentums", "am-sterbebette-des-christentums"),
    ("93", "Was ist Wahrheit?", "was-ist-wahrheit"),
    ("94", "Heilmittel der Verstimmten", "heilmittel-der-verstimmten"),
    ("95", "Die historische Widerlegung als die endgültige", "die-historische-widerlegung-als-die-endgueltige"),
    ("96", "In hoc signo vinces", "in-hoc-signo-vinces"),
]


def extract_text(html_content: str) -> str:
    """Extract article text from HTML."""
    match = re.search(r'<article[^>]*>(.*?)</article>', html_content, re.DOTALL)
    if not match:
        return ""
    text = match.group(1)
    # Remove h1/h2/h3 headers (we'll add our own)
    text = re.sub(r'<h[1-3][^>]*>.*?</h[1-3]>', '', text, flags=re.DOTALL)
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Remove remaining HTML
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def download_aphorism(slug: str) -> str:
    """Download and extract a single aphorism."""
    url = BASE + slug
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR downloading {slug}: {e}")
        return ""


def main():
    all_text = []
    all_text.append("# Morgenröthe\n## Gedanken über die moralischen Vorurtheile\n### Friedrich Nietzsche (1881)\n\n")

    # Read the Vorrede we already have
    print("=== Extracting Vorrede ===")
    vorrede_path = os.path.join(OUT_DIR, "_vorrede_raw.html")
    with open(vorrede_path) as f:
        vorrede_html = f.read()
    vorrede_text = extract_text(vorrede_html)
    all_text.append("## Vorrede\n\n")
    # The vorrede has numbered sections - add them back
    # The text already contains section markers
    all_text.append(vorrede_text + "\n\n")

    # Download Book 1
    all_text.append("\n---\n\n## Erstes Buch\n\n")

    total = len(APHORISMS)
    for i, (num, title, slug) in enumerate(APHORISMS):
        print(f"  [{i+1}/{total}] Downloading {num}. {title}...")
        html_content = download_aphorism(slug)
        if html_content:
            text = extract_text(html_content)
            if text:
                all_text.append(f"### {num}. {title}\n\n{text}\n\n")
            else:
                print(f"    WARNING: Could not extract text for {num}")
                all_text.append(f"### {num}. {title}\n\n[Text not available]\n\n")
        else:
            all_text.append(f"### {num}. {title}\n\n[Download failed]\n\n")

        # Small delay to be respectful
        if i % 10 == 9:
            time.sleep(1)

    # Write output
    output = "".join(all_text)
    out_path = os.path.join(OUT_DIR, "original.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n=== Done! Written to {out_path} ===")
    print(f"Total characters: {len(output)}")


if __name__ == "__main__":
    main()
