"""Tests per a la generació del feed RSS."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def projecte_temporal(tmp_path: Path):
    """Crea una estructura de projecte mínima per testejar el build RSS."""
    # Directori obres
    obra_dir = tmp_path / "obres" / "filosofia" / "epictet" / "enchiridion"
    obra_dir.mkdir(parents=True)

    metadata = {
        "obra": {
            "titol": "Enchiridion",
            "titol_original": "Ἐγχειρίδιον",
            "autor": "Epictet",
            "traductor": "Editorial Clàssica",
            "any_original": "c. 125 dC",
            "any_traduccio": 2026,
            "llengua_original": "grec",
            "descripcio": "Manual pràctic de filosofia estoica",
        },
        "revisio": {
            "estat": "revisat",
            "qualitat": 8.5,
            "data_revisio": "2026-01-25",
        },
    }
    (obra_dir / "metadata.yml").write_text(
        yaml.dump(metadata, allow_unicode=True), encoding="utf-8"
    )
    (obra_dir / "original.md").write_text("## I\n\nText original", encoding="utf-8")
    (obra_dir / "traduccio.md").write_text("## I\n\nText traduït", encoding="utf-8")

    # Segona obra
    obra2_dir = tmp_path / "obres" / "narrativa" / "kafka" / "metamorfosi"
    obra2_dir.mkdir(parents=True)

    metadata2 = {
        "obra": {
            "titol": "La metamorfosi",
            "autor": "Franz Kafka",
            "traductor": "Editorial Clàssica",
            "any_traduccio": 2026,
            "llengua_original": "alemany",
            "descripcio": "Relat sobre la transformació de Gregor Samsa",
        },
        "revisio": {
            "estat": "revisat",
            "qualitat": 9.0,
            "data_revisio": "2026-02-15",
        },
    }
    (obra2_dir / "metadata.yml").write_text(
        yaml.dump(metadata2, allow_unicode=True), encoding="utf-8"
    )
    (obra2_dir / "original.md").write_text("## I\n\nOriginal alemany", encoding="utf-8")
    (obra2_dir / "traduccio.md").write_text("## I\n\nTraducció", encoding="utf-8")

    # Templates mínims
    templates_dir = tmp_path / "web" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "base.html").write_text(
        "{% block content %}{% endblock %}", encoding="utf-8"
    )
    (templates_dir / "obra.html").write_text(
        "{% extends 'base.html' %}{% block content %}<h1>{{ obra.titol }}</h1>{% endblock %}",
        encoding="utf-8",
    )
    (templates_dir / "index.html").write_text(
        "{% extends 'base.html' %}{% block content %}index{% endblock %}",
        encoding="utf-8",
    )
    (templates_dir / "cataleg.html").write_text(
        "{% extends 'base.html' %}{% block content %}cataleg{% endblock %}",
        encoding="utf-8",
    )
    (templates_dir / "cerca.html").write_text(
        "{% extends 'base.html' %}{% block content %}cerca{% endblock %}",
        encoding="utf-8",
    )

    # CSS / JS / data / assets dirs buits
    (tmp_path / "web" / "css").mkdir(parents=True, exist_ok=True)
    (tmp_path / "web" / "js").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)

    return tmp_path


def test_build_rss_genera_fitxer(projecte_temporal: Path, monkeypatch):
    """El build RSS ha de generar feed.xml dins docs/."""
    import sys

    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    from scripts.build import BuildSystem

    builder = BuildSystem(projecte_temporal)
    # Executar només les parts necessàries
    builder.docs_dir.mkdir(exist_ok=True)
    builder.build_obres()
    builder.build_rss()

    feed_path = projecte_temporal / "docs" / "feed.xml"
    assert feed_path.exists(), "feed.xml no s'ha generat"


def test_rss_xml_valid(projecte_temporal: Path, monkeypatch):
    """El feed RSS ha de ser XML vàlid amb estructura RSS 2.0."""
    import sys

    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    from scripts.build import BuildSystem

    builder = BuildSystem(projecte_temporal)
    builder.docs_dir.mkdir(exist_ok=True)
    builder.build_obres()
    builder.build_rss()

    feed_path = projecte_temporal / "docs" / "feed.xml"
    tree = ET.parse(feed_path)
    root = tree.getroot()

    assert root.tag == "rss"
    assert root.get("version") == "2.0"

    channel = root.find("channel")
    assert channel is not None
    assert channel.find("title").text == "Biblioteca Arion"
    assert channel.find("language").text == "ca"
    assert channel.find("description") is not None


def test_rss_conté_obres(projecte_temporal: Path, monkeypatch):
    """El feed ha de contenir un <item> per cada obra."""
    import sys

    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    from scripts.build import BuildSystem

    builder = BuildSystem(projecte_temporal)
    builder.docs_dir.mkdir(exist_ok=True)
    builder.build_obres()
    builder.build_rss()

    feed_path = projecte_temporal / "docs" / "feed.xml"
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel")
    items = channel.findall("item")

    assert len(items) == 2

    titols = [item.find("title").text for item in items]
    assert any("Enchiridion" in t for t in titols)
    assert any("La metamorfosi" in t for t in titols)


def test_rss_ordre_cronologic(projecte_temporal: Path, monkeypatch):
    """Les obres han d'estar ordenades per data (més recent primer)."""
    import sys

    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    from scripts.build import BuildSystem

    builder = BuildSystem(projecte_temporal)
    builder.docs_dir.mkdir(exist_ok=True)
    builder.build_obres()
    builder.build_rss()

    feed_path = projecte_temporal / "docs" / "feed.xml"
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel")
    items = channel.findall("item")

    # Kafka (2026-02-15) ha d'anar abans que Epictet (2026-01-25)
    assert "Kafka" in items[0].find("title").text
    assert "Epictet" in items[1].find("title").text


def test_rss_items_tenen_camps_requerits(projecte_temporal: Path, monkeypatch):
    """Cada item ha de tenir title, link, guid i description."""
    import sys

    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    from scripts.build import BuildSystem

    builder = BuildSystem(projecte_temporal)
    builder.docs_dir.mkdir(exist_ok=True)
    builder.build_obres()
    builder.build_rss()

    feed_path = projecte_temporal / "docs" / "feed.xml"
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel")

    for item in channel.findall("item"):
        assert item.find("title") is not None and item.find("title").text
        assert item.find("link") is not None and item.find("link").text
        assert item.find("guid") is not None and item.find("guid").text
        assert item.find("description") is not None and item.find("description").text
        assert item.find("pubDate") is not None
        assert item.find("category") is not None
