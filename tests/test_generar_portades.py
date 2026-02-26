"""Tests per al mòdul scripts/generar_portades.py."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Assegurar que el directori arrel està al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generar_portades import (
    carregar_metadata,
    copiar_a_web,
    determinar_genere,
    preparar_metadata_portadista,
    trobar_obres_validades,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def obra_dir(tmp_path: Path) -> Path:
    """Crea un directori d'obra temporal amb metadata.yml i .validated."""
    obra = tmp_path / "obres" / "filosofia" / "seneca" / "epistola-1"
    obra.mkdir(parents=True)

    metadata_content = """obra:
  titol: "Epistola I — Sobre la recuperacio del temps"
  autor: Seneca
  any_original: 62-65
  any_traduccio: 2026
  llengua_original: llati
  genere: filosofia
  descripcio: >
    Primera de les 124 Epistoles morals a Lucili de Seneca.
  temes:
    - estoicisme
    - temps
    - memento mori
revisio:
  estat: revisat
  qualitat: 8.0
"""
    (obra / "metadata.yml").write_text(metadata_content, encoding="utf-8")
    (obra / ".validated").touch()
    return obra


@pytest.fixture
def obra_sense_validated(tmp_path: Path) -> Path:
    """Crea un directori d'obra sense .validated."""
    obra = tmp_path / "obres" / "filosofia" / "plato" / "criton"
    obra.mkdir(parents=True)
    (obra / "metadata.yml").write_text("obra:\n  titol: Criton\n", encoding="utf-8")
    return obra


@pytest.fixture
def obra_oriental(tmp_path: Path) -> Path:
    """Crea un directori d'obra oriental."""
    obra = tmp_path / "obres" / "oriental" / "sanscrit" / "sutra-cor"
    obra.mkdir(parents=True)

    metadata_content = """obra:
  titol: "El Sutra del Cor"
  autor: "Anonim"
  llengua_original: sanscrit
  genere: oriental
  temes:
    - zen
    - budeisme
"""
    (obra / "metadata.yml").write_text(metadata_content, encoding="utf-8")
    (obra / ".validated").touch()
    return obra


@pytest.fixture
def obra_poesia(tmp_path: Path) -> Path:
    """Crea un directori d'obra de poesia."""
    obra = tmp_path / "obres" / "poesia" / "shakespeare" / "sonets"
    obra.mkdir(parents=True)

    metadata_content = """obra:
  titol: "Sonets"
  autor: "William Shakespeare"
  llengua_original: angles
  genere: poesia
  temes:
    - amor
    - bellesa
"""
    (obra / "metadata.yml").write_text(metadata_content, encoding="utf-8")
    (obra / ".validated").touch()
    return obra


# ═══════════════════════════════════════════════════════════════════════════════
# Tests carregar_metadata
# ═══════════════════════════════════════════════════════════════════════════════


class TestCarregarMetadata:
    """Tests per a carregar_metadata."""

    def test_carrega_metadata_valid(self, obra_dir: Path) -> None:
        """Carrega correctament un metadata.yml existent."""
        meta = carregar_metadata(obra_dir)
        assert meta is not None
        assert meta["obra"]["titol"] == "Epistola I — Sobre la recuperacio del temps"
        assert meta["obra"]["autor"] == "Seneca"

    def test_retorna_none_si_no_existeix(self, tmp_path: Path) -> None:
        """Retorna None si no hi ha metadata.yml."""
        result = carregar_metadata(tmp_path)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# Tests determinar_genere
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeterminarGenere:
    """Tests per a determinar_genere."""

    def test_genere_filosofia(self, obra_dir: Path) -> None:
        """Detecta filosofia del camp genere."""
        meta = carregar_metadata(obra_dir)
        assert determinar_genere(meta, obra_dir) == "FIL"

    def test_genere_oriental(self, obra_oriental: Path) -> None:
        """Detecta oriental del camp genere."""
        meta = carregar_metadata(obra_oriental)
        assert determinar_genere(meta, obra_oriental) == "ORI"

    def test_genere_poesia(self, obra_poesia: Path) -> None:
        """Detecta poesia del camp genere."""
        meta = carregar_metadata(obra_poesia)
        assert determinar_genere(meta, obra_poesia) == "POE"

    def test_genere_per_defecte_filosofia(self, tmp_path: Path) -> None:
        """Retorna FIL per defecte si no es pot determinar."""
        meta = {"obra": {"titol": "Test"}}
        assert determinar_genere(meta, tmp_path) == "FIL"

    def test_genere_dedueix_del_path(self, tmp_path: Path) -> None:
        """Dedueix el genere del path si no hi ha camp genere."""
        obra = tmp_path / "obres" / "narrativa" / "kafka" / "metamorfosi"
        obra.mkdir(parents=True)
        meta = {"obra": {"titol": "La metamorfosi"}}
        # Necessitem que obra_dir sigui relatiu a ROOT/obres
        with patch("scripts.generar_portades.ROOT", tmp_path):
            assert determinar_genere(meta, obra) == "NOV"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests preparar_metadata_portadista
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepararMetadataPortadista:
    """Tests per a preparar_metadata_portadista."""

    def test_prepara_correctament(self, obra_dir: Path) -> None:
        """Extreu camps correctes per al portadista."""
        meta = carregar_metadata(obra_dir)
        result = preparar_metadata_portadista(meta, obra_dir)

        assert result["titol"] == "Epistola I — Sobre la recuperacio del temps"
        assert result["autor"] == "Seneca"
        assert result["genere"] == "FIL"
        assert "estoicisme" in result["temes"]
        assert len(result["descripcio"]) > 0

    def test_valors_per_defecte(self, tmp_path: Path) -> None:
        """Usa valors per defecte si falten camps."""
        obra = tmp_path / "obres" / "test" / "autor" / "obra-test"
        obra.mkdir(parents=True)
        meta = {"obra": {}}
        result = preparar_metadata_portadista(meta, obra)

        assert result["titol"] == "obra-test"
        assert result["autor"] == "autor"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests trobar_obres_validades
# ═══════════════════════════════════════════════════════════════════════════════


class TestTrobarObresValidades:
    """Tests per a trobar_obres_validades."""

    def test_troba_obres_amb_validated(self, obra_dir: Path) -> None:
        """Troba obres amb fitxer .validated."""
        base = obra_dir.parent.parent.parent  # obres/
        result = trobar_obres_validades(base)
        assert len(result) == 1
        assert result[0] == obra_dir

    def test_ignora_obres_sense_validated(self, obra_sense_validated: Path) -> None:
        """Ignora obres que no tenen .validated."""
        base = obra_sense_validated.parent.parent.parent  # obres/
        result = trobar_obres_validades(base)
        assert len(result) == 0

    def test_troba_multiples(self, tmp_path: Path) -> None:
        """Troba varies obres validades."""
        base = tmp_path / "obres"

        # Crear dues obres validades
        obra1 = base / "filosofia" / "seneca" / "epistola-1"
        obra1.mkdir(parents=True)
        (obra1 / ".validated").touch()
        (obra1 / "metadata.yml").write_text("obra:\n  titol: Epistola I\n")

        obra2 = base / "oriental" / "sanscrit" / "sutra-cor"
        obra2.mkdir(parents=True)
        (obra2 / ".validated").touch()
        (obra2 / "metadata.yml").write_text("obra:\n  titol: Sutra del Cor\n")

        result = trobar_obres_validades(base)
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Tests copiar_a_web
# ═══════════════════════════════════════════════════════════════════════════════


class TestCopiarAWeb:
    """Tests per a copiar_a_web."""

    def test_copia_correctament(self, obra_dir: Path, tmp_path: Path) -> None:
        """Copia la portada a web/assets/portades/."""
        portada = obra_dir / "portada.png"
        portada.write_bytes(b"fake-png-data")

        with patch("scripts.generar_portades.ROOT", tmp_path):
            result = copiar_a_web(portada, obra_dir)

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == b"fake-png-data"
        assert "portades" in str(result)

    def test_crea_directori_si_no_existeix(self, obra_dir: Path, tmp_path: Path) -> None:
        """Crea el directori web/assets/portades/ si no existeix."""
        portada = obra_dir / "portada.png"
        portada.write_bytes(b"data")

        web_dir = tmp_path / "web" / "assets" / "portades"
        assert not web_dir.exists()

        with patch("scripts.generar_portades.ROOT", tmp_path):
            copiar_a_web(portada, obra_dir)

        assert web_dir.exists()
