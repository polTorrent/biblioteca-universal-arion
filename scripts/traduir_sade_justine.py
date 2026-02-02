#!/usr/bin/env python3
"""Traducció de Justine ou les Malheurs de la vertu del Marquès de Sade.

Novel·la filosòfica de 1791.
Text original: ~113.000 paraules (obra extensa)
Font: Wikisource (domini públic)
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
    """Crea o actualitza metadata.yml amb el format correcte."""
    metadata_path = obra_dir / "metadata.yml"

    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            existing = yaml.safe_load(f) or {}
        if 'obra' in existing:
            return

    metadata = {
        'obra': {
            'titol': titol,
            'titol_original': 'Justine, ou les Malheurs de la vertu',
            'autor': autor,
            'autor_original': 'Donatien Alphonse François de Sade',
            'traductor': 'Biblioteca Arion (IA + comunitat)',
            'any_original': 1791,
            'any_traduccio': datetime.now().year,
            'llengua_original': llengua,
            'genere': genere,
            'descripcio': "Primera novel·la publicada del Marquès de Sade, escrita durant el seu empresonament a la Bastilla. Una reflexió filosòfica sobre la virtut, el vici i la injustícia del destí, a través de les desgràcies de la virtuosa Justine.",
            'font': 'Wikisource (domini públic)',
        }
    }

    obra_dir.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ
# ═══════════════════════════════════════════════════════════════════════════════

OBRA_PATH = "narrativa/sade/justine"
TITOL = "Justine o els Infortunis de la Virtut"
AUTOR = "Marquès de Sade"
LLENGUA_ORIGEN = "francès"
GENERE = "narrativa"

# Configuració del pipeline - optimitzada per obra llarga
CONFIG = {
    "fer_analisi_previa": True,
    "crear_glossari": True,
    "fer_chunking": True,
    "max_chars_chunk": 3000,  # Chunks moderats per obra llarga
    "fer_avaluacio": True,
    "fer_refinament": True,
    "llindar_qualitat": 7.0,  # Llindar més flexible per obra llarga
    "max_iteracions_refinament": 1,  # Menys iteracions per eficiència
    "mostrar_dashboard": True,
    "dashboard_port": 5050,
    # Anotació crítica
    "generar_anotacions": True,
    "densitat_notes": "normal",  # minima/normal/exhaustiva
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

    # Crear/verificar metadata.yml
    crear_metadata_yml(obra_dir, TITOL, AUTOR, LLENGUA_ORIGEN, GENERE)

    # Verificar que existeix l'original
    if not original_path.exists():
        print(f"❌ Error: No existeix {original_path}")
        sys.exit(1)

    # Llegir text original
    print("═" * 70)
    print(f"  TRADUCCIÓ: {TITOL}")
    print(f"  Autor: {AUTOR}")
    print(f"  Llengua: {LLENGUA_ORIGEN} → català")
    print("═" * 70)
    print()

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    # Netejar metadades
    text_original = netejar_metadades_font(text_original)

    # Detectar inici del contingut narratiu
    import re
    text_narratiu = text_original

    # Treure capçalera editorial si existeix
    match = re.search(r'À MA BONNE AMIE\.?\s*\n', text_original, re.IGNORECASE)
    if match:
        text_narratiu = text_original[match.start():]

    print(f"Text original: {len(text_narratiu):,} caràcters")
    print(f"Paraules aproximades: {len(text_narratiu.split()):,}")
    print()
    print("⚠️  ATENCIÓ: Aquesta és una obra molt extensa.")
    print("    La traducció completa pot trigar diverses hores.")
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
        generar_anotacions=CONFIG.get("generar_anotacions", True),
        densitat_notes=CONFIG.get("densitat_notes", "normal"),
    )

    # Crear i executar pipeline
    pipeline = PipelineV2(config=config)

    print("Iniciant traducció amb Pipeline V2...")
    if CONFIG["mostrar_dashboard"]:
        print(f"Dashboard: http://localhost:{CONFIG['dashboard_port']}")
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

    # Post-processament automàtic
    post_processar_traduccio(
        obra_dir=obra_dir,
        resultat=resultat,
        generar_portada_auto=True,
        executar_build_auto=True,
    )

    print()
    print("═" * 70)
    print("  ✅ TRADUCCIÓ COMPLETADA I PUBLICADA")
    print("═" * 70)

    return resultat


if __name__ == "__main__":
    main()
