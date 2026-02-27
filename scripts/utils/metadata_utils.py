"""Utilitats per a la gestió de metadades de les obres."""

import logging
from datetime import date
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


def crear_metadata_yml(
    obra_dir: Path,
    titol: str,
    autor: str,
    llengua: str,
    genere: str,
) -> None:
    """Crea o actualitza metadata.yml amb el format correcte (clau 'obra:' a l'arrel).

    Args:
        obra_dir: Directori de l'obra.
        titol: Títol de l'obra.
        autor: Nom de l'autor.
        llengua: Llengua original (ex: 'grec', 'japonès', 'alemany').
        genere: Gènere literari (ex: 'filosofia', 'narrativa', 'poesia').
    """
    metadata_path = obra_dir / "metadata.yml"

    # Si existeix, verificar format
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            log.warning("YAML malformat a %s, es recrearà", metadata_path)
            existing = {}

        if not isinstance(existing, dict):
            log.warning("metadata.yml no és un diccionari a %s, es recrearà", metadata_path)
            existing = {}

        # Si ja té la clau 'obra:', no cal fer res
        if "obra" in existing:
            return

        # Si té dades però sense 'obra:', migrar al nou format
        if "titol" in existing:
            obra_data: dict[str, object] = {
                "titol": existing.get("titol", titol),
                "autor": existing.get("autor", autor),
                "traductor": existing.get(
                    "traductor", "Biblioteca Arion (IA + comunitat)"
                ),
                "any_traduccio": date.today().year,
                "llengua_original": existing.get("llengua_origen")
                or existing.get("llengua_original")
                or llengua,
                "genere": existing.get("genere", genere),
                "descripcio": existing.get("descripcio", ""),
            }
            # Afegir camps opcionals només si existeixen
            for camp in ("titol_original", "autor_original", "any_original"):
                valor = existing.get(camp)
                if valor is not None:
                    obra_data[camp] = valor

            new_metadata: dict[str, object] = {"obra": obra_data}
            # Preservar altres camps a l'arrel (no dins 'obra')
            if "revisio" in existing:
                new_metadata["revisio"] = existing["revisio"]
            if "estadistiques" in existing:
                new_metadata["estadistiques"] = existing["estadistiques"]

            with open(metadata_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    new_metadata,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            return

    # Crear nou metadata
    metadata: dict[str, object] = {
        "obra": {
            "titol": titol,
            "autor": autor,
            "traductor": "Biblioteca Arion (IA + comunitat)",
            "any_traduccio": date.today().year,
            "llengua_original": llengua,
            "genere": genere,
            "descripcio": "",
        }
    }

    obra_dir.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        yaml.dump(
            metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )
