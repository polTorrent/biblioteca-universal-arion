"""Tests per al sistema de Checkpointing."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from utils.checkpointer import (
    Checkpointer,
    ChunkCheckpoint,
    PipelineCheckpoint,
)


class TestChunkCheckpoint:
    """Tests per a ChunkCheckpoint."""

    def test_default_values(self):
        """Comprova valors per defecte."""
        chunk = ChunkCheckpoint(
            chunk_id="1",
            text_original="Text original",
        )
        assert chunk.chunk_id == "1"
        assert chunk.estat == "pendent"
        assert chunk.text_original == "Text original"
        assert chunk.text_traduit is None
        assert chunk.iteracions_revisor == 0
        assert chunk.qualitat is None

    def test_all_states(self):
        """Comprova que tots els estats són vàlids."""
        estats = [
            "pendent",
            "traductor",
            "revisor",
            "perfeccionament",
            "anotador",
            "completat",
            "error",
        ]
        for estat in estats:
            chunk = ChunkCheckpoint(
                chunk_id="1",
                text_original="Text",
                estat=estat,
            )
            assert chunk.estat == estat


class TestPipelineCheckpoint:
    """Tests per a PipelineCheckpoint."""

    def test_default_values(self):
        """Comprova valors per defecte."""
        checkpoint = PipelineCheckpoint(
            sessio_id="test-123",
            obra="Test Obra",
            autor="Test Autor",
        )
        assert checkpoint.sessio_id == "test-123"
        assert checkpoint.obra == "Test Obra"
        assert checkpoint.autor == "Test Autor"
        assert checkpoint.fase_actual == "inicialitzant"
        assert checkpoint.chunks == []
        assert checkpoint.total_cost_eur == 0.0

    def test_all_phases(self):
        """Comprova que totes les fases són vàlides."""
        fases = [
            "inicialitzant",
            "brief",
            "pescador",
            "costos",
            "investigador",
            "glossarista",
            "traduccio",
            "fusio",
            "introduccio",
            "aprovacio",
            "publicacio",
            "completat",
            "error",
        ]
        for fase in fases:
            checkpoint = PipelineCheckpoint(
                sessio_id="test",
                obra="Obra",
                autor="Autor",
                fase_actual=fase,
            )
            assert checkpoint.fase_actual == fase


class TestCheckpointer:
    """Tests per a Checkpointer."""

    @pytest.fixture
    def checkpointer(self, tmp_path):
        """Crea un checkpointer amb directori temporal."""
        return Checkpointer(checkpoint_dir=tmp_path)

    def test_iniciar_sessio(self, checkpointer):
        """Comprova que iniciar() crea un checkpoint."""
        checkpoint = checkpointer.iniciar(
            sessio_id="test-session",
            obra="La República",
            autor="Plató",
            llengua_origen="grec",
            genere="filosofia",
        )
        assert checkpoint.sessio_id == "test-session"
        assert checkpoint.obra == "La República"
        assert checkpoint.autor == "Plató"
        assert checkpoint.llengua_origen == "grec"
        assert checkpoint.genere == "filosofia"
        assert checkpoint.fase_actual == "inicialitzant"

    def test_guardar_i_carregar(self, checkpointer):
        """Comprova que es pot guardar i carregar un checkpoint."""
        # Iniciar
        checkpointer.iniciar(
            sessio_id="test-save",
            obra="Ènquiridió",
            autor="Epictet",
        )

        # Modificar
        checkpointer.checkpoint.glossari = {"logos": "raó"}
        checkpointer._save()

        # Carregar
        loaded = checkpointer.carregar("test-save")
        assert loaded is not None
        assert loaded.obra == "Ènquiridió"
        assert loaded.glossari == {"logos": "raó"}

    def test_existeix(self, checkpointer):
        """Comprova que existeix() funciona correctament."""
        assert not checkpointer.existeix("no-existeix")

        checkpointer.iniciar(
            sessio_id="existeix-test",
            obra="Test",
            autor="Test",
        )
        assert checkpointer.existeix("existeix-test")

    def test_llistar_sessions(self, checkpointer):
        """Comprova que llistar_sessions() funciona."""
        assert checkpointer.llistar_sessions() == []

        checkpointer.iniciar("sessio-1", "Obra 1", "Autor 1")
        checkpointer.iniciar("sessio-2", "Obra 2", "Autor 2")

        sessions = checkpointer.llistar_sessions()
        assert len(sessions) == 2
        assert "sessio-1" in sessions
        assert "sessio-2" in sessions

    def test_guardar_glossari(self, checkpointer):
        """Comprova que guardar_glossari() actualitza la fase."""
        checkpointer.iniciar("glossari-test", "Obra", "Autor")
        checkpointer.guardar_glossari({"terme": "traducció"})

        assert checkpointer.checkpoint.glossari == {"terme": "traducció"}
        assert checkpointer.checkpoint.fase_actual == "traduccio"

    def test_iniciar_chunks(self, checkpointer):
        """Comprova que iniciar_chunks() crea els chunks."""
        checkpointer.iniciar("chunks-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Chunk 1", "Chunk 2", "Chunk 3"])

        assert len(checkpointer.checkpoint.chunks) == 3
        assert checkpointer.checkpoint.chunks[0].chunk_id == "1"
        assert checkpointer.checkpoint.chunks[0].text_original == "Chunk 1"
        assert checkpointer.checkpoint.chunks[1].chunk_id == "2"
        assert checkpointer.checkpoint.chunks[2].text_original == "Chunk 3"

    def test_actualitzar_chunk(self, checkpointer):
        """Comprova que actualitzar_chunk() funciona."""
        checkpointer.iniciar("update-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Text original"])

        checkpointer.actualitzar_chunk(
            "1",
            estat="traductor",
            text_traduit="Text traduït",
        )

        chunk = checkpointer.checkpoint.chunks[0]
        assert chunk.estat == "traductor"
        assert chunk.text_traduit == "Text traduït"

    def test_chunk_completat(self, checkpointer):
        """Comprova que chunk_completat() marca el chunk."""
        checkpointer.iniciar("complete-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Text"])

        checkpointer.chunk_completat("1", qualitat=8.5)

        chunk = checkpointer.checkpoint.chunks[0]
        assert chunk.estat == "completat"
        assert chunk.qualitat == 8.5
        assert chunk.timestamp_fi is not None

    def test_chunk_error(self, checkpointer):
        """Comprova que chunk_error() marca l'error."""
        checkpointer.iniciar("error-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Text"])

        checkpointer.chunk_error("1", "Error de traducció")

        chunk = checkpointer.checkpoint.chunks[0]
        assert chunk.estat == "error"
        assert chunk.error_message == "Error de traducció"
        assert checkpointer.checkpoint.errors_count == 1

    def test_obtenir_chunks_pendents(self, checkpointer):
        """Comprova que obtenir_chunks_pendents() funciona."""
        checkpointer.iniciar("pendents-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Chunk 1", "Chunk 2", "Chunk 3"])

        # Completar primer chunk
        checkpointer.chunk_completat("1")

        pendents = checkpointer.obtenir_chunks_pendents()
        assert len(pendents) == 2
        assert pendents[0].chunk_id == "2"
        assert pendents[1].chunk_id == "3"

    def test_guardar_fusio(self, checkpointer):
        """Comprova que guardar_fusio() actualitza la fase."""
        checkpointer.iniciar("fusio-test", "Obra", "Autor")
        checkpointer.guardar_fusio("Text fusionat complet")

        assert checkpointer.checkpoint.text_fusionat == "Text fusionat complet"
        assert checkpointer.checkpoint.fase_actual == "fusio"

    def test_actualitzar_estadistiques(self, checkpointer):
        """Comprova que actualitzar_estadistiques() acumula correctament."""
        checkpointer.iniciar("stats-test", "Obra", "Autor")

        checkpointer.actualitzar_estadistiques(
            tokens_input=100,
            tokens_output=50,
            cost_eur=0.01,
            temps_segons=5.0,
        )
        checkpointer.actualitzar_estadistiques(
            tokens_input=200,
            tokens_output=100,
            cost_eur=0.02,
            temps_segons=10.0,
        )

        assert checkpointer.checkpoint.total_tokens_input == 300
        assert checkpointer.checkpoint.total_tokens_output == 150
        assert checkpointer.checkpoint.total_cost_eur == pytest.approx(0.03)
        assert checkpointer.checkpoint.total_temps_segons == 15.0

    def test_finalitzar(self, checkpointer):
        """Comprova que finalitzar() marca el checkpoint com completat."""
        checkpointer.iniciar("final-test", "Obra", "Autor")
        checkpointer.finalitzar()

        assert checkpointer.checkpoint.fase_actual == "completat"

    def test_eliminar(self, checkpointer):
        """Comprova que eliminar() esborra el checkpoint."""
        checkpointer.iniciar("delete-test", "Obra", "Autor")
        assert checkpointer.existeix("delete-test")

        result = checkpointer.eliminar("delete-test")
        assert result is True
        assert not checkpointer.existeix("delete-test")

        # Esborrar inexistent
        result = checkpointer.eliminar("no-existeix")
        assert result is False

    def test_obtenir_resum(self, checkpointer):
        """Comprova que obtenir_resum() retorna info correcta."""
        checkpointer.iniciar("resum-test", "Obra", "Autor")
        checkpointer.iniciar_chunks(["Chunk 1", "Chunk 2"])
        checkpointer.chunk_completat("1", qualitat=8.0)
        checkpointer.actualitzar_estadistiques(
            tokens_input=100,
            cost_eur=0.01,
        )

        resum = checkpointer.obtenir_resum()
        assert resum is not None
        assert resum["sessio_id"] == "resum-test"
        assert resum["chunks_total"] == 2
        assert resum["chunks_completats"] == 1
        assert resum["chunks_pendents"] == 1
        assert resum["qualitat_mitjana"] == 8.0
        assert resum["total_cost_eur"] == 0.01

    def test_llistar_incomplets(self, checkpointer):
        """Comprova que llistar_incomplets() funciona."""
        # Sessió incompleta
        checkpointer.iniciar("incomplet", "Obra 1", "Autor 1")
        checkpointer.iniciar_chunks(["Chunk"])

        # Sessió completa
        checkpointer.iniciar("complet", "Obra 2", "Autor 2")
        checkpointer.finalitzar()

        incomplets = checkpointer.llistar_incomplets()
        assert len(incomplets) == 1
        assert incomplets[0]["sessio_id"] == "incomplet"
