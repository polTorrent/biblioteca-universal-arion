"""Agent especialitzat en formatar traduccions al format Editorial Clàssica.

Genera fitxers Markdown segons l'especificació de FORMAT.md.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class WorkMetadata(BaseModel):
    """Metadades d'una obra."""

    title: str
    author: str
    translator: str = "Editorial Clàssica"
    source_language: Literal["grec", "llatí", "anglès", "alemany", "francès"] = "grec"
    original_author: str | None = None
    original_title: str | None = None
    period: str | None = None
    genre: str | None = None
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    status: Literal["esborrany", "revisat", "publicat"] = "esborrany"
    quality_score: float | None = None
    revision_rounds: int = 0
    total_cost_eur: float = 0.0
    tags: list[str] = Field(default_factory=list)
    isbn: str | None = None
    editor: str | None = None


class Section(BaseModel):
    """Una secció de l'obra."""

    title: str
    level: int = 2  # Nivell de capçalera (2=##, 3=###)
    content: str
    speaker: str | None = None  # Per a diàlegs
    type: str | None = None  # discurs, capítol, escena, etc.
    themes: list[str] = Field(default_factory=list)
    original_ref: str | None = None  # Referència a l'original (e.g., "174a-178a")


class GlossaryEntry(BaseModel):
    """Entrada de glossari."""

    term: str
    original: str | None = None
    transliteration: str | None = None
    definition: str
    context: str | None = None


class FormattingRequest(BaseModel):
    """Sol·licitud de formatatge."""

    metadata: WorkMetadata
    introduction: str | None = None
    sections: list[Section]
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    translator_notes: list[str] = Field(default_factory=list)
    bibliography: list[str] = Field(default_factory=list)
    output_path: Path | None = None


class FormatterAgent(BaseAgent):
    """Agent que formata traduccions segons l'especificació Editorial Clàssica.

    Genera fitxers Markdown amb:
    - Metadades YAML
    - Estructura semàntica
    - Glossari
    - Notes del traductor
    - Bibliografia
    """

    agent_name: str = "Formatter"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un expert en edició de textos clàssics i formatatge Markdown.

OBJECTIU:
Generar fitxers Markdown perfectament formats segons l'especificació Editorial Clàssica.

TASQUES:
1. Estructurar el contingut de manera clara i semàntica
2. Aplicar convencions tipogràfiques correctes
3. Formatar diàlegs, poesia i prosa adequadament
4. Mantenir coherència en l'ús de capçaleres i èmfasi
5. Generar glossaris i notes ben organitzats

CONVENCIONS:
- Noms de parlants: **NEGRETA**
- Termes estrangers: *cursiva*
- Títols d'obres: ***negreta cursiva***
- Notes del traductor: [N.T.: ...]
- Referències: Stephanus, OCT, etc."""

    def format_work(self, request: FormattingRequest) -> str:
        """Formata una obra completa en Markdown.

        Args:
            request: Sol·licitud amb totes les dades de l'obra.

        Returns:
            Contingut Markdown complet.
        """
        parts = []

        # 1. Metadades YAML
        parts.append(self._generate_yaml_frontmatter(request.metadata))
        parts.append("")

        # 2. Capçalera principal
        parts.append(f"# {request.metadata.title}")
        parts.append("")
        parts.append(f"**Autor**: {request.metadata.author}")
        parts.append(f"**Traductor**: {request.metadata.translator}")
        parts.append(f"**Any**: {request.metadata.date[:4]}")
        parts.append("")

        if request.metadata.genre:
            parts.append(f"> {request.metadata.genre}")
            parts.append("")

        # 3. Introducció (si n'hi ha)
        if request.introduction:
            parts.append("## Introducció")
            parts.append("")
            parts.append(request.introduction)
            parts.append("")

        # 4. Seccions principals
        for section in request.sections:
            parts.append(self._format_section(section))
            parts.append("")

        # 5. Notes del traductor
        if request.translator_notes:
            parts.append("## Notes del Traductor")
            parts.append("")
            for i, note in enumerate(request.translator_notes, 1):
                parts.append(f"{i}. {note}")
            parts.append("")

        # 6. Glossari
        if request.glossary:
            parts.append("## Glossari")
            parts.append("")
            for entry in sorted(request.glossary, key=lambda e: e.term):
                parts.append(self._format_glossary_entry(entry))
            parts.append("")

        # 7. Bibliografia
        if request.bibliography:
            parts.append("## Bibliografia")
            parts.append("")
            for ref in request.bibliography:
                parts.append(f"- {ref}")
            parts.append("")

        markdown = "\n".join(parts)

        # Guardar si s'ha especificat output_path
        if request.output_path:
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            request.output_path.write_text(markdown, encoding="utf-8")

        return markdown

    def _generate_yaml_frontmatter(self, metadata: WorkMetadata) -> str:
        """Genera el YAML frontmatter."""
        yaml_parts = ["---"]

        # Camps bàsics
        yaml_parts.append(f'title: "{metadata.title}"')
        yaml_parts.append(f'author: "{metadata.author}"')
        yaml_parts.append(f'translator: "{metadata.translator}"')
        yaml_parts.append(f'source_language: "{metadata.source_language}"')

        # Camps opcionals
        if metadata.original_author:
            yaml_parts.append(f'original_author: "{metadata.original_author}"')
        if metadata.original_title:
            yaml_parts.append(f'original_title: "{metadata.original_title}"')
        if metadata.period:
            yaml_parts.append(f'period: "{metadata.period}"')
        if metadata.genre:
            yaml_parts.append(f'genre: "{metadata.genre}"')

        yaml_parts.append(f'date: "{metadata.date}"')
        yaml_parts.append(f'status: "{metadata.status}"')

        if metadata.quality_score is not None:
            yaml_parts.append(f"quality_score: {metadata.quality_score}")
        if metadata.revision_rounds:
            yaml_parts.append(f"revision_rounds: {metadata.revision_rounds}")
        if metadata.total_cost_eur:
            yaml_parts.append(f"total_cost_eur: {metadata.total_cost_eur:.2f}")

        if metadata.tags:
            tags_str = ", ".join(f'"{tag}"' for tag in metadata.tags)
            yaml_parts.append(f"tags: [{tags_str}]")

        if metadata.isbn:
            yaml_parts.append(f'isbn: "{metadata.isbn}"')
        if metadata.editor:
            yaml_parts.append(f'editor: "{metadata.editor}"')

        yaml_parts.append("---")
        return "\n".join(yaml_parts)

    def _format_section(self, section: Section) -> str:
        """Formata una secció."""
        parts = []

        # Capçalera de la secció
        header_prefix = "#" * section.level
        parts.append(f"{header_prefix} {section.title}")

        # Metadades opcionals (com a comentari HTML)
        if section.speaker or section.type or section.themes or section.original_ref:
            meta_parts = ["<!-- section-meta"]
            if section.speaker:
                meta_parts.append(f'speaker: "{section.speaker}"')
            if section.type:
                meta_parts.append(f'type: "{section.type}"')
            if section.themes:
                themes_str = ", ".join(f'"{t}"' for t in section.themes)
                meta_parts.append(f"themes: [{themes_str}]")
            if section.original_ref:
                meta_parts.append(f'original: "{section.original_ref}"')
            meta_parts.append("-->")
            parts.append("\n".join(meta_parts))

        parts.append("")
        parts.append(section.content)

        return "\n".join(parts)

    def _format_glossary_entry(self, entry: GlossaryEntry) -> str:
        """Formata una entrada de glossari."""
        parts = []

        # Terme principal
        header = f"**{entry.term}**"
        if entry.original:
            header += f" ({entry.original})"
        if entry.transliteration:
            header += f" [*{entry.transliteration}*]"

        parts.append(header)
        parts.append(entry.definition)

        if entry.context:
            parts.append(f"*Context*: {entry.context}")

        parts.append("")  # Línia buida entre entrades
        return "\n".join(parts)

    def format_dialogue_line(self, speaker: str, text: str) -> str:
        """Formata una línia de diàleg.

        Args:
            speaker: Nom del parlant.
            text: Text del parlament.

        Returns:
            Línia formatada: **SPEAKER** — Text
        """
        return f"**{speaker.upper()}** — {text}"

    def format_poetry_line(self, line: str, indent: int = 4) -> str:
        """Formata un vers de poesia.

        Args:
            line: Text del vers.
            indent: Espais d'indentació.

        Returns:
            Vers indentat.
        """
        return " " * indent + line

    def format_translator_note(self, note: str) -> str:
        """Formata una nota del traductor inline.

        Args:
            note: Contingut de la nota.

        Returns:
            Nota formatada: [N.T.: ...]
        """
        return f"[N.T.: {note}]"

    def format_reference(self, ref: str, text: str | None = None) -> str:
        """Formata una referència.

        Args:
            ref: Referència (e.g., "174a", "República 510b").
            text: Text opcional a mostrar.

        Returns:
            Referència formatada.
        """
        if text:
            return f"[{text}](#{ref})"
        return f"[{ref}](#{ref})"

    def extract_speakers(self, text: str) -> list[str]:
        """Extreu noms de parlants d'un text.

        Args:
            text: Text amb diàlegs.

        Returns:
            Llista de noms de parlants únics.
        """
        import re

        # Patró: **NOM** — o **NOM.**
        pattern = r'\*\*([A-ZÀÁÈÉÍÒÓÚÜ][A-ZÀÁÈÉÍÒÓÚÜ·]+)\*\*\s*[—\.]'
        matches = re.findall(pattern, text)
        return list(dict.fromkeys(matches))  # Eliminar duplicats mantenint ordre

    def split_into_speeches(self, text: str) -> list[tuple[str, str]]:
        """Divideix un diàleg en parlaments.

        Args:
            text: Text del diàleg complet.

        Returns:
            Llista de tuples (parlant, text).
        """
        import re

        speeches = []
        pattern = r'\*\*([A-ZÀÁÈÉÍÒÓÚÜ][A-ZÀÁÈÉÍÒÓÚÜ·]+)\*\*\s*—\s*(.+?)(?=\*\*[A-ZÀÁÈÉÍÒÓÚÜ]|\Z)'
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            speaker = match.group(1)
            speech = match.group(2).strip()
            speeches.append((speaker, speech))

        return speeches

    def generate_table_of_contents(self, sections: list[Section]) -> str:
        """Genera una taula de continguts.

        Args:
            sections: Llista de seccions.

        Returns:
            Markdown amb la TOC.
        """
        lines = ["## Índex de Continguts", ""]

        for section in sections:
            indent = "  " * (section.level - 2)  # Nivell 2 = sense indent
            anchor = section.title.lower().replace(" ", "-").replace(":", "")
            # Eliminar caràcters especials
            anchor = "".join(c for c in anchor if c.isalnum() or c == "-")
            lines.append(f"{indent}- [{section.title}](#{anchor})")

        lines.append("")
        return "\n".join(lines)

    def validate_markdown(self, content: str) -> list[str]:
        """Valida un fitxer Markdown.

        Args:
            content: Contingut Markdown.

        Returns:
            Llista de warnings/errors (buida si tot és correcte).
        """
        issues = []

        # Comprovar frontmatter
        if not content.startswith("---"):
            issues.append("⚠️  Falta YAML frontmatter al començament")

        # Comprovar capçalera principal
        if "\n# " not in content[:500]:
            issues.append("⚠️  Falta capçalera principal de nivell 1 (#)")

        # Comprovar metadades bàsiques
        required_fields = ["title:", "author:", "translator:"]
        for field in required_fields:
            if field not in content[:500]:
                issues.append(f"⚠️  Falta camp obligatori: {field}")

        # Comprovar codificació
        try:
            content.encode("utf-8")
        except UnicodeEncodeError:
            issues.append("⚠️  Problemes de codificació UTF-8")

        return issues

    def process(self, prompt: str) -> AgentResponse:
        """Processa una sol·licitud de formatatge amb l'LLM.

        Útil per generar estructura a partir de text pla.
        """
        return super().process(prompt)
