"""Download aphorisms 97-182 (Zweites Buch + Drittes Buch partial) from textlog.de."""
import re
import html
import urllib.request
import time
import os

BASE = "https://www.textlog.de/nietzsche/schriften/morgenroete/"
OUT_DIR = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/"

# Zweites Buch: aphorisms 97-148
# Drittes Buch: aphorisms 149-182
APHORISMS = [
    # === Zweites Buch ===
    ("97", "Man wird moralisch, — nicht weil man moralisch ist", "man-wird-moralisch-nicht-weil-man-moralisch-ist"),
    ("98", "Wandel der Moral", "wandel-der-moral"),
    ("99", "Worin wir Alle unvernünftig sind", "worin-wir-alle-unvernuenftig-sind"),
    ("100", "Vom Traume erwachen", "vom-traume-erwachen"),
    ("101", "Bedenklich", "bedenklich"),
    ("102", "Die ältesten moralischen Urteile", "die-aeltesten-moralischen-urteile"),
    ("103", "Es gibt zwei Arten von Leugnern der Sittlichkeit", "es-gibt-zwei-arten-von-leugnern-der-sittlichkeit"),
    ("104", "Unsere Wertschätzungen", "unsere-wertschaetzungen"),
    ("105", "Der Schein-Egoismus", "der-schein-egoismus"),
    ("106", "Gegen die Definitionen der moralischen Ziele", "gegen-die-definitionen-der-moralischen-ziele"),
    ("107", "Unser Anrecht auf unsere Torheit", "unser-anrecht-auf-unsere-torheit"),
    ("108", "Einige Thesen", "einige-thesen"),
    ("109", "Selbst-Beherrschung und Mäßigung und ihr letztes Motiv", "selbst-beherrschung-und-maessigung-und-ihr-letztes-motiv"),
    ("110", "Das, was sich widersetzt", "das-was-sich-widersetzt"),
    ("111", "An die Bewunderer der Objektivität", "an-die-bewunderer-der-objektivitaet"),
    ("112", "Zur Naturgeschichte von Pflicht und Recht", "zur-naturgeschichte-von-pflicht-und-recht"),
    ("113", "Das Streben nach Auszeichnung", "das-streben-nach-auszeichnung"),
    ("114", "Von der Erkenntnis des Leidenden", "von-der-erkenntnis-des-leidenden"),
    ("115", 'Das sogenannte „Ich"', "das-sogenannte-ich"),
    ("116", 'Die unbekannte Welt des „Subjekts"', "die-unbekannte-welt-des-subjekts"),
    ("117", "Im Gefängnis", "im-gefaengnis"),
    ("118", "Was ist denn der Nächste", "was-ist-denn-der-naechste"),
    ("119", "Erleben und Erdichten", "erleben-und-erdichten"),
    ("120", "Zur Beruhigung des Skeptikers", "zur-beruhigung-des-skeptikers"),
    ("121", "Ursache und Wirkung", "ursache-und-wirkung"),
    ("122", "Die Zwecke in der Natur", "die-zwecke-in-der-natur"),
    ("123", "Vernunft", "vernunft"),
    ("124", "Was ist Wollen", "was-ist-wollen"),
    ("125", 'Vom „Reich der Freiheit"', "vom-reich-der-freiheit"),
    ("126", "Vergessen", "vergessen"),
    ("127", "Nach Zwecken", "nach-zwecken"),
    ("128", "Der Traum und die Verantwortlichkeit", "der-traum-und-die-verantwortlichkeit"),
    ("129", "Der angebliche Kampf der Motive", "der-angebliche-kampf-der-motive"),
    ("130", "Zwecke", "zwecke-willen"),
    ("131", "Die moralischen Moden", "die-moralischen-moden"),
    ("132", "Die ausklingende Christlichkeit in der Moral", "die-ausklingende-christlichkeit-in-der-moral"),
    ("133", '„Nicht mehr an sich denken"', "nicht-mehr-an-sich-denken"),
    ("134", "In wie fern man sich vor dem Mitleiden zu hüten hat", "in-wie-fern-man-sich-vor-dem-mitleiden-zu-hueten-hat"),
    ("135", "Das Bemitleidetwerden", "das-bemitleidetwerden"),
    ("136", "Das Glück im Mitleiden", "das-glueck-im-mitleiden"),
    ("137", 'Warum das „Ich" verdoppeln', "warum-das-ich-verdoppeln"),
    ("138", "Das Zärtlicherwerden", "das-zaertlicherwerden"),
    ("139", "Angeblich höher", "angeblich-hoeher"),
    ("140", "Loben und Tadeln", "loben-und-tadeln"),
    ("141", "Schöner, aber weniger wert", "schoener-aber-weniger-wert"),
    ("142", "Mitempfindung", "mitempfindung"),
    ("143", "Wehe, wenn dieser Trieb erst wütet", "wehe-wenn-dieser-trieb-erst-wuetet"),
    ("144", "Die Ohren vor dem Jammer zuhalten", "die-ohren-vor-dem-jammer-zuhalten"),
    ("145", "Unegoistisch", "unegoistisch"),
    ("146", "Auch über den Nächsten hinweg", "auch-ueber-den-naechsten-hinweg"),
    ("147", "Ursache des Altruismus", "ursache-des-altruismus"),
    ("148", "Ausblick in die Ferne", "ausblick-in-die-ferne"),
    # === Drittes Buch ===
    ("149", "Kleine abweichende Handlungen tun not", "kleine-abweichende-handlungen-tun-not"),
    ("150", "Der Zufall der Ehen", "der-zufall-der-ehen"),
    ("151", "Hier sind neue Ideale zu erfinden", "hier-sind-neue-ideale-zu-erfinden"),
    ("152", "Eidformel", "eidformel"),
    ("153", "Ein Unzufriedener", "ein-unzufriedener"),
    ("154", "Trost der Gefährdeten", "trost-der-gefaehrdeten"),
    ("155", "Erloschene Skepsis", "erloschene-skepsis"),
    ("156", "Aus Übermut böse", "aus-uebermut-boese"),
    ("157", 'Kultus der „Naturlaute"', "kultus-der-naturlaute"),
    ("158", "Klima des Schmeichlers", "klima-des-schmeichlers"),
    ("159", "Die Totenerwecker", "die-totenerwecker"),
    ("160", "Eitel, begehrlich und wenig weise", "eitel-begehrlich-und-wenig-weise"),
    ("161", "Schönheit gemäß dem Zeitalter", "schoenheit-gemaess-dem-zeitalter"),
    ("162", "Die Ironie der Gegenwärtigen", "die-ironie-der-gegenwaertigen"),
    ("163", "Gegen Rousseau", "gegen-rousseau"),
    ("164", "Vielleicht verfrüht", "vielleicht-verfrueht"),
    ("165", "Welche Moral nicht langweilt", "welche-moral-nicht-langweilt"),
    ("166", "Am Scheidewege", "am-scheidewege"),
    ("167", "Die unbedingten Huldigungen", "die-unbedingten-huldigungen"),
    ("168", "Ein Vorbild", "ein-vorbild"),
    ("169", "Das Griechische uns sehr fremd", "das-griechische-uns-sehr-fremd"),
    ("170", "Andere Perspektive des Gefühls", "andere-perspektive-des-gefuehls"),
    ("171", "Die Ernährung des modernen Menschen", "die-ernaehrung-des-modernen-menschen"),
    ("172", "Tragödie und Musik", "tragoedie-und-musik"),
    ("173", "Die Lobredner der Arbeit", "die-lobredner-der-arbeit"),
    ("174", "Moralische Mode einer handeltreibenden Gesellschaft", "moralische-mode-einer-handeltreibenden-gesellschaft"),
    ("175", "Grundgedanke einer Kultur der Handeltreibenden", "grundgedanke-einer-kultur-der-handeltreibenden"),
    ("176", "Die Kritik über die Väter", "die-kritik-ueber-die-vaeter"),
    ("177", "Einsamkeit lernen", "einsamkeit-lernen"),
    ("178", "Die Täglich-Abgenutzten", "die-taeglich-abgenutzten"),
    ("179", "So wenig als möglich Staat", "so-wenig-als-moeglich-staat"),
    ("180", "Die Kriege", "die-kriege"),
    ("181", "Regieren", "regieren"),
    ("182", "Die grobe Konsequenz", "die-grobe-konsequenz"),
]


def extract_text(html_content: str) -> str:
    """Extract article text from HTML, handling Docusaurus v2 layout."""
    # Try to find the main article content
    match = re.search(r'<article[^>]*>(.*?)</article>', html_content, re.DOTALL)
    if not match:
        return ""
    article = match.group(1)

    # Find the markdown content div
    md_match = re.search(
        r'class="theme-doc-markdown markdown">(.*?)(?:<nav|<footer|</article>)',
        article, re.DOTALL
    )
    if md_match:
        text = md_match.group(1)
    else:
        text = article

    # Remove navigation elements (prev/next links)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
    # Remove h1/h2 (page titles)
    text = re.sub(r'<h[12][^>]*>.*?</h[12]>', '', text, flags=re.DOTALL)
    # Remove h3 headers (aphorism number headers from textlog)
    text = re.sub(r'<h3[^>]*>.*?</h3>', '', text, flags=re.DOTALL)
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Remove leading aphorism number if present (e.g., "97." at start)
    text = re.sub(r'^\d+\.\s*', '', text)

    return text


def download_aphorism(slug: str) -> str:
    """Download and extract a single aphorism page."""
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

    # Zweites Buch header
    all_text.append("\n---\n\n## Zweites Buch\n\n")

    total = len(APHORISMS)
    switched_to_book3 = False

    for i, (num, title, slug) in enumerate(APHORISMS):
        # Add Drittes Buch header before aphorism 149
        if num == "149" and not switched_to_book3:
            all_text.append("\n---\n\n## Drittes Buch\n\n")
            switched_to_book3 = True

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

        # Small delay to be respectful to the server
        time.sleep(0.5)
        if i % 10 == 9:
            time.sleep(1)

    # Write output to a separate file first
    output = "".join(all_text)
    out_path = os.path.join(OUT_DIR, "_zweites_drittes_buch.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n=== Done! Written to {out_path} ===")
    print(f"Total characters: {len(output)}")
    print(f"Aphorisms processed: {total}")
    print(f"\nTo append to original.md, run:")
    print(f"  # First remove old Fünftes Buch placeholder section, then insert this text")


if __name__ == "__main__":
    main()
