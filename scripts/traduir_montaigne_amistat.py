#!/usr/bin/env python3
"""Traducció de 'De l'Amitié' de Michel de Montaigne.

Assaig sobre l'amistat del llibre I dels Essais (1595).
Text original en francès mitjà del Renaixement.
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
            'titol_original': "De l'Amitié",
            'autor': autor,
            'autor_original': 'Michel de Montaigne',
            'traductor': 'Biblioteca Arion (IA + comunitat)',
            'any_original': 1580,  # Primera edició dels Essais
            'any_traduccio': datetime.now().year,
            'llengua_original': llengua,
            'genere': genere,
            'descripcio': "Assaig sobre l'amistat perfecta, escrit en record d'Étienne de La Boétie. Capítol XXVII del Llibre I dels Essais.",
        }
    }

    obra_dir.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ
# ═══════════════════════════════════════════════════════════════════════════════

# Ruta a l'obra
OBRA_PATH = "filosofia/montaigne/de-l-amistat"

# Metadades de l'obra
TITOL = "De l'amistat"
AUTOR = "Michel de Montaigne"
LLENGUA_ORIGEN = "francès"
GENERE = "filosofia"

# Configuració del pipeline
CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 2500,  # Chunks petits per a millor qualitat
    "fer_avaluacio": True,
    "fer_refinament": True,
    "llindar_qualitat": 7.5,
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
        print(f"Error: No existeix {original_path}")
        print(f"   Crea primer el fitxer original.md a {obra_dir}")
        sys.exit(1)

    # Llegir text original
    print("=" * 60)
    print(f"  TRADUCCIÓ: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} -> català")
    print("=" * 60)
    print()

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    # Netejar metadades de fonts digitals
    text_original = netejar_metadades_font(text_original)

    # Netejar capçalera si existeix (buscar primer paràgraf)
    text_narratiu = text_original

    # Detectar inici del contingut (primer paràgraf després de ---)
    import re
    match = re.search(r'^---\s*$', text_original, re.MULTILINE)
    if match:
        # Buscar el contingut després del primer ---
        rest = text_original[match.end():]
        match2 = re.search(r'\n\n([A-Z])', rest)
        if match2:
            text_narratiu = rest[match2.start():].strip()

    # Treure peu de pàgina si existeix
    for footer in ['*Text de domini públic', '*Traducció de domini públic', '---\n\n*', '*Font:']:
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
    print("=" * 60)
    print("  TRADUCCIÓ COMPLETADA I PUBLICADA")
    print("=" * 60)

    return resultat


if __name__ == "__main__":
    main()
