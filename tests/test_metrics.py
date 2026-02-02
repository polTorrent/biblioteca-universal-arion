"""Tests per al mòdul utils/metrics.py."""

import json
import pytest
from datetime import datetime
from pathlib import Path
from utils.metrics import (
    MetriquesChunk,
    MetriquesPipeline,
    MetricsCollector,
)


class TestMetriquesChunk:
    """Tests per a MetriquesChunk."""

    def test_crear_chunk_basic(self):
        """Crear un chunk amb valors bàsics."""
        chunk = MetriquesChunk(chunk_id="1")
        assert chunk.chunk_id == "1"
        assert chunk.temps_traduccio_s == 0.0
        assert chunk.errors == []

    def test_temps_total(self):
        """Calcular temps total d'un chunk."""
        chunk = MetriquesChunk(
            chunk_id="1",
            temps_traduccio_s=10.0,
            temps_revisio_s=5.0,
            temps_perfeccionament_s=3.0,
        )
        assert chunk.temps_total() == 18.0

    def test_millora_qualitat(self):
        """Calcular millora de qualitat."""
        chunk = MetriquesChunk(
            chunk_id="1",
            qualitat_inicial=6.0,
            qualitat_final=8.5,
        )
        assert chunk.millora_qualitat() == 2.5

    def test_millora_qualitat_sense_dades(self):
        """Millora qualitat sense dades retorna None."""
        chunk = MetriquesChunk(chunk_id="1")
        assert chunk.millora_qualitat() is None


class TestMetriquesPipeline:
    """Tests per a MetriquesPipeline."""

    def test_crear_pipeline(self):
        """Crear mètriques de pipeline."""
        m = MetriquesPipeline(
            sessio_id="test-123",
            obra="L'Obra",
            autor="L'Autor",
        )
        assert m.sessio_id == "test-123"
        assert m.obra == "L'Obra"
        assert m.chunks == []

    def test_afegir_chunk(self):
        """Afegir chunk actualitza totals."""
        m = MetriquesPipeline(sessio_id="test", obra="Obra", autor="Autor")
        chunk = MetriquesChunk(
            chunk_id="1",
            temps_traduccio_s=10.0,
            tokens_input=100,
            tokens_output=50,
        )
        m.afegir_chunk(chunk)

        assert len(m.chunks) == 1
        assert m.total_tokens_input == 100
        assert m.total_tokens_output == 50
        assert m.total_temps_s == 10.0

    def test_finalitzar(self):
        """Finalitzar estableix timestamp fi."""
        m = MetriquesPipeline(sessio_id="test", obra="Obra", autor="Autor")
        m.finalitzar()
        assert m.fi is not None

    def test_resum(self):
        """Generar resum de mètriques."""
        m = MetriquesPipeline(sessio_id="test", obra="Obra", autor="Autor")
        m.afegir_chunk(MetriquesChunk(
            chunk_id="1",
            qualitat_final=8.5,
            iteracions_refinament=2,
        ))
        m.afegir_chunk(MetriquesChunk(
            chunk_id="2",
            qualitat_final=7.5,
            iteracions_refinament=1,
        ))
        m.finalitzar()

        resum = m.resum()
        assert resum["chunks_processats"] == 2
        assert resum["qualitat_mitjana"] == 8.0
        assert resum["iteracions_mitjana"] == 1.5
        assert resum["taxa_exit"] == 1.0

    def test_guardar_i_carregar(self, tmp_path):
        """Guardar i carregar mètriques."""
        m = MetriquesPipeline(sessio_id="test-save", obra="Obra", autor="Autor")
        m.afegir_chunk(MetriquesChunk(chunk_id="1", qualitat_final=8.0))
        m.finalitzar()

        # Guardar
        filepath = m.guardar(tmp_path)
        assert filepath.exists()

        # Carregar
        m2 = MetriquesPipeline.carregar(filepath)
        assert m2.sessio_id == "test-save"
        assert len(m2.chunks) == 1
        assert m2.chunks[0].qualitat_final == 8.0


class TestMetricsCollector:
    """Tests per a MetricsCollector."""

    def test_crear_collector(self, tmp_path):
        """Crear collector."""
        collector = MetricsCollector(tmp_path)
        assert collector.directori == tmp_path

    def test_carregar_totes_buit(self, tmp_path):
        """Carregar d'un directori buit."""
        collector = MetricsCollector(tmp_path)
        metriques = collector.carregar_totes()
        assert metriques == []

    def test_carregar_totes(self, tmp_path):
        """Carregar múltiples mètriques."""
        # Crear dues sessions
        for i in range(2):
            m = MetriquesPipeline(sessio_id=f"test-{i}", obra=f"Obra {i}", autor="Autor")
            m.afegir_chunk(MetriquesChunk(chunk_id="1", qualitat_final=7.0 + i))
            m.finalitzar()
            m.guardar(tmp_path)

        collector = MetricsCollector(tmp_path)
        metriques = collector.carregar_totes()
        assert len(metriques) == 2

    def test_informe_global_buit(self, tmp_path):
        """Informe global sense dades."""
        collector = MetricsCollector(tmp_path)
        informe = collector.informe_global()
        assert "No hi ha mètriques" in informe

    def test_informe_global(self, tmp_path):
        """Informe global amb dades."""
        m = MetriquesPipeline(sessio_id="test", obra="Obra", autor="Autor")
        m.afegir_chunk(MetriquesChunk(chunk_id="1", qualitat_final=8.5))
        m.finalitzar()
        m.guardar(tmp_path)

        collector = MetricsCollector(tmp_path)
        informe = collector.informe_global()
        assert "Sessions totals: 1" in informe
        assert "Chunks processats: 1" in informe

    def test_informe_sessio(self, tmp_path):
        """Informe de sessió específica."""
        m = MetriquesPipeline(sessio_id="test-specific", obra="Obra", autor="Autor")
        m.afegir_chunk(MetriquesChunk(chunk_id="1", qualitat_final=8.5))
        m.finalitzar()
        m.guardar(tmp_path)

        collector = MetricsCollector(tmp_path)
        informe = collector.informe_sessio("test-specific")
        assert "test-specific" in informe
        assert "Obra" in informe

    def test_informe_sessio_no_existeix(self, tmp_path):
        """Informe de sessió inexistent."""
        collector = MetricsCollector(tmp_path)
        informe = collector.informe_sessio("no-existeix")
        assert "No s'han trobat" in informe

    def test_eliminar_metriques(self, tmp_path):
        """Eliminar mètriques d'una sessió."""
        m = MetriquesPipeline(sessio_id="test-delete", obra="Obra", autor="Autor")
        m.guardar(tmp_path)

        collector = MetricsCollector(tmp_path)

        # Verificar que existeix
        filepath = tmp_path / "test-delete_metrics.json"
        assert filepath.exists()

        # Eliminar
        result = collector.eliminar_metriques("test-delete")
        assert result is True
        assert not filepath.exists()

        # Eliminar de nou (no existeix)
        result = collector.eliminar_metriques("test-delete")
        assert result is False
