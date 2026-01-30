#!/usr/bin/env python3
"""Template per traduir una obra nova.

INSTRUCCIONS:
1. Copia aquest fitxer amb un nom descriptiu (ex: traduir_nom_obra.py)
2. Modifica les variables de configuració a la secció CONFIGURACIÓ
3. Executa: python scripts/traduir_nom_obra.py

El procés farà:
1. Llegir el text original
2. Crear glossari terminològic
3. Traduir amb avaluació i refinament
4. Formatar capítols (original i traducció)
5. Generar portada
6. Actualitzar metadata
7. Publicar a la web (build)
"""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Afegir el directori arrel al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from datetime import datetime
import yaml

from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio
from scripts.post_traduccio import post_processar_traduccio, netejar_metadades_font


def crear_metadata_yml(obra_dir: Path, titol: str, autor: str, llengua: str, genere: str) -> None:
    """Crea o actualitza metadata.yml amb el format correcte (clau 'obra:' a l'arrel)."""
    metadata_path = obra_dir / "metadata.yml"

    # Si existeix, verificar format
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            existing = yaml.safe_load(f) or {}

        # Si ja té la clau 'obra:', no cal fer res
        if 'obra' in existing:
            return

        # Si té dades però sense 'obra:', migrar al nou format
        if 'titol' in existing:
            new_metadata = {
                'obra': {
                    'titol': existing.get('titol', titol),
                    'titol_original': existing.get('titol_original'),
                    'autor': existing.get('autor', autor),
                    'autor_original': existing.get('autor_original'),
                    'traductor': existing.get('traductor', 'Biblioteca Arion (IA + comunitat)'),
                    'any_original': existing.get('any_original'),
                    'any_traduccio': datetime.now().year,
                    'llengua_original': existing.get('llengua_origen') or existing.get('llengua_original') or llengua,
                    'genere': existing.get('genere', genere),
                    'descripcio': existing.get('descripcio', ''),
                }
            }
            # Preservar altres camps
            if 'revisio' in existing:
                new_metadata['revisio'] = existing['revisio']
            if 'estadistiques' in existing:
                new_metadata['obra']['estadistiques'] = existing['estadistiques']

            with open(metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return

    # Crear nou metadata
    metadata = {
        'obra': {
            'titol': titol,
            'autor': autor,
            'traductor': 'Biblioteca Arion (IA + comunitat)',
            'any_traduccio': datetime.now().year,
            'llengua_original': llengua,
            'genere': genere,
            'descripcio': '',
        }
    }

    obra_dir.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ - MODIFICA AQUESTES VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# Ruta a l'obra (relatiu a la carpeta obres/)
# Ex: "narrativa/akutagawa/biombo-infern", "filosofia/plato/criton"
OBRA_PATH = "narrativa/AUTOR/NOM_OBRA"

# Metadades de l'obra
TITOL = "Títol de l'Obra"
AUTOR = "Nom de l'Autor"
LLENGUA_ORIGEN = "anglès"  # japonès, grec, alemany, llatí, etc.
GENERE = "narrativa"  # narrativa, filosofia, poesia, teatre

# Configuració del pipeline
CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 2500,  # Chunks més petits = millor qualitat però més lent
    "fer_avaluacio": True,
    "fer_refinament": True,
    "llindar_qualitat": 7.5,  # Puntuació mínima per aprovar
    "max_iteracions_refinament": 2,
    "mostrar_dashboard": True,
    "dashboard_port": 5050,
}

# ═══════════════════════════════════════════════════════════════════════════════
# NO MODIFICAR A PARTIR D'AQUÍ
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Executa la traducció."""

    # Rutes
    base_dir = Path(__file__).parent.parent
    obra_dir = base_dir / "obres" / OBRA_PATH
    original_path = obra_dir / "original.md"
    traduccio_path = obra_dir / "traduccio.md"

    # Crear/verificar metadata.yml amb format correcte
    crear_metadata_yml(obra_dir, TITOL, AUTOR, LLENGUA_ORIGEN, GENERE)

    # Verificar que existeix l'original
    if not original_path.exists():
        print(f"❌ Error: No existeix {original_path}")
        print(f"   Crea primer el fitxer original.md a {obra_dir}")
        sys.exit(1)

    # Llegir text original
    print("═" * 60)
    print(f"  TRADUCCIÓ: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} → català")
    print("═" * 60)
    print()

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    # Netejar metadades de fonts digitals (Aozora Bunko, Project Gutenberg, etc.)
    text_original = netejar_metadades_font(text_original)

    # Netejar capçalera si existeix (buscar primer capítol)
    text_narratiu = text_original

    # Detectar inici del contingut (primer ## o primer capítol numerat)
    import re
    match = re.search(r'^(##\s+|[一二三四五六七八九十]+\s*$|[IVXLCDM]+\s*$)', text_original, re.MULTILINE)
    if match:
        text_narratiu = text_original[match.start():]

    # Treure peu de pàgina si existeix
    for footer in ['*Text de domini públic', '*Traducció de domini públic', '---\n\n*']:
        if footer in text_narratiu:
            text_narratiu = text_narratiu.split(footer)[0].strip()

    print(f"Text original: {len(text_narratiu)} caràcters")
    print()

    # Configurar pipeline
    config = ConfiguracioPipelineV2(
        fer_analisi_previa=CONFIG["fer_analisi_previa"],
        crear_glossari=CONFIG["crear_glossari"],
        fer_chunking=CONFIG["fer_chunking"],
        max_chars_chunk=CONFIG["max_chars_chunk"],
        fer_avaluacio=CONFIG["fer_avaluacio"],
        fer_refinament=CONFIG["fer_refinament"],
        llindars=LlindarsAvaluacio(
            global_minim=CONFIG["llindar_qualitat"],
            max_iteracions=CONFIG["max_iteracions_refinament"],
        ),
        mostrar_dashboard=CONFIG["mostrar_dashboard"],
        dashboard_port=CONFIG["dashboard_port"],
    )

    # Crear i executar pipeline
    pipeline = PipelineV2(config=config)

    print("Iniciant traducció amb Pipeline V2...")
    if CONFIG["mostrar_dashboard"]:
        print(f"(Dashboard a http://localhost:{CONFIG['dashboard_port']})")
    print()

    resultat = pipeline.traduir(
        text=text_narratiu,
        llengua_origen=LLENGUA_ORIGEN,
        autor=AUTOR,
        obra=TITOL,
        genere=GENERE,
    )

    # Guardar traducció
    traduccio_final = f"""# {TITOL}
*{AUTOR}*

Traduït del {LLENGUA_ORIGEN} per Biblioteca Arion

---

{resultat.traduccio_final}

---

*Traducció de domini públic.*
"""

    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(traduccio_final)

    # Mostrar resum
    print()
    print(resultat.resum())
    print()
    print(f"Traducció guardada a: {traduccio_path}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # POST-PROCESSAMENT AUTOMÀTIC
    # ═══════════════════════════════════════════════════════════════════════════════
    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    print()
    print("═" * 60)
    print("  ✅ TRADUCCIÓ COMPLETADA I PUBLICADA")
    print("═" * 60)

    return resultat


if __name__ == "__main__":
    main()
