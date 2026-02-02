"""Utilitats per a la gestió de metadades de les obres."""

from datetime import datetime
from pathlib import Path

import yaml


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
        with open(metadata_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}

        # Si ja té la clau 'obra:', no cal fer res
        if "obra" in existing:
            return

        # Si té dades però sense 'obra:', migrar al nou format
        if "titol" in existing:
            new_metadata = {
                "obra": {
                    "titol": existing.get("titol", titol),
                    "titol_original": existing.get("titol_original"),
                    "autor": existing.get("autor", autor),
                    "autor_original": existing.get("autor_original"),
                    "traductor": existing.get(
                        "traductor", "Biblioteca Arion (IA + comunitat)"
                    ),
                    "any_original": existing.get("any_original"),
                    "any_traduccio": datetime.now().year,
                    "llengua_original": existing.get("llengua_origen")
                    or existing.get("llengua_original")
                    or llengua,
                    "genere": existing.get("genere", genere),
                    "descripcio": existing.get("descripcio", ""),
                }
            }
            # Preservar altres camps
            if "revisio" in existing:
                new_metadata["revisio"] = existing["revisio"]
            if "estadistiques" in existing:
                new_metadata["obra"]["estadistiques"] = existing["estadistiques"]

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
    metadata = {
        "obra": {
            "titol": titol,
            "autor": autor,
            "traductor": "Biblioteca Arion (IA + comunitat)",
            "any_traduccio": datetime.now().year,
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
