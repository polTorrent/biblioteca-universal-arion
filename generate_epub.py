#!/usr/bin/env python3
"""
Generador d'EPUB per a El Convit de Plató.
Crea un EPUB bilingüe grec-català directament sense usar l'API.
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Directoris
OUTPUT_DIR = Path("output/symposium")
EPUB_DIR = OUTPUT_DIR / "epub"
DATA_DIR = Path("data/originals/plato")

# Metadades
METADATA = {
    "title": "El Convit",
    "title_original": "Συμπόσιον",
    "author": "Plató",
    "translator": "Pipeline Editorial IA",
    "language": "ca",
    "language_original": "grc",
    "publisher": "Editorial Clàssica",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "identifier": f"urn:uuid:{uuid4()}",
    "rights": "Domini públic. Traducció sota llicència CC BY-SA 4.0",
    "description": "Traducció catalana del Simposi de Plató. Edició bilingüe grec-català.",
}


def create_epub_structure():
    """Crea l'estructura de directoris de l'EPUB."""
    dirs = [
        EPUB_DIR / "META-INF",
        EPUB_DIR / "OEBPS",
        EPUB_DIR / "OEBPS" / "text",
        EPUB_DIR / "OEBPS" / "styles",
        EPUB_DIR / "OEBPS" / "images",
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
    css = '''/* Estils per a El Convit de Plató */
@charset "UTF-8";

body {
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.8;
    margin: 1.5em;
    color: #333;
}

h1 {
    font-size: 2em;
    text-align: center;
    margin: 1em 0;
    color: #2c3e50;
}

h2 {
    font-size: 1.5em;
    color: #34495e;
    margin-top: 1.5em;
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.3em;
}

h3 {
    font-size: 1.2em;
    color: #7f8c8d;
}

.title-page {
    text-align: center;
    margin-top: 30%;
}

.title-page h1 {
    font-size: 2.5em;
    margin-bottom: 0.5em;
}

.title-page .author {
    font-size: 1.5em;
    font-style: italic;
    margin-bottom: 2em;
}

.title-page .translator {
    font-size: 1em;
    margin-top: 3em;
}

.bilingual {
    margin: 1.5em 0;
}

.greek {
    font-style: italic;
    color: #666;
    margin-bottom: 0.5em;
    font-size: 0.95em;
    line-height: 1.6;
}

.catalan {
    color: #2c3e50;
    line-height: 1.8;
}

.speaker {
    font-weight: bold;
    color: #8e44ad;
    margin-top: 1em;
}

.dialogue {
    margin-left: 1em;
}

blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #bdc3c7;
    font-style: italic;
}

.footnote {
    font-size: 0.85em;
    color: #7f8c8d;
}

.footnote-ref {
    vertical-align: super;
    font-size: 0.75em;
    color: #3498db;
    text-decoration: none;
}

.toc {
    list-style: none;
    padding: 0;
}

.toc li {
    margin: 0.5em 0;
}

.toc a {
    text-decoration: none;
    color: #2c3e50;
}

.colophon {
    margin-top: 3em;
    text-align: center;
    font-size: 0.9em;
    color: #95a5a6;
}

.credits {
    margin: 2em 0;
    font-size: 0.9em;
}
'''
    (EPUB_DIR / "OEBPS" / "styles" / "main.css").write_text(css, encoding="utf-8")


def create_content_opf():
    """Crea el fitxer content.opf."""
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">{METADATA["identifier"]}</dc:identifier>
    <dc:title>{METADATA["title"]} / {METADATA["title_original"]}</dc:title>
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
    <item id="css" href="styles/main.css" media-type="text/css"/>
    <item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="title" href="text/title.xhtml" media-type="application/xhtml+xml"/>
    <item id="intro" href="text/intro.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter01" href="text/chapter01.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter02" href="text/chapter02.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter03" href="text/chapter03.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter04" href="text/chapter04.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter05" href="text/chapter05.xhtml" media-type="application/xhtml+xml"/>
    <item id="colophon" href="text/colophon.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="title"/>
    <itemref idref="nav"/>
    <itemref idref="intro"/>
    <itemref idref="chapter01"/>
    <itemref idref="chapter02"/>
    <itemref idref="chapter03"/>
    <itemref idref="chapter04"/>
    <itemref idref="chapter05"/>
    <itemref idref="colophon"/>
  </spine>
</package>'''
    (EPUB_DIR / "OEBPS" / "content.opf").write_text(content, encoding="utf-8")


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


def create_title_page():
    """Crea la pàgina de títol."""
    content = '''<div class="title-page">
  <h1>El Convit</h1>
  <p class="author">Plató</p>
  <p style="font-size: 1.2em; margin: 1em 0;">Συμπόσιον</p>
  <p class="translator">Traducció al català</p>
  <p style="margin-top: 2em;">Edició bilingüe grec-català</p>
  <p style="margin-top: 3em; font-size: 0.9em;">Editorial Clàssica</p>
</div>'''
    (EPUB_DIR / "OEBPS" / "text" / "title.xhtml").write_text(
        xhtml_template("El Convit - Plató", content), encoding="utf-8"
    )


def create_nav():
    """Crea la taula de continguts navegable."""
    content = '''<nav epub:type="toc" id="toc">
  <h1>Taula de continguts</h1>
  <ol class="toc">
    <li><a href="title.xhtml">Portada</a></li>
    <li><a href="intro.xhtml">Introducció</a></li>
    <li><a href="chapter01.xhtml">Part I: El banquet a casa d'Agató</a></li>
    <li><a href="chapter02.xhtml">Part II: Els primers discursos</a></li>
    <li><a href="chapter03.xhtml">Part III: Aristòfanes i Agató</a></li>
    <li><a href="chapter04.xhtml">Part IV: Sòcrates i Diotima</a></li>
    <li><a href="chapter05.xhtml">Part V: L'arribada d'Alcibíades</a></li>
    <li><a href="colophon.xhtml">Colofó</a></li>
  </ol>
</nav>'''
    (EPUB_DIR / "OEBPS" / "text" / "nav.xhtml").write_text(
        xhtml_template("Taula de continguts", content), encoding="utf-8"
    )


def create_intro():
    """Crea la introducció."""
    content = '''<section>
  <h1>Introducció</h1>

  <h2>L'obra</h2>
  <p>El <em>Convit</em> (en grec Συμπόσιον, <em>Sympósion</em>) és un dels diàlegs més cèlebres de Plató, escrit aproximadament entre el 385 i el 370 aC. L'obra narra un banquet celebrat a casa del poeta tràgic Agató per commemorar la seva primera victòria als concursos dramàtics atenesos.</p>

  <p>Durant el simposi, els convidats decideixen pronunciar discursos en honor d'Eros, el déu de l'amor. Cada orador ofereix una perspectiva diferent sobre la natura de l'amor, des de la visió mèdica de Erixímac fins a la profunda reflexió filosòfica de Sòcrates, passant pel famós mite dels éssers esfèrics d'Aristòfanes.</p>

  <h2>Els personatges</h2>
  <ul>
    <li><strong>Sòcrates</strong>: El filòsof atenès, protagonista del diàleg.</li>
    <li><strong>Agató</strong>: Poeta tràgic, amfitrió del banquet.</li>
    <li><strong>Fedre</strong>: Jove atenès, primer orador.</li>
    <li><strong>Pausànias</strong>: Amant d'Agató, distingeix l'amor vulgar del celestial.</li>
    <li><strong>Erixímac</strong>: Metge, ofereix una visió còsmica de l'amor.</li>
    <li><strong>Aristòfanes</strong>: El famós comedògraf, autor del mite dels éssers partits.</li>
    <li><strong>Alcibíades</strong>: General atenès, irromp ebri al final i fa un elogi de Sòcrates.</li>
    <li><strong>Diotima</strong>: Sacerdotessa de Mantinea, mestra de Sòcrates en qüestions d'amor.</li>
  </ul>

  <h2>Sobre aquesta traducció</h2>
  <p>Aquesta traducció catalana s'ha realitzat directament del grec clàssic, buscant l'equilibri entre la fidelitat al text original i la fluïdesa en la llengua d'arribada. S'ha prioritzat mantenir el to filosòfic i l'oralitat característica del diàleg platònic.</p>

  <p>L'edició presenta el text en format bilingüe, permetent al lector confrontar la traducció amb l'original grec.</p>
</section>'''
    (EPUB_DIR / "OEBPS" / "text" / "intro.xhtml").write_text(
        xhtml_template("Introducció", content), encoding="utf-8"
    )


def split_text_into_chapters(text: str) -> list[str]:
    """Divideix el text en capítols basant-se en la longitud."""
    lines = text.strip().split('\n')
    total_lines = len(lines)
    chapter_size = total_lines // 5

    chapters = []
    for i in range(5):
        start = i * chapter_size
        end = (i + 1) * chapter_size if i < 4 else total_lines
        chapter_lines = lines[start:end]
        chapters.append('\n'.join(chapter_lines))

    return chapters


def format_text_as_html(text: str) -> str:
    """Converteix text pla a HTML amb paràgrafs."""
    paragraphs = text.strip().split('\n\n')
    html_parts = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Detectar si és un diàleg (comença amb cometes o guió)
        if para.startswith('«') or para.startswith('—') or para.startswith('"'):
            html_parts.append(f'<p class="dialogue">{para}</p>')
        else:
            html_parts.append(f'<p>{para}</p>')

    return '\n'.join(html_parts)


def create_chapters():
    """Crea els capítols de l'obra."""
    # Llegir la traducció completa
    translation_file = OUTPUT_DIR / "EL_CONVIT_COMPLET.txt"
    translation = translation_file.read_text(encoding="utf-8")

    # Llegir el text grec original si existeix
    greek_file = DATA_DIR / "symposium_greek.txt"
    greek = greek_file.read_text(encoding="utf-8") if greek_file.exists() else ""

    # Dividir en capítols
    cat_chapters = split_text_into_chapters(translation)
    greek_chapters = split_text_into_chapters(greek) if greek else [""] * 5

    chapter_titles = [
        "Part I: El banquet a casa d'Agató",
        "Part II: Els primers discursos",
        "Part III: Aristòfanes i Agató",
        "Part IV: Sòcrates i Diotima",
        "Part V: L'arribada d'Alcibíades",
    ]

    for i, (cat, grc, title) in enumerate(zip(cat_chapters, greek_chapters, chapter_titles), 1):
        content_parts = [f'<h1>{title}</h1>']

        # Format bilingüe: primer grec, després català
        if grc.strip():
            # Mostrar primer paràgraf del grec com a mostra
            greek_preview = grc[:2000] + "..." if len(grc) > 2000 else grc
            content_parts.append(f'''
<div class="bilingual">
  <details>
    <summary style="cursor: pointer; color: #666;">Mostrar text grec original</summary>
    <div class="greek">{format_text_as_html(greek_preview)}</div>
  </details>
</div>
''')

        content_parts.append(f'<div class="catalan">{format_text_as_html(cat)}</div>')

        (EPUB_DIR / "OEBPS" / "text" / f"chapter0{i}.xhtml").write_text(
            xhtml_template(title, '\n'.join(content_parts)), encoding="utf-8"
        )

    print(f"  ✓ Creats 5 capítols")


def create_colophon():
    """Crea el colofó."""
    content = f'''<div class="colophon">
  <h1>Colofó</h1>

  <p><em>El Convit</em> de Plató</p>
  <p>Traducció al català</p>

  <hr style="width: 30%; margin: 2em auto;"/>

  <p>Text original: Domini públic</p>
  <p>Traducció: Llicència CC BY-SA 4.0</p>

  <p style="margin-top: 2em;">
    Aquesta edició ha estat produïda amb el suport<br/>
    del Pipeline Editorial IA
  </p>

  <p style="margin-top: 2em;">
    <strong>{METADATA["publisher"]}</strong><br/>
    {METADATA["date"]}
  </p>

  <p style="margin-top: 3em; font-size: 0.8em;">
    Aquest EPUB ha estat generat automàticament<br/>
    i pot contenir errors. Reviseu el text original.
  </p>
</div>'''
    (EPUB_DIR / "OEBPS" / "text" / "colophon.xhtml").write_text(
        xhtml_template("Colofó", content), encoding="utf-8"
    )


def create_epub_file():
    """Empaqueta tot en un fitxer EPUB."""
    epub_path = OUTPUT_DIR / "El_Convit_Plato.epub"

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
    print("GENERADOR EPUB: El Convit de Plató")
    print("=" * 60)
    print()

    print("Creant estructura EPUB...")
    create_epub_structure()
    print("  ✓ Directoris creats")

    create_mimetype()
    create_container_xml()
    print("  ✓ Fitxers META-INF creats")

    create_css()
    print("  ✓ Estils CSS creats")

    create_content_opf()
    print("  ✓ Manifest OPF creat")

    create_title_page()
    create_nav()
    create_intro()
    print("  ✓ Pàgines preliminars creades")

    print("\nProcessant contingut...")
    create_chapters()
    create_colophon()

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
    print("\nPer validar l'EPUB, podeu usar:")
    print("  - EPUBCheck: java -jar epubcheck.jar El_Convit_Plato.epub")
    print("  - Calibre: calibre El_Convit_Plato.epub")


if __name__ == "__main__":
    main()
