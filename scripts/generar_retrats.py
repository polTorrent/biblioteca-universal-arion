#!/usr/bin/env python3
"""Genera retrats d'autors amb Venice AI per a la web.

Cerca tots els autors únics al directori obres/, i genera un retrat
estilitzat (rotoscòpia sepia) per cadascun usant l'AgentRetratista.

El retrat es guarda com a retrat_<autor_slug>.png dins el directori
de l'autor (primera obra trobada), i es copia a web/assets/autors/.

Ús:
    # Generar retrats per tots els autors sense retrat
    python3 scripts/generar_retrats.py

    # Forçar regeneració de tots els retrats
    python3 scripts/generar_retrats.py --force

    # Generar retrat per un autor concret
    python3 scripts/generar_retrats.py --autor seneca

    # Dry run (mostrar què es generaria)
    python3 scripts/generar_retrats.py --dry-run

    # Llistar autors sense retrat
    python3 scripts/generar_retrats.py --list
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any

# Forçar mode subscripció als agents (evita requerir ANTHROPIC_API_KEY,
# ja que AgentRetratista usa Venice API directament, no Anthropic).
os.environ["CLAUDECODE"] = "1"

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    print("PyYAML no instal·lat. Executa: pip install PyYAML")
    sys.exit(1)

from agents.agents_retratista import AUTORS_IMATGES, AgentRetratista  # noqa: E402


def trobar_autors(obres_dir: Path) -> dict[str, dict]:
    """Troba tots els autors únics escanejant obres/.

    Retorna un diccionari amb clau=slug_autor i valor=dict amb:
    - nom: nom de l'autor (de metadata.yml)
    - slug: slug de l'autor (nom del directori)
    - obra_dir: directori de la primera obra (per guardar el retrat)
    - categoria: categoria (filosofia, narrativa, etc.)

    Args:
        obres_dir: Directori base d'obres.

    Returns:
        Dict d'autors únics.
    """
    autors: dict[str, dict] = {}

    for metadata_file in sorted(obres_dir.rglob("metadata.yml")):
        obra_dir = metadata_file.parent
        parts = obra_dir.relative_to(obres_dir).parts
        if len(parts) < 3:
            continue

        categoria = parts[0]
        autor_slug = parts[1]

        if autor_slug in autors:
            continue

        try:
            with open(metadata_file, encoding="utf-8") as f:
                metadata = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            print(f"  Avís: metadata invàlida a {metadata_file}: {e}")
            continue

        obra_data = metadata.get("obra", {})
        nom_autor = obra_data.get("autor", autor_slug.replace("-", " ").title())

        autors[autor_slug] = {
            "nom": nom_autor,
            "slug": autor_slug,
            "obra_dir": obra_dir,
            "autor_dir": obra_dir.parent,
            "categoria": categoria,
        }

    return autors


def retrat_path(autor_dir: Path, autor_slug: str) -> Path:
    """Retorna el path esperat del retrat d'un autor.

    Args:
        autor_dir: Directori de l'autor (obres/<cat>/<autor>/).
        autor_slug: Slug de l'autor.

    Returns:
        Path del fitxer retrat.
    """
    return autor_dir / f"retrat_{autor_slug}.png"


def copiar_a_web(retrat_file: Path, autor_slug: str) -> Path | None:
    """Copia el retrat al directori web/assets/autors/.

    Args:
        retrat_file: Fitxer del retrat generat.
        autor_slug: Slug de l'autor.

    Returns:
        Path de destí o None si falla.
    """
    web_autors = ROOT / "web" / "assets" / "autors"
    web_autors.mkdir(parents=True, exist_ok=True)
    dest = web_autors / f"retrat_{autor_slug}.png"
    try:
        shutil.copy2(retrat_file, dest)
        return dest
    except OSError as e:
        print(f"  Avís: no s'ha pogut copiar retrat a web: {e}")
        return None


def generar_retrat(
    autor_slug: str,
    autor_info: dict[str, Any],
    agent: AgentRetratista,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Genera el retrat per un autor.

    Args:
        autor_slug: Slug de l'autor.
        autor_info: Dict amb nom, obra_dir, etc.
        agent: Agent retratista inicialitzat.
        force: Regenerar encara que ja existeixi.
        dry_run: Només mostrar què es faria.

    Returns:
        True si s'ha generat correctament.
    """
    autor_dir = autor_info["autor_dir"]
    output = retrat_path(autor_dir, autor_slug)

    if output.exists() and not force:
        print(f"  Ja té retrat: {output.relative_to(ROOT)}")
        return False

    nom = autor_info["nom"]

    # Buscar dades a AUTORS_IMATGES (nom_wikimedia per cercar a Wikimedia)
    imatge_info = AUTORS_IMATGES.get(autor_slug, {})
    nom_wikimedia = imatge_info.get("nom_wikimedia", nom)

    if dry_run:
        print(f"  [DRY RUN] {nom} (wikimedia: {nom_wikimedia})")
        return False

    print(f"  Generant retrat per: {nom}...")

    metadata = {
        "nom": nom,
        "nom_wikimedia": nom_wikimedia,
        "estil": "rotoscopia_sepia",
    }

    try:
        image_bytes = agent.generar_retrat(metadata)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image_bytes)
        size_kb = len(image_bytes) / 1024
        print(f"  Retrat guardat: {output.relative_to(ROOT)} ({size_kb:.0f} KB)")

        web_path = copiar_a_web(output, autor_slug)
        if web_path:
            print(f"  Copiat a: {web_path.relative_to(ROOT)}")

        return True

    except ValueError as e:
        print(f"  Error per {nom}: {e}")
        return False
    except Exception as e:
        print(f"  Error inesperat per {nom}: {e}")
        return False


def main() -> None:
    """Punt d'entrada principal."""
    parser = argparse.ArgumentParser(
        description="Genera retrats d'autors amb Venice AI.",
    )
    parser.add_argument(
        "--autor",
        type=str,
        help="Genera retrat per un autor concret (ex: seneca, kafka).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerar retrats encara que ja existeixin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar què es generaria sense executar.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Llistar autors sense retrat.",
    )

    args = parser.parse_args()

    obres_dir = ROOT / "obres"

    print("=" * 55)
    print("GENERADOR DE RETRATS — Biblioteca Universal Arion")
    print("=" * 55)
    print()

    autors = trobar_autors(obres_dir)
    print(f"Autors trobats: {len(autors)}")
    print()

    if args.list:
        sense_retrat = [
            (slug, info) for slug, info in autors.items()
            if not retrat_path(info["autor_dir"], slug).exists()
        ]
        print(f"Autors sense retrat ({len(sense_retrat)}/{len(autors)}):")
        for slug, info in sorted(sense_retrat):
            wikimedia = AUTORS_IMATGES.get(slug, {}).get("nom_wikimedia", "?")
            print(f"  - {slug}: {info['nom']} (wikimedia: {wikimedia})")
        if not sense_retrat:
            print("  Tots els autors tenen retrat!")
        return

    # Inicialitzar agent
    try:
        agent = AgentRetratista()
    except Exception as e:
        print(f"Error inicialitzant agent retratista: {e}")
        sys.exit(1)

    # Determinar autors a processar
    if args.autor:
        if args.autor not in autors:
            print(f"Autor no trobat: {args.autor}")
            print(f"Disponibles: {', '.join(sorted(autors.keys()))}")
            sys.exit(1)
        autors_processar = {args.autor: autors[args.autor]}
    else:
        autors_processar = autors

    print(f"Autors a processar: {len(autors_processar)}")
    print("-" * 40)

    generats = 0
    errors = 0

    for slug, info in sorted(autors_processar.items()):
        print(f"\n{slug} ({info['nom']}):")
        try:
            if generar_retrat(slug, info, agent, force=args.force, dry_run=args.dry_run):
                generats += 1
        except Exception as e:
            print(f"  Error inesperat: {e}")
            errors += 1

    print(f"\n{'=' * 40}")
    print(f"Retrats generats: {generats}")
    if errors:
        print(f"Errors: {errors}")
    print("=" * 40)


if __name__ == "__main__":
    main()
