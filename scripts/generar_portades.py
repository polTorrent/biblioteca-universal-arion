#!/usr/bin/env python3
"""Genera portades amb Venice AI per a obres validades.

Cerca obres amb fitxer `.validated`, llegeix metadata.yml i genera
una portada artística amb l'agent portadista si no en té.

Ús:
    # Generar portades per totes les obres validades sense portada
    python3 scripts/generar_portades.py

    # Forçar regeneració de totes les portades (obres validades)
    python3 scripts/generar_portades.py --force

    # Generar portada per una obra concreta
    python3 scripts/generar_portades.py --obra filosofia/seneca/epistola-1

    # Dry run (mostrar què es generaria)
    python3 scripts/generar_portades.py --dry-run

    # Llistar obres validades sense portada
    python3 scripts/generar_portades.py --list
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# CLAUDECODE=1 per usar subscripció (cost €0)
os.environ["CLAUDECODE"] = "1"

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    print("PyYAML no instal·lat. Executa: pip install PyYAML")
    sys.exit(1)

from agents.portadista import AgentPortadista, PortadistaConfig
from agents.venice_client import VeniceError


def carregar_metadata(obra_dir: Path) -> dict | None:
    """Carrega metadata.yml d'una obra.

    Args:
        obra_dir: Directori de l'obra.

    Returns:
        Dict amb les dades o None si no existeix.
    """
    meta_path = obra_dir / "metadata.yml"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def determinar_genere(metadata: dict, obra_dir: Path) -> str:
    """Determina el gènere literari per al portadista.

    Args:
        metadata: Dades de metadata.yml.
        obra_dir: Directori de l'obra (per deduir del path).

    Returns:
        Codi de gènere (FIL, POE, NOV, SAG, ORI, TEA, EPO).
    """
    obra = metadata.get("obra", {})
    genere_meta = obra.get("genere", "").lower()
    llengua = obra.get("llengua_original", "").lower()

    # Mapeig directe del camp genere del metadata
    mapa_genere = {
        "filosofia": "FIL",
        "poesia": "POE",
        "narrativa": "NOV",
        "teatre": "TEA",
        "oriental": "ORI",
        "epopeia": "EPO",
    }

    if genere_meta in mapa_genere:
        return mapa_genere[genere_meta]

    # Deduir del path (obres/CATEGORIA/autor/obra)
    obres_root = ROOT / "obres"
    parts = obra_dir.relative_to(obres_root).parts if obra_dir.is_relative_to(obres_root) else ()
    if parts:
        categoria = parts[0].lower()
        if categoria in mapa_genere:
            return mapa_genere[categoria]

    # Deduir de la llengua
    if "sànscrit" in llengua or "sanscrit" in llengua:
        return "SAG"
    if "japonès" in llengua or "xinès" in llengua:
        return "ORI"

    return "FIL"


def preparar_metadata_portadista(metadata: dict, obra_dir: Path) -> dict:
    """Prepara el diccionari de metadades per l'agent portadista.

    Args:
        metadata: Dades crues de metadata.yml.
        obra_dir: Directori de l'obra.

    Returns:
        Dict amb format esperat per AgentPortadista.crear_prompt().
    """
    obra = metadata.get("obra", {})
    return {
        "titol": obra.get("titol", obra_dir.name),
        "autor": obra.get("autor", obra_dir.parent.name),
        "genere": determinar_genere(metadata, obra_dir),
        "temes": obra.get("temes", []),
        "descripcio": obra.get("descripcio", ""),
    }


def trobar_obres_validades(base_dir: Path) -> list[Path]:
    """Troba totes les obres amb fitxer .validated.

    Args:
        base_dir: Directori base d'obres (normalment obres/).

    Returns:
        Llista de directoris d'obres validades, ordenats.
    """
    return sorted(p.parent for p in base_dir.rglob(".validated"))


def copiar_a_web(portada_path: Path, obra_dir: Path) -> Path | None:
    """Copia la portada al directori web/assets/portades/.

    Args:
        portada_path: Camí de la portada generada.
        obra_dir: Directori de l'obra.

    Returns:
        Camí de destí o None si falla.
    """
    web_portades = ROOT / "web" / "assets" / "portades"
    web_portades.mkdir(parents=True, exist_ok=True)
    slug = f"{obra_dir.parent.name}-{obra_dir.name}"
    web_path = web_portades / f"{slug}-portada.png"
    try:
        shutil.copy2(portada_path, web_path)
        return web_path
    except OSError:
        return None


def generar_portada(
    obra_dir: Path,
    agent: AgentPortadista,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Genera la portada per una obra validada.

    Args:
        obra_dir: Directori de l'obra.
        agent: Agent portadista inicialitzat.
        force: Regenerar encara que ja existeixi.
        dry_run: Només mostrar què es faria.

    Returns:
        True si s'ha generat correctament.
    """
    portada_path = obra_dir / "portada.png"

    # Comprovar si ja existeix
    if portada_path.exists() and not force:
        print(f"  Ja té portada: {obra_dir.relative_to(ROOT)}")
        return False

    # Carregar metadata
    metadata = carregar_metadata(obra_dir)
    if not metadata:
        print(f"  Sense metadata.yml: {obra_dir.relative_to(ROOT)}")
        return False

    meta_portadista = preparar_metadata_portadista(metadata, obra_dir)
    titol = meta_portadista["titol"]
    genere = meta_portadista["genere"]

    if dry_run:
        prompt_result = agent.crear_prompt(meta_portadista)
        print(f"  [DRY RUN] {titol} ({genere})")
        print(f"    Simbol: {prompt_result['simbol']}")
        print(f"    Raonament: {prompt_result['raonament']}")
        return False

    print(f"  Generant portada per: {titol} ({genere})...")

    try:
        portada_bytes = agent.generar_portada(meta_portadista)
        portada_path.write_bytes(portada_bytes)
        size_kb = len(portada_bytes) / 1024
        print(f"  Portada guardada: {portada_path.relative_to(ROOT)} ({size_kb:.0f} KB)")

        # Copiar a web/assets/portades/
        web_path = copiar_a_web(portada_path, obra_dir)
        if web_path:
            print(f"  Copiada a: {web_path.relative_to(ROOT)}")

        return True

    except VeniceError as e:
        print(f"  Error Venice per {titol}: {e}")
        return False
    except Exception as e:
        print(f"  Error inesperat per {titol}: {e}")
        return False


def main() -> None:
    """Punt d'entrada principal."""
    parser = argparse.ArgumentParser(
        description="Genera portades amb Venice AI per a obres validades.",
    )
    parser.add_argument(
        "--obra",
        type=str,
        help="Genera per una obra concreta (ex: filosofia/seneca/epistola-1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerar portades encara que ja existeixin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que es generaria sense executar.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Llistar obres validades sense portada.",
    )

    args = parser.parse_args()

    obres_dir = ROOT / "obres"

    print("=" * 55)
    print("GENERADOR DE PORTADES — Biblioteca Universal Arion")
    print("=" * 55)
    print()

    if args.list:
        obres = trobar_obres_validades(obres_dir)
        sense_portada = [o for o in obres if not (o / "portada.png").exists()]
        print(f"Obres validades sense portada ({len(sense_portada)}/{len(obres)}):")
        for obra in sense_portada:
            meta = carregar_metadata(obra)
            titol = meta.get("obra", {}).get("titol", obra.name) if meta else obra.name
            print(f"  - {obra.relative_to(obres_dir)} ({titol})")
        if not sense_portada:
            print("  Totes les obres validades tenen portada!")
        return

    # Inicialitzar agent portadista
    # CLAUDECODE=1 fa que BaseAgent no creï client Anthropic (usa subscripció).
    # VeniceError es captura internament a AgentPortadista.__init__ (venice=None).
    try:
        agent = AgentPortadista(portadista_config=PortadistaConfig())
    except Exception as e:
        print(f"Error inicialitzant agent portadista: {e}")
        sys.exit(1)

    if not args.dry_run and not agent.venice:
        print("Error: Venice client no disponible. Configura VENICE_API_KEY a .env")
        sys.exit(1)

    # Determinar obres a processar
    if args.obra:
        obra_path = obres_dir / args.obra
        if not obra_path.exists():
            # Buscar recursivament
            for meta_file in obres_dir.rglob("metadata.yml"):
                if args.obra in str(meta_file.relative_to(obres_dir)):
                    obra_path = meta_file.parent
                    break
        if not obra_path.exists():
            print(f"Obra no trobada: {args.obra}")
            sys.exit(1)
        obres = [obra_path]
    else:
        obres = trobar_obres_validades(obres_dir)

    if not obres:
        print("No s'han trobat obres validades.")
        return

    print(f"Obres a processar: {len(obres)}")
    print("-" * 40)

    generades = 0
    errors = 0

    for obra_dir in obres:
        rel = obra_dir.relative_to(ROOT)
        print(f"\n{rel}:")
        try:
            if generar_portada(obra_dir, agent, force=args.force, dry_run=args.dry_run):
                generades += 1
        except Exception as e:
            print(f"  Error inesperat: {e}")
            errors += 1

    print(f"\n{'=' * 40}")
    print(f"Portades generades: {generades}")
    if errors:
        print(f"Errors: {errors}")
    print("=" * 40)


if __name__ == "__main__":
    main()
