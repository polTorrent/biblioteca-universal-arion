"""Generador automàtic d'EPUB per a la Biblioteca Universal Arion.

Crea EPUB 3.0 amb fallback NCX (EPUB 2) sense dependències externes
(només standard library + markdown, que ja és dependència del projecte).
"""

import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

import markdown
import yaml


# ─── CSS per al lector electrònic ─────────────────────────────────────────────

EPUB_CSS = """\
body {
    font-family: "Georgia", "Palatino", serif;
    line-height: 1.6;
    margin: 1em;
    color: #1a1a1a;
}
h1 {
    font-size: 1.8em;
    text-align: center;
    margin: 1.5em 0 0.5em;
    color: #2c1810;
}
h2 {
    font-size: 1.3em;
    margin: 1.5em 0 0.8em;
    color: #3d2914;
    border-bottom: 1px solid #d4c5a9;
    padding-bottom: 0.3em;
}
h3 {
    font-size: 1.1em;
    margin: 1.2em 0 0.6em;
    color: #4a3520;
}
p {
    margin: 0.6em 0;
    text-align: justify;
}
blockquote {
    margin: 1em 1.5em;
    padding-left: 1em;
    border-left: 3px solid #b8a88a;
    font-style: italic;
    color: #555;
}
.nota {
    font-size: 0.9em;
    color: #444;
    margin: 0.8em 0;
    padding: 0.5em 0.8em;
    border-left: 3px solid #c0a060;
    background: #faf6ee;
}
.glossari-entry {
    margin: 1em 0;
    padding: 0.5em 0;
    border-bottom: 1px solid #eee;
}
.glossari-entry .grec {
    font-weight: bold;
    color: #2c1810;
}
.glossari-entry .translit {
    font-style: italic;
    color: #666;
}
.glossari-entry .definicio {
    margin-top: 0.3em;
}
sup a {
    text-decoration: none;
    color: #8b4513;
    font-size: 0.85em;
}
.titol-portada {
    font-size: 2.2em;
    text-align: center;
    margin-top: 30%;
    color: #2c1810;
    font-weight: bold;
}
.autor-portada {
    font-size: 1.4em;
    text-align: center;
    margin-top: 1em;
    color: #5a4a3a;
    font-style: italic;
}
.editorial-portada {
    text-align: center;
    margin-top: 3em;
    font-size: 0.9em;
    color: #888;
}
.colofon {
    margin-top: 3em;
    text-align: center;
    font-size: 0.85em;
    color: #888;
}
"""


# ─── Helpers XML ──────────────────────────────────────────────────────────────

def _xml_declaration() -> bytes:
    return b'<?xml version="1.0" encoding="UTF-8"?>\n'


def _serialize(element: Element, ns_map: dict[str, str] | None = None) -> bytes:
    """Serialitza un Element a bytes amb declaració XML."""
    # Registrar namespaces
    if ns_map:
        for prefix, uri in ns_map.items():
            if prefix:
                element.set(f"xmlns:{prefix}", uri)
            else:
                element.set("xmlns", uri)
    raw = tostring(element, encoding="unicode", xml_declaration=False)
    return _xml_declaration() + raw.encode("utf-8")


# ─── Classe principal ─────────────────────────────────────────────────────────

class GeneradorEPUB:
    """Genera un fitxer EPUB a partir d'un directori d'obra."""

    def __init__(self, dir_obra: str | Path):
        self.obra_path = Path(dir_obra)
        self.metadata: dict[str, Any] = {}
        self.obra_data: dict[str, Any] = {}
        self.uid = str(uuid.uuid4())
        self.md = markdown.Markdown(
            extensions=["extra", "smarty"],
            output_format="html5",
        )

    # ── Lectura de fitxers ────────────────────────────────────────────────

    def _llegir_metadata(self) -> None:
        yml = self.obra_path / "metadata.yml"
        if yml.exists():
            with open(yml, "r", encoding="utf-8") as f:
                self.metadata = yaml.safe_load(f) or {}
        self.obra_data = self.metadata.get("obra", {})

    def _llegir_text(self, nom: str) -> str:
        fitxer = self.obra_path / nom
        if fitxer.exists():
            return fitxer.read_text(encoding="utf-8")
        return ""

    def _llegir_glossari(self) -> list[dict[str, Any]]:
        fitxer = self.obra_path / "glossari.yml"
        if fitxer.exists():
            with open(fitxer, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("termes", [])
        return []

    # ── Conversió Markdown → XHTML ───────────────────────────────────────

    def _md_a_html(self, text: str) -> str:
        self.md.reset()
        return self.md.convert(text)

    def _netejar_capcalera_v2(self, text: str) -> str:
        """Elimina capçalera de metadades V2 (YAML frontmatter o bloc fins a ---)."""
        if "---" not in text:
            return text
        lines = text.split("\n")
        # YAML frontmatter: comença amb --- i acaba amb ---
        if lines[0].strip() == "---":
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    return "\n".join(lines[i + 1:]).strip()
            # Només un --- inicial sense tancament: eliminar primera línia
            return "\n".join(lines[1:]).strip()
        # Format V2: capçalera lliure acabada amb ---
        for i, line in enumerate(lines):
            if line.strip() == "---":
                return "\n".join(lines[i + 1:]).strip()
        return text

    # ── Generació de capítols XHTML ──────────────────────────────────────

    def _xhtml_document(self, titol: str, cos_html: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ca" lang="ca">\n'
            "<head>\n"
            '<meta charset="UTF-8"/>\n'
            f"<title>{_esc(titol)}</title>\n"
            '<link rel="stylesheet" type="text/css" href="stylesheet.css"/>\n'
            "</head>\n"
            f"<body>\n{cos_html}\n</body>\n"
            "</html>"
        )

    def _generar_portada_xhtml(self) -> str:
        titol = self.obra_data.get("titol", self.obra_path.name.capitalize())
        autor = self.obra_data.get("autor", "Autor desconegut")
        titol_orig = self.obra_data.get("titol_original", "")
        any_orig = self.obra_data.get("any_original", "")

        cos = f'<div class="titol-portada">{_esc(titol)}</div>\n'
        if titol_orig:
            cos += f'<p style="text-align:center;color:#888;font-style:italic">{_esc(titol_orig)}</p>\n'
        cos += f'<div class="autor-portada">{_esc(autor)}</div>\n'
        if any_orig:
            cos += f'<p style="text-align:center;color:#999;margin-top:0.5em">{_esc(any_orig)}</p>\n'
        cos += '<div class="editorial-portada">Biblioteca Universal Arion</div>\n'
        cos += f'<p style="text-align:center;font-size:0.8em;color:#aaa;margin-top:1em">Traducció al català · {datetime.now().year}</p>\n'
        return self._xhtml_document(titol, cos)

    def _generar_traduccio_xhtml(self, text: str) -> str:
        titol = self.obra_data.get("titol", "Traducció")
        text = self._netejar_capcalera_v2(text)
        html = self._md_a_html(text)
        return self._xhtml_document(titol, html)

    def _generar_introduccio_xhtml(self, text: str) -> str:
        html = self._md_a_html(text)
        return self._xhtml_document("Introducció", html)

    def _generar_notes_xhtml(self, text: str) -> str:
        html = self._md_a_html(text)
        return self._xhtml_document("Notes del traductor", html)

    def _generar_glossari_xhtml(self, termes: list[dict[str, Any]]) -> str:
        parts = ["<h1>Glossari</h1>\n"]
        for t in termes:
            grec = t.get("grec", "")
            translit = t.get("transliteracio", "")
            traduccio = t.get("traduccio", "")
            definicio = t.get("definicio", "").strip()
            parts.append('<div class="glossari-entry">')
            parts.append(f'  <p><span class="grec">{_esc(grec)}</span>')
            if translit:
                parts.append(f' <span class="translit">({_esc(translit)})</span>')
            parts.append(f" — {_esc(traduccio)}</p>")
            if definicio:
                parts.append(f'  <p class="definicio">{_esc(definicio)}</p>')
            parts.append("</div>\n")
        return self._xhtml_document("Glossari", "\n".join(parts))

    def _generar_colofon_xhtml(self) -> str:
        titol = self.obra_data.get("titol", "")
        autor = self.obra_data.get("autor", "")
        traductor = self.obra_data.get("traductor", "Biblioteca Arion")
        cos = (
            '<div class="colofon">\n'
            f"<h2>Colofó</h2>\n"
            f"<p><em>{_esc(titol)}</em> de {_esc(autor)}</p>\n"
            f"<p>Traducció al català: {_esc(traductor)}</p>\n"
            f"<p>Biblioteca Universal Arion · {datetime.now().year}</p>\n"
            "<p>Llicència: CC BY-SA 4.0</p>\n"
            "<p>Aquesta traducció és lliure. Podeu copiar-la, distribuir-la "
            "i adaptar-la sempre que n'indiqueu l'autoria.</p>\n"
            "</div>"
        )
        return self._xhtml_document("Colofó", cos)

    # ── OPF (Package Document) ────────────────────────────────────────────

    def _generar_opf(
        self,
        items: list[tuple[str, str, str]],
        spine_ids: list[str],
        te_portada_img: bool,
    ) -> bytes:
        """Genera content.opf.

        items: [(id, href, media-type), ...]
        spine_ids: [id, ...]  (ordre de lectura)
        """
        titol = self.obra_data.get("titol", self.obra_path.name.capitalize())
        autor = self.obra_data.get("autor", "Autor desconegut")
        llengua = "ca"
        descripcio = self.obra_data.get("descripcio", "")

        pkg = Element("package")
        pkg.set("xmlns", "http://www.idpf.org/2007/opf")
        pkg.set("version", "3.0")
        pkg.set("unique-identifier", "bookid")

        # Metadata
        meta = SubElement(pkg, "metadata")
        meta.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")

        dc_id = SubElement(meta, "dc:identifier")
        dc_id.set("id", "bookid")
        dc_id.text = f"urn:uuid:{self.uid}"

        dc_title = SubElement(meta, "dc:title")
        dc_title.text = titol

        dc_lang = SubElement(meta, "dc:language")
        dc_lang.text = llengua

        dc_creator = SubElement(meta, "dc:creator")
        dc_creator.text = autor

        dc_publisher = SubElement(meta, "dc:publisher")
        dc_publisher.text = "Biblioteca Universal Arion"

        dc_rights = SubElement(meta, "dc:rights")
        dc_rights.text = "CC BY-SA 4.0"

        if descripcio:
            dc_desc = SubElement(meta, "dc:description")
            dc_desc.text = descripcio.strip()

        dc_date = SubElement(meta, "dc:date")
        dc_date.text = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        modified = SubElement(meta, "meta")
        modified.set("property", "dcterms:modified")
        modified.text = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if te_portada_img:
            cover_meta = SubElement(meta, "meta")
            cover_meta.set("name", "cover")
            cover_meta.set("content", "cover-image")

        # Manifest
        manifest = SubElement(pkg, "manifest")
        for item_id, href, mtype in items:
            item = SubElement(manifest, "item")
            item.set("id", item_id)
            item.set("href", href)
            item.set("media-type", mtype)
            if item_id == "nav":
                item.set("properties", "nav")
            if item_id == "cover-image":
                item.set("properties", "cover-image")

        # Spine
        spine = SubElement(pkg, "spine")
        spine.set("toc", "ncx")
        for sid in spine_ids:
            itemref = SubElement(spine, "itemref")
            itemref.set("idref", sid)

        raw = tostring(pkg, encoding="unicode", xml_declaration=False)
        return _xml_declaration() + raw.encode("utf-8")

    # ── NCX (EPUB 2 compat) ──────────────────────────────────────────────

    def _generar_ncx(self, nav_points: list[tuple[str, str, str]]) -> bytes:
        """nav_points: [(id, label, href), ...]"""
        ncx = Element("ncx")
        ncx.set("xmlns", "http://www.daisy.org/z3986/2005/ncx/")
        ncx.set("version", "2005-1")

        head = SubElement(ncx, "head")
        uid_meta = SubElement(head, "meta")
        uid_meta.set("name", "dtb:uid")
        uid_meta.set("content", f"urn:uuid:{self.uid}")

        doc_title = SubElement(ncx, "docTitle")
        text = SubElement(doc_title, "text")
        text.text = self.obra_data.get("titol", "Llibre")

        nav_map = SubElement(ncx, "navMap")
        for i, (nid, label, href) in enumerate(nav_points, 1):
            point = SubElement(nav_map, "navPoint")
            point.set("id", nid)
            point.set("playOrder", str(i))
            nav_label = SubElement(point, "navLabel")
            nav_text = SubElement(nav_label, "text")
            nav_text.text = label
            content = SubElement(point, "content")
            content.set("src", href)

        raw = tostring(ncx, encoding="unicode", xml_declaration=False)
        return _xml_declaration() + raw.encode("utf-8")

    # ── NAV XHTML (EPUB 3) ───────────────────────────────────────────────

    def _generar_nav(self, nav_points: list[tuple[str, str, str]]) -> str:
        items_html = "\n".join(
            f'      <li><a href="{href}">{_esc(label)}</a></li>'
            for _, label, href in nav_points
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ca">\n'
            "<head>\n"
            '<meta charset="UTF-8"/>\n'
            "<title>Índex</title>\n"
            '<link rel="stylesheet" type="text/css" href="stylesheet.css"/>\n'
            "</head>\n"
            "<body>\n"
            '  <nav epub:type="toc" id="toc">\n'
            "    <h1>Índex</h1>\n"
            "    <ol>\n"
            f"{items_html}\n"
            "    </ol>\n"
            "  </nav>\n"
            "</body>\n"
            "</html>"
        )

    # ── Mètode principal ─────────────────────────────────────────────────

    def generar(self, output_path: str | Path | None = None) -> Path:
        """Genera l'EPUB i retorna el Path del fitxer creat."""
        self._llegir_metadata()

        titol = self.obra_data.get("titol", self.obra_path.name.capitalize())
        safe_name = re.sub(r"[^\w\s-]", "", titol).strip().replace(" ", "_")

        if output_path is None:
            output_path = self.obra_path / f"{safe_name}.epub"
        output_path = Path(output_path)

        # Recollir contingut
        traduccio = self._llegir_text("traduccio.md")
        introduccio = self._llegir_text("introduccio.md")
        notes = self._llegir_text("notes.md")
        glossari = self._llegir_glossari()

        # Portada imatge
        portada_img: bytes | None = None
        portada_ext = ""
        for ext in ("png", "jpg", "jpeg"):
            p = self.obra_path / f"portada.{ext}"
            if p.exists():
                portada_img = p.read_bytes()
                portada_ext = ext
                break

        media_type_img = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }

        # ── Construir EPUB (ZIP) ──────────────────────────────────────

        items: list[tuple[str, str, str]] = []  # (id, href, media-type)
        spine_ids: list[str] = []
        nav_points: list[tuple[str, str, str]] = []  # (id, label, href)
        files: dict[str, str | bytes] = {}  # path → contingut

        # CSS
        items.append(("css", "stylesheet.css", "text/css"))
        files["OEBPS/stylesheet.css"] = EPUB_CSS

        # Portada imatge
        if portada_img:
            fname = f"portada.{portada_ext}"
            items.append(("cover-image", fname, media_type_img[portada_ext]))
            files[f"OEBPS/{fname}"] = portada_img

        # 1. Portada XHTML
        items.append(("portada", "portada.xhtml", "application/xhtml+xml"))
        spine_ids.append("portada")
        nav_points.append(("portada", "Portada", "portada.xhtml"))
        files["OEBPS/portada.xhtml"] = self._generar_portada_xhtml()

        # 2. Introducció
        if introduccio.strip():
            items.append(("introduccio", "introduccio.xhtml", "application/xhtml+xml"))
            spine_ids.append("introduccio")
            nav_points.append(("introduccio", "Introducció", "introduccio.xhtml"))
            files["OEBPS/introduccio.xhtml"] = self._generar_introduccio_xhtml(introduccio)

        # 3. Traducció (contingut principal)
        if traduccio.strip():
            items.append(("traduccio", "traduccio.xhtml", "application/xhtml+xml"))
            spine_ids.append("traduccio")
            nav_points.append(("traduccio", "Traducció", "traduccio.xhtml"))
            files["OEBPS/traduccio.xhtml"] = self._generar_traduccio_xhtml(traduccio)

        # 4. Notes
        if notes.strip():
            items.append(("notes", "notes.xhtml", "application/xhtml+xml"))
            spine_ids.append("notes")
            nav_points.append(("notes", "Notes del traductor", "notes.xhtml"))
            files["OEBPS/notes.xhtml"] = self._generar_notes_xhtml(notes)

        # 5. Glossari
        if glossari:
            items.append(("glossari", "glossari.xhtml", "application/xhtml+xml"))
            spine_ids.append("glossari")
            nav_points.append(("glossari", "Glossari", "glossari.xhtml"))
            files["OEBPS/glossari.xhtml"] = self._generar_glossari_xhtml(glossari)

        # 6. Colofó
        items.append(("colofo", "colofo.xhtml", "application/xhtml+xml"))
        spine_ids.append("colofo")
        nav_points.append(("colofo", "Colofó", "colofo.xhtml"))
        files["OEBPS/colofo.xhtml"] = self._generar_colofon_xhtml()

        # NAV (EPUB 3)
        items.append(("nav", "nav.xhtml", "application/xhtml+xml"))
        files["OEBPS/nav.xhtml"] = self._generar_nav(nav_points)

        # NCX (EPUB 2 compat)
        items.append(("ncx", "toc.ncx", "application/x-dtbncx+xml"))
        files["OEBPS/toc.ncx"] = self._generar_ncx(nav_points)

        # OPF
        files["OEBPS/content.opf"] = self._generar_opf(
            items, spine_ids, te_portada_img=portada_img is not None
        )

        # container.xml
        container_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            "  <rootfiles>\n"
            '    <rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/>\n'
            "  </rootfiles>\n"
            "</container>"
        )
        files["META-INF/container.xml"] = container_xml

        # ── Escriure ZIP ──────────────────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype MUST be first and uncompressed
            zf.writestr(
                "mimetype",
                "application/epub+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            for path, content in files.items():
                if isinstance(content, bytes):
                    zf.writestr(path, content)
                else:
                    zf.writestr(path, content.encode("utf-8"))

        return output_path


def _esc(text: Any) -> str:
    """Escapa caràcters XML."""
    s = str(text) if not isinstance(text, str) else text
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ─── Funció de conveniència ──────────────────────────────────────────────────

def generar_epub(dir_obra: str | Path, output_path: str | Path | None = None) -> str:
    """Genera l'arxiu EPUB d'una obra. Retorna el path del fitxer creat."""
    gen = GeneradorEPUB(dir_obra)
    resultat = gen.generar(output_path)
    return str(resultat)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Ús: python epub_generator.py <ruta/a/obra> [output.epub]")
        sys.exit(1)

    ruta = sys.argv[1]
    sortida = sys.argv[2] if len(sys.argv) > 2 else None
    out_epub = generar_epub(ruta, sortida)
    print(f"EPUB generat a: {out_epub}")
