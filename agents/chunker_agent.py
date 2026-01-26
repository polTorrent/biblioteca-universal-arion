"""Agent especialitzat en dividir textos llargs en fragments òptims per processament."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.translator_agent import SupportedLanguage

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class ChunkingStrategy(str, Enum):
    """Estratègies de divisió del text."""

    TEI_XML = "tei_xml"
    MARKDOWN = "markdown"
    HTML = "html"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    AUTO = "auto"


class ChunkMetadata(BaseModel):
    """Metadades d'un chunk."""

    section: str | None = None
    subsection: str | None = None
    speakers: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0
    has_dialogue: bool = False
    references: list[str] = Field(default_factory=list)


class TextChunk(BaseModel):
    """Un fragment de text amb metadades."""

    chunk_id: int
    text: str
    start_position: int
    end_position: int
    context_prev: str = ""
    context_next: str = ""
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)

    @property
    def char_count(self) -> int:
        return len(self.text)


class ChunkingRequest(BaseModel):
    """Sol·licitud de divisió de text."""

    text: str
    strategy: ChunkingStrategy = ChunkingStrategy.AUTO
    max_tokens: int = Field(default=3500, ge=500, le=8000)
    min_tokens: int = Field(default=500, ge=100, le=2000)
    overlap_tokens: int = Field(default=100, ge=0, le=500)
    preserve_structure: bool = True
    source_language: SupportedLanguage = "grec"


class ChunkingResult(BaseModel):
    """Resultat de la divisió del text."""

    chunks: list[TextChunk]
    total_chunks: int
    total_characters: int
    estimated_total_tokens: int
    strategy_used: ChunkingStrategy
    warnings: list[str] = Field(default_factory=list)


class ChunkerAgent(BaseAgent):
    """Agent que divideix textos llargs en fragments òptims per processament.

    Analitza l'estructura del text i el divideix respectant
    divisions lògiques com capítols, seccions, paràgrafs i frases.
    """

    agent_name: str = "Chunker"

    # Aproximació de tokens per caràcter (conservador per grec/llatí)
    CHARS_PER_TOKEN = 3.5

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)
        self._speaker_pattern = re.compile(r'\b([A-ZÀÁÈÉÍÒÓÚÜ][A-ZÀÁÈÉÍÒÓÚÜ]+)\.\s')
        self._greek_speaker_pattern = re.compile(r'\b([Α-Ω]+)\.\s')
        # Patró per parlants japonesos (en kanji o hiragana/katakana)
        self._japanese_speaker_pattern = re.compile(r'【([^】]+)】|「([^」]+)」\s*と\s*(\S+)')  # 【Nom】 o citació amb parlant

    @property
    def system_prompt(self) -> str:
        return """Ets un expert en anàlisi estructural de textos clàssics.

La teva tasca és identificar les divisions naturals d'un text per facilitar
el seu processament en fragments coherents.

Analitza:
1. Estructura general (pròleg, capítols, epíleg)
2. Divisions internes (seccions, parlaments)
3. Canvis de tema o interlocutor
4. Transicions naturals"""

    def chunk(self, request: ChunkingRequest) -> ChunkingResult:
        """Divideix un text en chunks òptims.

        Args:
            request: Sol·licitud amb el text i paràmetres de chunking.

        Returns:
            ChunkingResult amb la llista de chunks i metadades.
        """
        # Detectar estratègia si és AUTO
        strategy = request.strategy
        if strategy == ChunkingStrategy.AUTO:
            strategy = self._detect_strategy(request.text)

        # Aplicar estratègia adequada
        if strategy == ChunkingStrategy.TEI_XML:
            chunks = self._chunk_tei_xml(request)
        elif strategy == ChunkingStrategy.MARKDOWN:
            chunks = self._chunk_markdown(request)
        elif strategy == ChunkingStrategy.HTML:
            chunks = self._chunk_html(request)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_paragraphs(request)
        else:
            chunks = self._chunk_sentences(request)

        # Post-processar: afegir context i consolidar chunks petits
        chunks = self._add_context(chunks, request.overlap_tokens)
        chunks = self._consolidate_small_chunks(chunks, request.min_tokens)
        chunks = self._split_large_chunks(chunks, request.max_tokens)

        # Recalcular IDs
        for i, chunk in enumerate(chunks):
            chunk.chunk_id = i + 1

        # Calcular totals
        total_chars = sum(c.char_count for c in chunks)
        estimated_tokens = int(total_chars / self.CHARS_PER_TOKEN)

        warnings = []
        if len(chunks) > 50:
            warnings.append(f"Text molt llarg: {len(chunks)} chunks. Considera revisar manualment.")

        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_characters=total_chars,
            estimated_total_tokens=estimated_tokens,
            strategy_used=strategy,
            warnings=warnings,
        )

    def _detect_strategy(self, text: str) -> ChunkingStrategy:
        """Detecta automàticament l'estratègia de chunking més adequada."""
        # Comprova si és TEI XML
        if text.strip().startswith('<?xml') or '<TEI' in text or '<tei:' in text:
            return ChunkingStrategy.TEI_XML

        # Comprova si és HTML
        if '<html' in text.lower() or '<div' in text.lower() or '<p>' in text.lower():
            return ChunkingStrategy.HTML

        # Comprova si és Markdown
        if re.search(r'^#{1,6}\s', text, re.MULTILINE) or re.search(r'^\*\*\*|^---', text, re.MULTILINE):
            return ChunkingStrategy.MARKDOWN

        # Per defecte, usar paràgrafs
        return ChunkingStrategy.PARAGRAPH

    def _chunk_tei_xml(self, request: ChunkingRequest) -> list[TextChunk]:
        """Divideix text TEI XML respectant l'estructura."""
        chunks = []
        text = request.text

        # Intentar parsejar com XML
        try:
            # Eliminar declaració XML si existeix per evitar problemes
            clean_text = re.sub(r'<\?xml[^?]*\?>', '', text)
            # Afegir namespace si cal
            if 'xmlns' not in clean_text:
                clean_text = clean_text.replace('<TEI>', '<TEI xmlns="http://www.tei-c.org/ns/1.0">')

            root = ET.fromstring(clean_text)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

            # Buscar divisions principals
            divisions = root.findall('.//tei:div[@type="textpart"]', ns)
            if not divisions:
                divisions = root.findall('.//tei:div', ns)
            if not divisions:
                # Fallback a paràgrafs
                divisions = root.findall('.//tei:p', ns)

            position = 0
            for i, div in enumerate(divisions):
                # Extreure text de la divisió
                div_text = self._extract_text_from_element(div)
                if not div_text.strip():
                    continue

                # Obtenir metadades
                section = div.get('n', f'secció_{i+1}')
                subtype = div.get('subtype', '')

                # Detectar parlants
                speakers = self._extract_speakers_from_element(div, ns)

                chunk = TextChunk(
                    chunk_id=len(chunks) + 1,
                    text=div_text.strip(),
                    start_position=position,
                    end_position=position + len(div_text),
                    metadata=ChunkMetadata(
                        section=section,
                        subsection=subtype,
                        speakers=speakers,
                        estimated_tokens=int(len(div_text) / self.CHARS_PER_TOKEN),
                        has_dialogue=len(speakers) > 0,
                    ),
                )
                chunks.append(chunk)
                position += len(div_text)

        except ET.ParseError:
            # Si falla el parsing XML, usar paràgrafs
            return self._chunk_paragraphs(request)

        return chunks

    def _extract_text_from_element(self, element: ET.Element) -> str:
        """Extreu recursivament el text d'un element XML."""
        text = element.text or ''
        for child in element:
            text += self._extract_text_from_element(child)
            text += child.tail or ''
        return text

    def _extract_speakers_from_element(self, element: ET.Element, ns: dict) -> list[str]:
        """Extreu els parlants d'un element TEI."""
        speakers = set()

        # Buscar elements <said> amb atribut who
        for said in element.findall('.//tei:said', ns):
            who = said.get('who', '')
            if who:
                # Netejar el # inicial si existeix
                speakers.add(who.lstrip('#'))

        # Buscar elements <label> que indiquen parlant
        for label in element.findall('.//tei:label', ns):
            if label.text:
                speakers.add(label.text.strip().rstrip('.'))

        return list(speakers)

    def _chunk_markdown(self, request: ChunkingRequest) -> list[TextChunk]:
        """Divideix text Markdown per títols i seccions."""
        chunks = []
        text = request.text

        # Dividir per títols
        sections = re.split(r'(^#{1,6}\s+.+$)', text, flags=re.MULTILINE)

        current_section = ""
        current_text = ""
        position = 0

        for part in sections:
            if re.match(r'^#{1,6}\s+', part):
                # És un títol
                if current_text.strip():
                    chunks.append(self._create_chunk(
                        len(chunks) + 1,
                        current_text.strip(),
                        position,
                        current_section,
                    ))
                current_section = part.strip().lstrip('#').strip()
                position += len(current_text)
                current_text = part
            else:
                current_text += part

        # Afegir últim chunk
        if current_text.strip():
            chunks.append(self._create_chunk(
                len(chunks) + 1,
                current_text.strip(),
                position,
                current_section,
            ))

        return chunks

    def _chunk_html(self, request: ChunkingRequest) -> list[TextChunk]:
        """Divideix text HTML per elements estructurals."""
        chunks = []
        text = request.text

        # Dividir per paràgrafs i divs
        parts = re.split(r'(<(?:p|div|section|article)[^>]*>.*?</(?:p|div|section|article)>)', text, flags=re.DOTALL | re.IGNORECASE)

        position = 0
        for i, part in enumerate(parts):
            clean_text = re.sub(r'<[^>]+>', '', part).strip()
            if not clean_text:
                continue

            chunks.append(self._create_chunk(
                len(chunks) + 1,
                clean_text,
                position,
            ))
            position += len(part)

        return chunks

    def _chunk_paragraphs(self, request: ChunkingRequest) -> list[TextChunk]:
        """Divideix text per paràgrafs."""
        chunks = []
        text = request.text

        # Dividir per dobles salts de línia o punt i seguit amb majúscula
        paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', text)

        position = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detectar parlants en el paràgraf
            speakers = self._detect_speakers(para)

            chunks.append(TextChunk(
                chunk_id=len(chunks) + 1,
                text=para,
                start_position=position,
                end_position=position + len(para),
                metadata=ChunkMetadata(
                    speakers=speakers,
                    estimated_tokens=int(len(para) / self.CHARS_PER_TOKEN),
                    has_dialogue=len(speakers) > 0,
                ),
            ))
            position += len(para) + 2  # +2 per \n\n

        return chunks

    def _chunk_sentences(self, request: ChunkingRequest) -> list[TextChunk]:
        """Divideix text per frases (últim recurs)."""
        chunks = []
        text = request.text

        # Patró per detectar finals de frase
        sentences = re.split(r'(?<=[.!?;·])\s+', text)

        position = 0
        current_chunk_text = ""
        chunk_start = 0

        for sentence in sentences:
            estimated_tokens = int(len(current_chunk_text + sentence) / self.CHARS_PER_TOKEN)

            if estimated_tokens > request.max_tokens and current_chunk_text:
                # Crear chunk amb el text acumulat
                chunks.append(self._create_chunk(
                    len(chunks) + 1,
                    current_chunk_text.strip(),
                    chunk_start,
                ))
                chunk_start = position
                current_chunk_text = sentence + " "
            else:
                current_chunk_text += sentence + " "

            position += len(sentence) + 1

        # Afegir últim chunk
        if current_chunk_text.strip():
            chunks.append(self._create_chunk(
                len(chunks) + 1,
                current_chunk_text.strip(),
                chunk_start,
            ))

        return chunks

    def _create_chunk(
        self,
        chunk_id: int,
        text: str,
        start_position: int,
        section: str | None = None,
    ) -> TextChunk:
        """Crea un TextChunk amb metadades calculades."""
        speakers = self._detect_speakers(text)
        return TextChunk(
            chunk_id=chunk_id,
            text=text,
            start_position=start_position,
            end_position=start_position + len(text),
            metadata=ChunkMetadata(
                section=section,
                speakers=speakers,
                estimated_tokens=int(len(text) / self.CHARS_PER_TOKEN),
                has_dialogue=len(speakers) > 0,
            ),
        )

    def _detect_speakers(self, text: str) -> list[str]:
        """Detecta parlants en un text."""
        speakers = set()

        # Patró per parlants llatins/catalans (SÒCRATES., APOL·LODOR., etc.)
        for match in self._speaker_pattern.finditer(text):
            speakers.add(match.group(1))

        # Patró per parlants grecs (ΣΩΚΡ., ΑΠΟΛ., etc.)
        for match in self._greek_speaker_pattern.finditer(text):
            speakers.add(match.group(1))

        return list(speakers)

    def _add_context(self, chunks: list[TextChunk], overlap_tokens: int) -> list[TextChunk]:
        """Afegeix context dels chunks anteriors i següents."""
        if not chunks or overlap_tokens == 0:
            return chunks

        overlap_chars = int(overlap_tokens * self.CHARS_PER_TOKEN)

        for i, chunk in enumerate(chunks):
            # Context anterior
            if i > 0:
                prev_text = chunks[i - 1].text
                chunk.context_prev = prev_text[-overlap_chars:] if len(prev_text) > overlap_chars else prev_text

            # Context següent
            if i < len(chunks) - 1:
                next_text = chunks[i + 1].text
                chunk.context_next = next_text[:overlap_chars] if len(next_text) > overlap_chars else next_text

        return chunks

    def _consolidate_small_chunks(self, chunks: list[TextChunk], min_tokens: int) -> list[TextChunk]:
        """Consolida chunks massa petits amb els adjacents."""
        if not chunks:
            return chunks

        min_chars = int(min_tokens * self.CHARS_PER_TOKEN)
        consolidated = []
        buffer_chunk = None

        for chunk in chunks:
            if buffer_chunk is None:
                if chunk.char_count < min_chars:
                    buffer_chunk = chunk
                else:
                    consolidated.append(chunk)
            else:
                # Fusionar amb el buffer
                merged_text = buffer_chunk.text + "\n\n" + chunk.text
                merged_chunk = TextChunk(
                    chunk_id=buffer_chunk.chunk_id,
                    text=merged_text,
                    start_position=buffer_chunk.start_position,
                    end_position=chunk.end_position,
                    metadata=ChunkMetadata(
                        section=buffer_chunk.metadata.section or chunk.metadata.section,
                        speakers=list(set(buffer_chunk.metadata.speakers + chunk.metadata.speakers)),
                        estimated_tokens=int(len(merged_text) / self.CHARS_PER_TOKEN),
                        has_dialogue=buffer_chunk.metadata.has_dialogue or chunk.metadata.has_dialogue,
                    ),
                )

                if merged_chunk.char_count < min_chars:
                    buffer_chunk = merged_chunk
                else:
                    consolidated.append(merged_chunk)
                    buffer_chunk = None

        # Afegir buffer restant
        if buffer_chunk:
            if consolidated:
                # Fusionar amb l'últim
                last = consolidated[-1]
                merged_text = last.text + "\n\n" + buffer_chunk.text
                consolidated[-1] = TextChunk(
                    chunk_id=last.chunk_id,
                    text=merged_text,
                    start_position=last.start_position,
                    end_position=buffer_chunk.end_position,
                    metadata=ChunkMetadata(
                        section=last.metadata.section,
                        speakers=list(set(last.metadata.speakers + buffer_chunk.metadata.speakers)),
                        estimated_tokens=int(len(merged_text) / self.CHARS_PER_TOKEN),
                        has_dialogue=last.metadata.has_dialogue or buffer_chunk.metadata.has_dialogue,
                    ),
                )
            else:
                consolidated.append(buffer_chunk)

        return consolidated

    def _split_large_chunks(self, chunks: list[TextChunk], max_tokens: int) -> list[TextChunk]:
        """Divideix chunks massa grans."""
        max_chars = int(max_tokens * self.CHARS_PER_TOKEN)
        result = []

        for chunk in chunks:
            if chunk.char_count <= max_chars:
                result.append(chunk)
            else:
                # Dividir per frases
                sentences = re.split(r'(?<=[.!?;·])\s+', chunk.text)
                current_text = ""
                sub_start = chunk.start_position

                for sentence in sentences:
                    if len(current_text) + len(sentence) > max_chars and current_text:
                        result.append(TextChunk(
                            chunk_id=len(result) + 1,
                            text=current_text.strip(),
                            start_position=sub_start,
                            end_position=sub_start + len(current_text),
                            metadata=ChunkMetadata(
                                section=chunk.metadata.section,
                                speakers=chunk.metadata.speakers,
                                estimated_tokens=int(len(current_text) / self.CHARS_PER_TOKEN),
                                has_dialogue=chunk.metadata.has_dialogue,
                            ),
                        ))
                        sub_start += len(current_text)
                        current_text = sentence + " "
                    else:
                        current_text += sentence + " "

                if current_text.strip():
                    result.append(TextChunk(
                        chunk_id=len(result) + 1,
                        text=current_text.strip(),
                        start_position=sub_start,
                        end_position=chunk.end_position,
                        metadata=ChunkMetadata(
                            section=chunk.metadata.section,
                            speakers=chunk.metadata.speakers,
                            estimated_tokens=int(len(current_text) / self.CHARS_PER_TOKEN),
                            has_dialogue=chunk.metadata.has_dialogue,
                        ),
                    ))

        return result

    def generate_summary(self, chunks: list[TextChunk], up_to_index: int) -> str:
        """Genera un resum dels chunks anteriors per context.

        Args:
            chunks: Llista de chunks processats.
            up_to_index: Índex fins on generar el resum.

        Returns:
            Resum breu dels chunks anteriors.
        """
        if up_to_index <= 0 or not chunks:
            return ""

        # Per ara, retornar els últims 500 caràcters del chunk anterior
        # En una versió més avançada, es podria usar l'LLM per resumir
        prev_chunks = chunks[:up_to_index]
        if not prev_chunks:
            return ""

        last_chunk = prev_chunks[-1]
        summary = f"[Context anterior: secció {last_chunk.metadata.section or 'anterior'}] "

        # Extreure última frase significativa
        sentences = re.split(r'(?<=[.!?])\s+', last_chunk.text)
        if sentences:
            last_sentences = sentences[-2:] if len(sentences) > 1 else sentences
            summary += "...".join(last_sentences[-1:])[:300] + "..."

        return summary

    def estimate_processing_cost(
        self,
        result: ChunkingResult,
        input_price_per_million: float = 3.0,
        output_price_per_million: float = 15.0,
        output_multiplier: float = 1.3,
    ) -> dict:
        """Estima el cost de processar tots els chunks.

        Args:
            result: Resultat del chunking.
            input_price_per_million: Preu per milió de tokens d'entrada.
            output_price_per_million: Preu per milió de tokens de sortida.
            output_multiplier: Multiplicador per estimar tokens de sortida.

        Returns:
            Diccionari amb estimacions de cost.
        """
        total_input_tokens = result.estimated_total_tokens
        total_output_tokens = int(total_input_tokens * output_multiplier)

        input_cost = (total_input_tokens / 1_000_000) * input_price_per_million
        output_cost = (total_output_tokens / 1_000_000) * output_price_per_million

        return {
            "total_chunks": result.total_chunks,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "input_cost_usd": round(input_cost, 4),
            "output_cost_usd": round(output_cost, 4),
            "total_cost_usd": round(input_cost + output_cost, 4),
            "cost_per_chunk_usd": round((input_cost + output_cost) / result.total_chunks, 4) if result.total_chunks > 0 else 0,
        }
