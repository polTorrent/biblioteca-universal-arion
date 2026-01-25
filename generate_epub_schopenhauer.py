#!/usr/bin/env python3
"""
Generador d'EPUB per a 'Sobre la quàdruple arrel del principi de raó suficient'
d'Arthur Schopenhauer.
"""

import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Directoris
OUTPUT_DIR = Path("output/schopenhauer")
EPUB_DIR = OUTPUT_DIR / "epub"

# Metadades
METADATA = {
    "title": "Sobre la quàdruple arrel del principi de raó suficient",
    "title_original": "Über die vierfache Wurzel des Satzes vom zureichenden Grunde",
    "author": "Arthur Schopenhauer",
    "translator": "Pipeline Editorial IA",
    "language": "ca",
    "language_original": "de",
    "publisher": "Editorial Clàssica",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "identifier": f"urn:uuid:{uuid4()}",
    "rights": "Traducció sota llicència CC BY-SA 4.0",
    "description": "Traducció catalana de la dissertació doctoral de Schopenhauer (1813/1847), "
                   "obra fonamental per entendre la seva filosofia.",
}


def create_epub_structure():
    """Crea l'estructura de directoris de l'EPUB."""
    dirs = [
        EPUB_DIR / "META-INF",
        EPUB_DIR / "OEBPS",
        EPUB_DIR / "OEBPS" / "text",
        EPUB_DIR / "OEBPS" / "styles",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def create_mimetype():
    """Crea el fitxer mimetype."""
    (EPUB_DIR / "mimetype").write_text("application/epub+zip")


def create_container_xml():
    """Crea META-INF/container.xml."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
    (EPUB_DIR / "META-INF" / "container.xml").write_text(content)


def create_css():
    """Crea els estils CSS."""
    css = '''/* Estils per a Schopenhauer */
@charset "UTF-8";

body {
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.8;
    margin: 1.5em;
    color: #333;
    text-align: justify;
}

h1 {
    font-size: 1.8em;
    text-align: center;
    margin: 1.5em 0 1em 0;
    color: #1a1a2e;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 0.5em;
}

h2 {
    font-size: 1.4em;
    color: #16213e;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

h3 {
    font-size: 1.2em;
    color: #0f3460;
    font-style: italic;
}

.title-page {
    text-align: center;
    margin-top: 20%;
}

.title-page h1 {
    font-size: 1.6em;
    border: none;
    margin-bottom: 0.3em;
}

.title-page .subtitle {
    font-size: 1.1em;
    font-style: italic;
    color: #666;
    margin-bottom: 2em;
}

.title-page .author {
    font-size: 1.4em;
    margin: 1em 0;
}

.section-number {
    font-weight: bold;
    color: #0f3460;
}

.section-title {
    font-style: italic;
}

blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #ccc;
    font-style: italic;
    color: #555;
}

.footnote {
    font-size: 0.85em;
    color: #666;
}

.latin, .german {
    font-style: italic;
}

p {
    margin: 0.8em 0;
    text-indent: 1.5em;
}

p:first-of-type {
    text-indent: 0;
}

.chapter-intro {
    text-align: center;
    font-style: italic;
    margin: 2em 0;
}

.toc {
    list-style: none;
    padding: 0;
}

.toc li {
    margin: 0.5em 0;
    padding-left: 1em;
}

.toc a {
    text-decoration: none;
    color: #16213e;
}

.toc .chapter {
    font-weight: bold;
    margin-top: 1em;
}

.colophon {
    margin-top: 3em;
    text-align: center;
    font-size: 0.9em;
    color: #888;
}
'''
    (EPUB_DIR / "OEBPS" / "styles" / "main.css").write_text(css, encoding="utf-8")


def extract_chapters_from_translation(text: str) -> list[tuple[str, str]]:
    """Extreu els capítols del text traduït."""
    # Buscar patrons de capítol
    chapter_pattern = re.compile(r'={50,}\n(CHAPTER [IVX]+[^\n]*)\n={50,}', re.MULTILINE)

    # Dividir per capítols
    parts = chapter_pattern.split(text)

    chapters = []
    current_title = "Introducció"

    i = 0
    while i < len(parts):
        if parts[i].startswith("CHAPTER"):
            current_title = parts[i].strip()
            i += 1
            if i < len(parts):
                content = parts[i].strip()
                if content:
                    chapters.append((current_title, content))
            i += 1
        else:
            # Contingut abans del primer capítol
            content = parts[i].strip()
            if content and len(content) > 200:
                chapters.append((current_title, content))
            i += 1

    return chapters


def xhtml_template(title: str, content: str) -> str:
    """Genera plantilla XHTML."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ca">
<head>
  <meta charset="UTF-8"/>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="../styles/main.css"/>
</head>
<body>
{content}
</body>
</html>'''


def format_section_content(text: str) -> str:
    """Formata el contingut d'una secció com HTML."""
    # Netejar separadors
    text = re.sub(r'={50,}', '', text)

    # Convertir seccions § a headers
    text = re.sub(
        r'^(§\s*\d+\.?\s*)([^\n]+)',
        r'<h3><span class="section-number">\1</span><span class="section-title">\2</span></h3>',
        text,
        flags=re.MULTILINE
    )

    # Convertir paràgrafs
    paragraphs = text.split('\n\n')
    html_parts = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para.startswith('<h'):
            html_parts.append(para)
        else:
            # Escapar HTML i afegir paràgraf
            para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            para = para.replace('&lt;h3&gt;', '<h3>').replace('&lt;/h3&gt;', '</h3>')
            para = para.replace('&lt;span', '<span').replace('&lt;/span&gt;', '</span>')
            para = para.replace('class=&quot;', 'class="').replace('&quot;&gt;', '">')
            html_parts.append(f'<p>{para}</p>')

    return '\n'.join(html_parts)


def create_title_page():
    """Crea la pàgina de títol."""
    content = f'''<div class="title-page">
  <h1>Sobre la quàdruple arrel<br/>del principi de raó suficient</h1>
  <p class="subtitle">Über die vierfache Wurzel des Satzes vom zureichenden Grunde</p>
  <p class="author">Arthur Schopenhauer</p>
  <p style="margin-top: 2em; font-size: 0.9em;">Una dissertació filosòfica</p>
  <p style="margin-top: 1em; font-size: 0.9em;">(1813 / 1847)</p>
  <p style="margin-top: 3em;">Traducció al català</p>
  <p style="margin-top: 2em; font-size: 0.9em;">{METADATA["publisher"]}<br/>{METADATA["date"]}</p>
</div>'''
    (EPUB_DIR / "OEBPS" / "text" / "title.xhtml").write_text(
        xhtml_template("Portada", content), encoding="utf-8"
    )


def create_intro():
    """Crea la introducció."""
    content = '''<section>
  <h1>Nota sobre l'obra</h1>

  <p><em>Sobre la quàdruple arrel del principi de raó suficient</em> (en alemany: <em>Über die vierfache Wurzel des Satzes vom zureichenden Grunde</em>) és la dissertació doctoral d'Arthur Schopenhauer, presentada a la Universitat de Jena el 1813.</p>

  <p>L'obra és fonamental per entendre el sistema filosòfic de Schopenhauer, especialment la seva obra magna <em>El món com a voluntat i representació</em> (1818). El mateix Schopenhauer considerava aquest tractat com la clau per comprendre la seva filosofia.</p>

  <h2>Les quatre arrels</h2>
  <p>Schopenhauer distingeix quatre formes diferents del principi de raó suficient, cadascuna aplicable a una classe diferent d'objectes per al subjecte:</p>

  <ol>
    <li><strong>Principi de raó suficient del esdevenir</strong> (principium rationis sufficientis fiendi) — La llei de causalitat aplicada als objectes de la percepció empírica.</li>
    <li><strong>Principi de raó suficient del conèixer</strong> (principium rationis sufficientis cognoscendi) — La relació lògica entre judicis i conceptes.</li>
    <li><strong>Principi de raó suficient del ser</strong> (principium rationis sufficientis essendi) — Les relacions matemàtiques en l'espai i el temps.</li>
    <li><strong>Principi de raó suficient de l'actuar</strong> (principium rationis sufficientis agendi) — La llei de motivació que governa les accions de la voluntat.</li>
  </ol>

  <h2>Sobre aquesta traducció</h2>
  <p>Aquesta traducció catalana s'ha realitzat a partir de la traducció anglesa de Mme. Karl Hillebrand (1907), basada en la segona edició alemanya revisada (1847). S'ha procurat mantenir la precisió terminològica pròpia del discurs filosòfic.</p>
</section>'''
    (EPUB_DIR / "OEBPS" / "text" / "intro.xhtml").write_text(
        xhtml_template("Introducció", content), encoding="utf-8"
    )


def create_chapters(translation_file: Path) -> list[str]:
    """Crea els fitxers dels capítols."""
    text = translation_file.read_text(encoding="utf-8")

    # Buscar tots els blocs de capítol/secció
    section_pattern = re.compile(
        r'={60}\n([^\n]+)\n={60}\n\n(.*?)(?=\n={60}|\Z)',
        re.DOTALL
    )

    sections = section_pattern.findall(text)

    # Agrupar per capítols
    chapters = {}
    current_chapter = "PREFACI"

    for title, content in sections:
        title = title.strip()
        content = content.strip()

        if "CHAPTER" in title:
            # Extreure número de capítol
            match = re.search(r'CHAPTER ([IVX]+)', title)
            if match:
                current_chapter = f"CHAPTER {match.group(1)}"
                if current_chapter not in chapters:
                    chapters[current_chapter] = []

        if current_chapter not in chapters:
            chapters[current_chapter] = []

        chapters[current_chapter].append((title, content))

    # Crear fitxers de capítol
    chapter_files = []
    chapter_titles = {
        "PREFACI": "Prefaci",
        "CHAPTER I": "Capítol I: Introducció",
        "CHAPTER II": "Capítol II: Visió històrica del principi",
        "CHAPTER III": "Capítol III: Inadequació de les formulacions anteriors",
        "CHAPTER IV": "Capítol IV: Primera classe d'objectes i el principi del esdevenir",
        "CHAPTER V": "Capítol V: Segona classe d'objectes i el principi del conèixer",
        "CHAPTER VI": "Capítol VI: Tercera classe d'objectes i el principi del ser",
        "CHAPTER VII": "Capítol VII: Quarta classe d'objectes i el principi de l'actuar",
        "CHAPTER VIII": "Capítol VIII: Observacions generals i resultats",
    }

    for i, (chapter_key, chapter_sections) in enumerate(chapters.items(), 1):
        chapter_title = chapter_titles.get(chapter_key, chapter_key)

        content_parts = [f'<h1>{chapter_title}</h1>']

        for section_title, section_content in chapter_sections:
            # Formatar secció
            formatted = format_section_content(section_content)
            if "§" in section_title:
                # Extreure número i títol de secció
                content_parts.append(f'<section>\n{formatted}\n</section>')
            else:
                content_parts.append(formatted)

        filename = f"chapter{i:02d}.xhtml"
        chapter_files.append(filename)

        (EPUB_DIR / "OEBPS" / "text" / filename).write_text(
            xhtml_template(chapter_title, '\n'.join(content_parts)),
            encoding="utf-8"
        )

    print(f"  ✓ Creats {len(chapter_files)} capítols")
    return chapter_files


def create_nav(chapter_files: list[str]):
    """Crea la taula de continguts navegable."""
    chapter_titles = [
        "Prefaci i introducció",
        "Visió històrica del principi",
        "Inadequació de les formulacions anteriors",
        "Primera classe d'objectes",
        "Segona classe d'objectes",
        "Tercera classe d'objectes",
        "Quarta classe d'objectes",
        "Observacions generals i resultats",
    ]

    toc_items = ['<li><a href="title.xhtml">Portada</a></li>',
                 '<li><a href="intro.xhtml">Nota sobre l\'obra</a></li>']

    for i, filename in enumerate(chapter_files):
        title = chapter_titles[i] if i < len(chapter_titles) else f"Capítol {i+1}"
        toc_items.append(f'<li class="chapter"><a href="{filename}">Capítol {i+1}: {title}</a></li>')

    toc_items.append('<li><a href="colophon.xhtml">Colofó</a></li>')

    content = f'''<nav epub:type="toc" id="toc">
  <h1>Taula de continguts</h1>
  <ol class="toc">
    {chr(10).join(toc_items)}
  </ol>
</nav>'''
    (EPUB_DIR / "OEBPS" / "text" / "nav.xhtml").write_text(
        xhtml_template("Taula de continguts", content), encoding="utf-8"
    )


def create_colophon():
    """Crea el colofó."""
    content = f'''<div class="colophon">
  <h1>Colofó</h1>

  <p><em>Sobre la quàdruple arrel del principi de raó suficient</em></p>
  <p>Arthur Schopenhauer</p>

  <hr style="width: 30%; margin: 2em auto;"/>

  <p>Obra original (1813/1847): Domini públic</p>
  <p>Traducció anglesa (1907): Domini públic</p>
  <p>Traducció catalana: Llicència CC BY-SA 4.0</p>

  <p style="margin-top: 2em;">
    Aquesta edició ha estat produïda amb el suport<br/>
    del Pipeline Editorial IA
  </p>

  <p style="margin-top: 2em;">
    <strong>{METADATA["publisher"]}</strong><br/>
    {METADATA["date"]}
  </p>
</div>'''
    (EPUB_DIR / "OEBPS" / "text" / "colophon.xhtml").write_text(
        xhtml_template("Colofó", content), encoding="utf-8"
    )


def create_content_opf(chapter_files: list[str]):
    """Crea el fitxer content.opf."""

    # Manifest items
    manifest_items = [
        '<item id="css" href="styles/main.css" media-type="text/css"/>',
        '<item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="title" href="text/title.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="intro" href="text/intro.xhtml" media-type="application/xhtml+xml"/>',
    ]

    for i, filename in enumerate(chapter_files, 1):
        manifest_items.append(
            f'<item id="chapter{i:02d}" href="text/{filename}" media-type="application/xhtml+xml"/>'
        )

    manifest_items.append('<item id="colophon" href="text/colophon.xhtml" media-type="application/xhtml+xml"/>')

    # Spine items
    spine_items = ['<itemref idref="title"/>', '<itemref idref="nav"/>', '<itemref idref="intro"/>']
    for i in range(1, len(chapter_files) + 1):
        spine_items.append(f'<itemref idref="chapter{i:02d}"/>')
    spine_items.append('<itemref idref="colophon"/>')

    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">{METADATA["identifier"]}</dc:identifier>
    <dc:title>{METADATA["title"]}</dc:title>
    <dc:creator>{METADATA["author"]}</dc:creator>
    <dc:contributor>Traductor: {METADATA["translator"]}</dc:contributor>
    <dc:language>{METADATA["language"]}</dc:language>
    <dc:publisher>{METADATA["publisher"]}</dc:publisher>
    <dc:date>{METADATA["date"]}</dc:date>
    <dc:rights>{METADATA["rights"]}</dc:rights>
    <dc:description>{METADATA["description"]}</dc:description>
    <meta property="dcterms:modified">{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
  </metadata>
  <manifest>
    {chr(10).join(manifest_items)}
  </manifest>
  <spine>
    {chr(10).join(spine_items)}
  </spine>
</package>'''
    (EPUB_DIR / "OEBPS" / "content.opf").write_text(content, encoding="utf-8")


def create_epub_file():
    """Empaqueta tot en un fitxer EPUB."""
    epub_path = OUTPUT_DIR / "Schopenhauer_Rao_Suficient.epub"

    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # El mimetype ha de ser el primer fitxer i sense compressió
        epub.write(EPUB_DIR / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)

        # Afegir la resta de fitxers
        for root, dirs, files in os.walk(EPUB_DIR):
            for file in files:
                if file == "mimetype":
                    continue
                file_path = Path(root) / file
                arc_name = str(file_path.relative_to(EPUB_DIR))
                epub.write(file_path, arc_name)

    return epub_path


def main():
    print("=" * 60)
    print("GENERADOR EPUB: Schopenhauer - Raó Suficient")
    print("=" * 60)
    print()

    translation_file = OUTPUT_DIR / "SCHOPENHAUER_RAO_SUFICIENT_COMPLET.txt"
    if not translation_file.exists():
        print(f"[ERROR] No es troba: {translation_file}")
        return 1

    print("Creant estructura EPUB...")
    create_epub_structure()
    print("  ✓ Directoris creats")

    create_mimetype()
    create_container_xml()
    print("  ✓ Fitxers META-INF creats")

    create_css()
    print("  ✓ Estils CSS creats")

    create_title_page()
    create_intro()
    print("  ✓ Pàgines preliminars creades")

    print("\nProcessant contingut...")
    chapter_files = create_chapters(translation_file)

    create_nav(chapter_files)
    create_colophon()
    print("  ✓ Navegació i colofó creats")

    create_content_opf(chapter_files)
    print("  ✓ Manifest OPF creat")

    print("\nEmpaquetant EPUB...")
    epub_path = create_epub_file()
    size = epub_path.stat().st_size
    print(f"  ✓ EPUB creat: {epub_path}")
    print(f"  ✓ Mida: {size:,} bytes ({size/1024:.1f} KB)")

    print()
    print("=" * 60)
    print("EPUB GENERAT CORRECTAMENT!")
    print("=" * 60)
    print(f"\nFitxer: {epub_path}")

    return 0


if __name__ == "__main__":
    exit(main())
