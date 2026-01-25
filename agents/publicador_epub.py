"""Agent Publicador EPUB per generar ebooks professionals."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class EPUBMetadata(BaseModel):
    """Metadades per a l'EPUB."""

    titol: str
    autor: str
    traductor: str
    llengua: str = "ca"
    editorial: str = "Editorial Clàssica"
    data_publicacio: str
    isbn: str | None = None
    drets: str = "Domini públic. Traducció sota llicència CC BY-SA 4.0"
    descripcio: str
    materies: list[str] = Field(default_factory=list)
    colleccio: str | None = None
    numero_colleccio: int | None = None


class EPUBStructure(BaseModel):
    """Estructura de l'EPUB."""

    portada: bool = True
    pagina_titol: bool = True
    credits: bool = True
    taula_continguts: bool = True
    introduccio: bool = True
    nota_traductor: bool = True
    text_principal: bool = True
    notes: bool = True
    glossari: bool = True
    bibliografia: bool = False
    colofon: bool = True


class PublishRequest(BaseModel):
    """Sol·licitud de publicació."""

    metadata: EPUBMetadata
    estructura: EPUBStructure = Field(default_factory=EPUBStructure)
    text_original: str | None = None
    text_traduit: str
    introduccio: str | None = None
    nota_traductor: str | None = None
    notes: list[dict] | None = None
    glossari: list[dict] | None = None
    css: str | None = None
    format_bilingue: bool = True


class PublicadorEPUBAgent(BaseAgent):
    """Agent per generar fitxers EPUB professionals.

    Crea EPUB vàlids amb estructura completa, metadades
    i format bilingüe opcional.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return """Ets un expert en publicació digital i creació d'EPUB professionals.

OBJECTIU:
Generar especificacions completes per crear EPUB vàlids i elegants de textos clàssics.

ESTRUCTURA D'UN EPUB:

1. METADADES (OPF)
   - Títol, autor, traductor
   - ISBN (si n'hi ha)
   - Llengua (ca per català)
   - Editorial i data
   - Drets i llicència
   - Matèries (BISAC o BIC)
   - Descripció

2. ESTRUCTURA DE FITXERS
   ```
   META-INF/
     container.xml
   OEBPS/
     content.opf
     toc.ncx
     toc.xhtml
     styles/
       main.css
     images/
       cover.jpg
     text/
       cover.xhtml
       title.xhtml
       toc.xhtml
       introduction.xhtml
       chapter-001.xhtml
       ...
       notes.xhtml
       glossary.xhtml
       colophon.xhtml
   ```

3. FORMAT BILINGÜE
   Opcions:
   a) Pàgines enfrontades (original/traducció)
   b) Paràgrafs alternats
   c) Text original en cursiva sota cada paràgraf
   d) Capítols separats (primer original, després traducció)

4. ELEMENTS ESPECIALS
   - Notes a peu de pàgina amb enllaços bidireccionals
   - Índex navegable (NCX i XHTML)
   - Marcadors de capítols i seccions
   - Numeració de versos/línies per a poesia

5. VALIDACIÓ
   - EPUB 3.2 compatible
   - XHTML vàlid
   - CSS sense errors
   - Imatges optimitzades
   - Accessibilitat bàsica (alt text, lang)

FORMAT DE RESPOSTA:
{
    "metadata_opf": "<contingut XML del fitxer content.opf>",
    "estructura_fitxers": [
        {"path": "<camí>", "descripcio": "<què conté>"}
    ],
    "contingut_xhtml": {
        "cover": "<XHTML de la portada>",
        "title": "<XHTML de la pàgina de títol>",
        "toc": "<XHTML de la taula de continguts>",
        "chapter_template": "<plantilla XHTML per a capítols>",
        "notes": "<XHTML per a les notes>",
        "glossary": "<XHTML per al glossari>",
        "colophon": "<XHTML del colofó>"
    },
    "toc_ncx": "<contingut XML del fitxer toc.ncx>",
    "instruccions_generacio": [
        "<pas per crear l'EPUB>"
    ],
    "validacio": {
        "checklist": ["<element a verificar>"],
        "eines_recomanades": ["<eina>"]
    }
}"""

    def generate_epub_spec(self, request: PublishRequest) -> AgentResponse:
        """Genera especificacions completes per a l'EPUB.

        Args:
            request: Paràmetres de publicació.

        Returns:
            AgentResponse amb totes les especificacions.
        """
        prompt_parts = [
            "Genera especificacions completes per crear un EPUB professional.",
            "",
            "METADADES:",
            f"- Títol: {request.metadata.titol}",
            f"- Autor: {request.metadata.autor}",
            f"- Traductor: {request.metadata.traductor}",
            f"- Editorial: {request.metadata.editorial}",
            f"- Data: {request.metadata.data_publicacio}",
            f"- ISBN: {request.metadata.isbn or 'No assignat'}",
            f"- Descripció: {request.metadata.descripcio}",
            "",
            f"FORMAT BILINGÜE: {'Sí' if request.format_bilingue else 'No'}",
            "",
            "CONTINGUTS DISPONIBLES:",
            f"- Introducció: {'Sí' if request.introduccio else 'No'}",
            f"- Nota traductor: {'Sí' if request.nota_traductor else 'No'}",
            f"- Notes: {'Sí, ' + str(len(request.notes)) + ' notes' if request.notes else 'No'}",
            f"- Glossari: {'Sí, ' + str(len(request.glossari)) + ' entrades' if request.glossari else 'No'}",
            "",
            "MOSTRA DEL TEXT:",
            request.text_traduit[:1500] + "..." if len(request.text_traduit) > 1500 else request.text_traduit,
        ]

        return self.process("\n".join(prompt_parts))

    def generate_chapter_xhtml(
        self,
        titol_capitol: str,
        text_original: str | None,
        text_traduit: str,
        numero: int,
        format_bilingue: bool = True,
    ) -> AgentResponse:
        """Genera el XHTML d'un capítol.

        Args:
            titol_capitol: Títol del capítol.
            text_original: Text en llengua original.
            text_traduit: Text traduït.
            numero: Número de capítol.
            format_bilingue: Si ha de ser bilingüe.

        Returns:
            AgentResponse amb el XHTML del capítol.
        """
        prompt = f"""Genera XHTML vàlid per a EPUB 3 per aquest capítol:

TÍTOL: {titol_capitol}
NÚMERO: {numero}
BILINGÜE: {"Sí" if format_bilingue else "No"}

{"TEXT ORIGINAL:" + chr(10) + text_original[:1000] if text_original and format_bilingue else ""}

TEXT TRADUÏT:
{text_traduit[:1500]}

Genera XHTML complet amb:
- Declaració DOCTYPE
- Metadades bàsiques
- Enllaç a CSS
- Classes per estilitzar
- {"Estructura bilingüe clara" if format_bilingue else ""}"""

        return self.process(prompt)

    def generate_opf(self, metadata: EPUBMetadata, fitxers: list[str]) -> AgentResponse:
        """Genera el fitxer content.opf.

        Args:
            metadata: Metadades del llibre.
            fitxers: Llista de fitxers a incloure.

        Returns:
            AgentResponse amb el contingut OPF.
        """
        prompt = f"""Genera el fitxer content.opf per a EPUB 3:

METADADES:
- dc:title: {metadata.titol}
- dc:creator: {metadata.autor}
- dc:contributor (traductor): {metadata.traductor}
- dc:publisher: {metadata.editorial}
- dc:date: {metadata.data_publicacio}
- dc:language: {metadata.llengua}
- dc:rights: {metadata.drets}
- dc:description: {metadata.descripcio}
- dc:identifier (ISBN): {metadata.isbn or 'urn:uuid:GENERAR'}

FITXERS A INCLOURE AL MANIFEST:
{chr(10).join('- ' + f for f in fitxers)}

Genera XML vàlid amb:
- Namespace correcte per EPUB 3
- Manifest complet
- Spine ordenat
- Guide amb referències"""

        return self.process(prompt)
