"""Tests per al mòdul scripts/generar_retrats.py i agents/agents_retratista.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generar_retrats import (
    copiar_a_web,
    retrat_path,
    trobar_autors,
)
from agents.agents_retratista import AUTORS_IMATGES


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def obres_dir(tmp_path: Path) -> Path:
    """Crea una estructura d'obres temporal amb diversos autors."""
    base = tmp_path / "obres"

    # Filosofia - Sèneca
    seneca = base / "filosofia" / "seneca" / "epistola-1"
    seneca.mkdir(parents=True)
    (seneca / "metadata.yml").write_text(
        "obra:\n  titol: Epistola I\n  autor: Sèneca\n", encoding="utf-8"
    )

    # Filosofia - Plató (2 obres)
    criton = base / "filosofia" / "plato" / "criton"
    criton.mkdir(parents=True)
    (criton / "metadata.yml").write_text(
        "obra:\n  titol: Critó\n  autor: Plató\n", encoding="utf-8"
    )

    apologia = base / "filosofia" / "plato" / "apologia"
    apologia.mkdir(parents=True)
    (apologia / "metadata.yml").write_text(
        "obra:\n  titol: Apologia de Sòcrates\n  autor: Plató\n", encoding="utf-8"
    )

    # Narrativa - Kafka
    kafka = base / "narrativa" / "kafka" / "metamorfosi"
    kafka.mkdir(parents=True)
    (kafka / "metadata.yml").write_text(
        "obra:\n  titol: La metamorfosi\n  autor: Franz Kafka\n", encoding="utf-8"
    )

    return base


# ═══════════════════════════════════════════════════════════════════════════════
# Tests trobar_autors
# ═══════════════════════════════════════════════════════════════════════════════


class TestTrobarAutors:
    """Tests per a trobar_autors."""

    def test_troba_autors_unics(self, obres_dir: Path) -> None:
        """Troba cada autor una sola vegada, fins i tot amb múltiples obres."""
        autors = trobar_autors(obres_dir)
        assert len(autors) == 3
        assert "seneca" in autors
        assert "plato" in autors
        assert "kafka" in autors

    def test_extreu_nom_de_metadata(self, obres_dir: Path) -> None:
        """Extreu el nom de l'autor de metadata.yml."""
        autors = trobar_autors(obres_dir)
        assert autors["seneca"]["nom"] == "Sèneca"
        assert autors["kafka"]["nom"] == "Franz Kafka"

    def test_extreu_categoria(self, obres_dir: Path) -> None:
        """Extreu la categoria correctament."""
        autors = trobar_autors(obres_dir)
        assert autors["seneca"]["categoria"] == "filosofia"
        assert autors["kafka"]["categoria"] == "narrativa"

    def test_directori_buit(self, tmp_path: Path) -> None:
        """Retorna diccionari buit si no hi ha obres."""
        base = tmp_path / "obres"
        base.mkdir()
        autors = trobar_autors(base)
        assert len(autors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Tests retrat_path
# ═══════════════════════════════════════════════════════════════════════════════


class TestRetratPath:
    """Tests per a retrat_path."""

    def test_path_correcte(self, tmp_path: Path) -> None:
        """Genera el path correcte per al retrat."""
        autor_dir = tmp_path / "obres" / "filosofia" / "seneca"
        result = retrat_path(autor_dir, "seneca")
        assert result == autor_dir / "retrat_seneca.png"

    def test_path_amb_slug_compost(self, tmp_path: Path) -> None:
        """Genera path correcte per slugs compostos."""
        autor_dir = tmp_path / "obres" / "narrativa" / "edgar-allan-poe"
        result = retrat_path(autor_dir, "edgar-allan-poe")
        assert result == autor_dir / "retrat_edgar-allan-poe.png"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests copiar_a_web
# ═══════════════════════════════════════════════════════════════════════════════


class TestCopiarAWeb:
    """Tests per a copiar_a_web."""

    def test_copia_correctament(self, tmp_path: Path) -> None:
        """Copia el retrat a web/assets/autors/."""
        retrat = tmp_path / "retrat_seneca.png"
        retrat.write_bytes(b"fake-png-data")

        with patch("scripts.generar_retrats.ROOT", tmp_path):
            result = copiar_a_web(retrat, "seneca")

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == b"fake-png-data"
        assert "autors" in str(result)
        assert result.name == "retrat_seneca.png"

    def test_crea_directori_si_no_existeix(self, tmp_path: Path) -> None:
        """Crea el directori web/assets/autors/ si no existeix."""
        retrat = tmp_path / "retrat_kafka.png"
        retrat.write_bytes(b"data")

        web_dir = tmp_path / "web" / "assets" / "autors"
        assert not web_dir.exists()

        with patch("scripts.generar_retrats.ROOT", tmp_path):
            copiar_a_web(retrat, "kafka")

        assert web_dir.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Tests AUTORS_IMATGES
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutorsImatges:
    """Tests per al diccionari AUTORS_IMATGES."""

    def test_conté_autors_clau(self) -> None:
        """Comprova que conté els autors principals del projecte."""
        autors_esperats = [
            "plato", "seneca", "epictetus", "kafka", "shakespeare",
            "baudelaire", "dostoievski", "sofocles", "laozi",
        ]
        for autor in autors_esperats:
            assert autor in AUTORS_IMATGES, f"Falta autor: {autor}"

    def test_estructura_correcta(self) -> None:
        """Comprova que cada autor té els camps obligatoris."""
        for clau, info in AUTORS_IMATGES.items():
            assert "nom" in info, f"Falta 'nom' per a {clau}"
            assert "nom_wikimedia" in info, f"Falta 'nom_wikimedia' per a {clau}"
            assert len(info["nom"]) > 0, f"Nom buit per a {clau}"
            assert len(info["nom_wikimedia"]) > 0, f"nom_wikimedia buit per a {clau}"

    def test_minim_20_autors(self) -> None:
        """Hi ha almenys 20 autors registrats."""
        assert len(AUTORS_IMATGES) >= 20
