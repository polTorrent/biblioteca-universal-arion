"""Tests per al ChunkerAgent."""

import pytest
from pathlib import Path

from agents import (
    ChunkerAgent,
    ChunkingRequest,
    ChunkingStrategy,
    TextChunk,
)


class TestChunkerAgent:
    """Tests per a la funcionalitat de chunking."""

    @pytest.fixture
    def chunker(self):
        """Crea una instància del ChunkerAgent."""
        return ChunkerAgent()

    @pytest.fixture
    def sample_text(self):
        """Text de prova."""
        return """
        Pròleg: Introducció a l'obra.

        Capítol 1: El primer capítol comença aquí. Aquest és un paràgraf llarg
        que conté diverses frases. Continuem amb més contingut per tenir
        suficient text per fer proves adequades.

        Capítol 2: El segon capítol també té el seu contingut.
        Amb múltiples paràgrafs i frases.

        Epíleg: Conclusió de l'obra amb els pensaments finals de l'autor.
        """

    @pytest.fixture
    def long_text(self):
        """Text llarg de prova (>10.000 paraules)."""
        paragraph = """
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
        consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
        cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
        non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
        """ * 20  # ~200 paraules per paràgraf

        return "\n\n".join([paragraph] * 60)  # ~12.000 paraules

    @pytest.fixture
    def tei_xml_text(self):
        """Text TEI XML de prova."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <text xml:lang="grc">
                <body>
                    <div type="edition">
                        <div type="textpart" subtype="section" n="1">
                            <p><said who="#Sòcrates">Primera intervenció de Sòcrates.</said></p>
                        </div>
                        <div type="textpart" subtype="section" n="2">
                            <p><said who="#Plató">Resposta de Plató al mestre.</said></p>
                        </div>
                        <div type="textpart" subtype="section" n="3">
                            <p>Narració del diàleg entre els dos filòsofs.</p>
                        </div>
                    </div>
                </body>
            </text>
        </TEI>"""

    def test_chunk_basic_text(self, chunker, sample_text):
        """Prova chunking bàsic de text."""
        request = ChunkingRequest(
            text=sample_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=500,
            min_tokens=100,
        )
        result = chunker.chunk(request)

        assert result.total_chunks > 0
        assert result.total_characters > 0
        assert result.estimated_total_tokens > 0
        assert len(result.chunks) == result.total_chunks

    def test_no_content_loss(self, chunker, long_text):
        """Verifica que no es perd contingut durant el chunking."""
        request = ChunkingRequest(
            text=long_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=2000,
            min_tokens=200,
        )
        result = chunker.chunk(request)

        # Reconstruir text des dels chunks
        reconstructed = "\n\n".join(chunk.text for chunk in result.chunks)

        # El text reconstruït ha de contenir tot el contingut original
        # (pot tenir lleugeres diferències d'espais)
        original_words = set(long_text.split())
        reconstructed_words = set(reconstructed.split())

        # Verificar que no hem perdut paraules
        lost_words = original_words - reconstructed_words
        assert len(lost_words) == 0, f"S'han perdut paraules: {lost_words}"

    def test_chunk_sizes_within_limits(self, chunker, long_text):
        """Verifica que els chunks respecten els límits de tokens."""
        max_tokens = 2000
        min_tokens = 100

        request = ChunkingRequest(
            text=long_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
        )
        result = chunker.chunk(request)

        for chunk in result.chunks:
            # Verificar que no supera el màxim (amb un marge de tolerància)
            assert chunk.metadata.estimated_tokens <= max_tokens * 1.2, (
                f"Chunk {chunk.chunk_id} supera el màxim: {chunk.metadata.estimated_tokens} > {max_tokens}"
            )

    def test_auto_strategy_detection(self, chunker, sample_text, tei_xml_text):
        """Prova la detecció automàtica d'estratègia."""
        # Text pla -> PARAGRAPH
        request = ChunkingRequest(text=sample_text, strategy=ChunkingStrategy.AUTO)
        result = chunker.chunk(request)
        assert result.strategy_used == ChunkingStrategy.PARAGRAPH

        # TEI XML -> TEI_XML
        request = ChunkingRequest(text=tei_xml_text, strategy=ChunkingStrategy.AUTO)
        result = chunker.chunk(request)
        assert result.strategy_used == ChunkingStrategy.TEI_XML

    def test_tei_xml_chunking(self, chunker, tei_xml_text):
        """Prova chunking de TEI XML."""
        request = ChunkingRequest(
            text=tei_xml_text,
            strategy=ChunkingStrategy.TEI_XML,
            max_tokens=1000,
            min_tokens=100,
        )
        result = chunker.chunk(request)

        assert result.total_chunks >= 1
        assert result.strategy_used == ChunkingStrategy.TEI_XML

    def test_speaker_detection(self, chunker):
        """Prova la detecció de parlants."""
        text_with_speakers = """
        SÒCRATES. Bon dia, Fedre. On vas?
        FEDRE. Vinc de casa de Lísias, fill de Cèfal.
        SÒCRATES. I què hi feies?
        """

        request = ChunkingRequest(
            text=text_with_speakers,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=1000,
            min_tokens=100,
        )
        result = chunker.chunk(request)

        # Verificar que s'han detectat parlants
        all_speakers = []
        for chunk in result.chunks:
            all_speakers.extend(chunk.metadata.speakers)

        assert len(all_speakers) > 0

    def test_context_overlap(self, chunker, long_text):
        """Prova l'overlap de context entre chunks."""
        overlap_tokens = 100

        request = ChunkingRequest(
            text=long_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=1000,
            min_tokens=100,
            overlap_tokens=overlap_tokens,
        )
        result = chunker.chunk(request)

        # Verificar que els chunks tenen context
        if len(result.chunks) > 1:
            for i in range(1, len(result.chunks)):
                chunk = result.chunks[i]
                # El context_prev hauria d'estar present
                assert chunk.context_prev or i == 0

    def test_chunk_metadata(self, chunker, sample_text):
        """Prova que els chunks tenen metadades correctes."""
        request = ChunkingRequest(
            text=sample_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=500,
            min_tokens=100,
        )
        result = chunker.chunk(request)

        for chunk in result.chunks:
            assert chunk.chunk_id > 0
            assert chunk.text
            assert chunk.start_position >= 0
            assert chunk.end_position > chunk.start_position
            assert chunk.metadata.estimated_tokens > 0

    def test_cost_estimation(self, chunker, long_text):
        """Prova l'estimació de costos."""
        request = ChunkingRequest(
            text=long_text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=2000,
        )
        result = chunker.chunk(request)

        cost_estimate = chunker.estimate_processing_cost(result)

        assert "total_chunks" in cost_estimate
        assert "estimated_input_tokens" in cost_estimate
        assert "total_cost_usd" in cost_estimate
        assert cost_estimate["total_cost_usd"] > 0

    def test_summary_generation(self, chunker):
        """Prova la generació de resums de context."""
        chunks = [
            TextChunk(
                chunk_id=1,
                text="Primer chunk amb contingut.",
                start_position=0,
                end_position=26,
            ),
            TextChunk(
                chunk_id=2,
                text="Segon chunk amb més contingut.",
                start_position=27,
                end_position=56,
            ),
        ]

        summary = chunker.generate_summary(chunks, 1)
        assert summary  # Ha de generar algun resum
        assert "anterior" in summary.lower() or "..." in summary

    def test_empty_text(self, chunker):
        """Prova amb text buit."""
        request = ChunkingRequest(
            text="",
            strategy=ChunkingStrategy.PARAGRAPH,
        )
        result = chunker.chunk(request)

        assert result.total_chunks == 0
        assert result.total_characters == 0

    def test_single_paragraph_text(self, chunker):
        """Prova amb un sol paràgraf."""
        text = "Un sol paràgraf sense salts de línia. " * 50  # Fer-lo prou llarg
        request = ChunkingRequest(
            text=text,
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=1000,
            min_tokens=100,
        )
        result = chunker.chunk(request)

        assert result.total_chunks >= 1
        # El text s'ha de preservar (pot haver-hi lleugeres diferències d'espais)
        reconstructed = " ".join(chunk.text for chunk in result.chunks)
        assert len(reconstructed) > 0


class TestChunkingWithRealText:
    """Tests amb textos reals (si existeixen)."""

    @pytest.fixture
    def chunker(self):
        return ChunkerAgent()

    def test_symposium_chunking(self, chunker):
        """Prova chunking amb el text del Simposi si existeix."""
        symposium_path = Path("data/originals/plato/symposium_greek.txt")

        if not symposium_path.exists():
            pytest.skip("Text del Simposi no disponible")

        text = symposium_path.read_text(encoding="utf-8")

        request = ChunkingRequest(
            text=text,
            strategy=ChunkingStrategy.AUTO,
            max_tokens=3500,
            min_tokens=500,
        )
        result = chunker.chunk(request)

        # Verificacions bàsiques
        assert result.total_chunks > 0
        # El total de caràcters pot variar lleugerament per neteja d'espais
        assert abs(result.total_characters - len(text)) / len(text) < 0.01  # Tolerància 1%

        # Verificar que no es perd contingut
        reconstructed = " ".join(chunk.text for chunk in result.chunks)
        original_words = len(text.split())
        reconstructed_words = len(reconstructed.split())

        # Tolerància del 5%
        assert abs(original_words - reconstructed_words) / original_words < 0.05

        # Mostrar informació
        print(f"\nResultats del chunking del Simposi:")
        print(f"  Total chunks: {result.total_chunks}")
        print(f"  Tokens estimats: {result.estimated_total_tokens:,}")
        print(f"  Estratègia: {result.strategy_used.value}")

        cost = chunker.estimate_processing_cost(result)
        print(f"  Cost estimat: ${cost['total_cost_usd']:.4f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
