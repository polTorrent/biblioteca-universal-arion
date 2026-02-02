#!/usr/bin/env python3
"""
Genera portades per a totes les obres que no en tenen.
Utilitza l'agent portadista amb Venice.ai.

Ús:
    python scripts/generar_portades.py                 # Genera portades per obres sense
    python scripts/generar_portades.py --all           # Regenera totes les portades
    python scripts/generar_portades.py --obra plato/criton  # Genera per una obra específica
"""

import argparse
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Afegir el directori arrel al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    print("❌ PyYAML no instal·lat. Executa: pip install PyYAML")
    sys.exit(1)


def get_genere_from_metadata(metadata: dict) -> str:
    """Determina el gènere literari a partir del metadata."""
    obra = metadata.get('obra', {})
    llengua = obra.get('llengua_original', '').lower()
    descripcio = obra.get('descripcio', '').lower()
    temes = metadata.get('temes', [])

    # Mapeig per llengua/tema
    if 'sànscrit' in llengua or 'sanscrit' in llengua:
        return 'SAG'  # Sagrat
    if 'grec' in llengua and ('filosof' in descripcio or 'plató' in descripcio.lower()):
        return 'FIL'  # Filosofia
    if 'llatí' in llengua or 'estoic' in descripcio:
        return 'FIL'
    if 'alemany' in llengua and 'filosof' in descripcio:
        return 'FIL'
    if 'japonès' in llengua or 'japó' in descripcio:
        return 'ORI'  # Oriental
    if any('poesia' in str(t).lower() or 'poètic' in str(t).lower() for t in temes):
        return 'POE'  # Poesia
    if any('teatre' in str(t).lower() or 'drama' in str(t).lower() for t in temes):
        return 'TEA'  # Teatre
    if 'narrativa' in str(ROOT / 'obres').lower() or 'conte' in descripcio or 'novel' in descripcio:
        return 'NOV'  # Novel·la/Narrativa

    return 'FIL'  # Per defecte filosofia


def find_obres_without_portada(obres_dir: Path) -> list[Path]:
    """Troba totes les obres sense portada."""
    obres_sense_portada = []

    for metadata_file in obres_dir.rglob('metadata.yml'):
        obra_dir = metadata_file.parent

        # Buscar portada existent
        has_portada = any(
            (obra_dir / f'portada.{ext}').exists()
            for ext in ['png', 'jpg', 'jpeg']
        )

        if not has_portada:
            obres_sense_portada.append(obra_dir)

    return obres_sense_portada


def generate_portada(obra_dir: Path, force: bool = False) -> bool:
    """Genera una portada per a una obra utilitzant l'agent portadista."""
    portada_path = obra_dir / 'portada.png'

    if portada_path.exists() and not force:
        print(f"   ⏭️  {obra_dir.name}: ja té portada")
        return False

    # Carregar metadata
    metadata_file = obra_dir / 'metadata.yml'
    if not metadata_file.exists():
        print(f"   ❌ {obra_dir.name}: no té metadata.yml")
        return False

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = yaml.safe_load(f) or {}

    obra = metadata.get('obra', {})
    titol = obra.get('titol', obra_dir.name)
    autor = obra.get('autor', obra_dir.parent.name)
    genere = get_genere_from_metadata(metadata)

    print(f"   📕 Generant portada per: {titol} ({genere})")

    try:
        from agents.portadista import generar_portada_obra
        import shutil

        # Obtenir temes del metadata
        temes = metadata.get('metadata_original', {}).get('tags', [])
        descripcio = metadata.get('obra', {}).get('descripcio', '')

        # Generar portada
        generar_portada_obra(
            titol=titol,
            autor=autor,
            genere=genere,
            temes=temes[:5] if temes else [],
            descripcio=descripcio,
            output_path=portada_path,
        )

        # Copiar també a web/assets/portades/ per al build
        web_portades = ROOT / 'web' / 'assets' / 'portades'
        web_portades.mkdir(parents=True, exist_ok=True)
        slug = f"{obra_dir.parent.name}-{obra_dir.name}"
        web_path = web_portades / f"{slug}-portada.png"
        shutil.copy(portada_path, web_path)

        print(f"   ✅ Portada generada: {portada_path}")
        print(f"   ✅ Copiada a: {web_path}")
        return True

    except ImportError as e:
        print(f"   ❌ No es pot importar l'agent portadista: {e}")
        print("      Assegura't que tens les dependències instal·lades.")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Genera portades per a les obres')
    parser.add_argument('--all', action='store_true', help='Regenera totes les portades')
    parser.add_argument('--obra', type=str, help='Genera per una obra específica (ex: plato/criton)')
    parser.add_argument('--list', action='store_true', help='Llista obres sense portada')
    args = parser.parse_args()

    obres_dir = ROOT / 'obres'

    print("═" * 50)
    print("GENERADOR DE PORTADES")
    print("═" * 50)
    print()

    if args.list:
        obres = find_obres_without_portada(obres_dir)
        print(f"Obres sense portada ({len(obres)}):")
        for obra in obres:
            print(f"  - {obra.parent.name}/{obra.name}")
        return

    if args.obra:
        # Generar per una obra específica
        obra_path = obres_dir / args.obra
        if not obra_path.exists():
            # Buscar recursivament
            for metadata_file in obres_dir.rglob('metadata.yml'):
                if args.obra in str(metadata_file):
                    obra_path = metadata_file.parent
                    break

        if obra_path.exists():
            generate_portada(obra_path, force=args.all)
        else:
            print(f"❌ Obra no trobada: {args.obra}")
        return

    # Generar per totes les obres sense portada (o totes si --all)
    if args.all:
        obres = list(obres_dir.rglob('metadata.yml'))
        obres = [m.parent for m in obres]
    else:
        obres = find_obres_without_portada(obres_dir)

    if not obres:
        print("✅ Totes les obres tenen portada!")
        return

    print(f"Generant portades per a {len(obres)} obres...")
    print()

    success = 0
    for obra in obres:
        if generate_portada(obra, force=args.all):
            success += 1

    print()
    print("═" * 50)
    print(f"✅ Portades generades: {success}/{len(obres)}")
    print("═" * 50)


if __name__ == '__main__':
    main()
