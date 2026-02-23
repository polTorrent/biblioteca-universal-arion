#!/usr/bin/env python3
"""Script genèric per traduir qualsevol obra amb Pipeline V2.

Ús:
    python3 scripts/traduir_pipeline.py obres/filosofia/seneca/de-brevitate-vitae/
    python3 scripts/traduir_pipeline.py obres/narrativa/kafka/metamorfosi/

Llegeix metadata.yml per obtenir títol, autor, llengua i gènere automàticament.
"""

import os
import sys
import re

# CLAUDECODE=1 per usar subscripció (cost €0)
os.environ["CLAUDECODE"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import yaml

from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio

try:
    from scripts.post_traduccio import post_processar_traduccio, netejar_metadades_font
except ImportError:
    post_processar_traduccio = None
    netejar_metadades_font = lambda t: t

try:
    from scripts.utils import crear_metadata_yml
except ImportError:
    crear_metadata_yml = None


def carregar_metadata(obra_dir: Path) -> dict:
    """Carrega metadata.yml i extreu info necessària."""
    meta_path = obra_dir / "metadata.yml"
    if not meta_path.exists():
        # Intentar deduir de l'estructura de directoris
        parts = obra_dir.parts
        # obres/categoria/autor/obra
        return {
            "titol": obra_dir.name.replace("-", " ").title(),
            "autor": obra_dir.parent.name.replace("-", " ").title(),
            "llengua": "llatí",
            "genere": parts[-3] if len(parts) >= 3 else "narrativa",
        }

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}

    obra = meta.get("obra", meta)
    return {
        "titol": obra.get("titol", obra.get("title", obra_dir.name)),
        "autor": obra.get("autor", obra.get("author", obra_dir.parent.name)),
        "llengua": obra.get("llengua_original", obra.get("source_language", "llatí")),
        "genere": obra.get("genere", obra.get("category", "narrativa")),
    }


def main():
    if len(sys.argv) < 2:
        print("Ús: python3 scripts/traduir_pipeline.py <ruta_obra>")
        print("Ex:  python3 scripts/traduir_pipeline.py obres/filosofia/seneca/de-brevitate-vitae/")
        sys.exit(1)

    # Ruta de l'obra
    base_dir = Path(__file__).parent.parent
    obra_rel = sys.argv[1].rstrip("/")
    
    # Suportar tant ruta absoluta com relativa
    if os.path.isabs(obra_rel):
        obra_dir = Path(obra_rel)
    else:
        obra_dir = base_dir / obra_rel

    if not obra_dir.exists():
        print(f"❌ No existeix: {obra_dir}")
        sys.exit(1)

    # Carregar metadata
    meta = carregar_metadata(obra_dir)
    titol = meta["titol"]
    autor = meta["autor"]
    llengua = meta["llengua"]
    genere = meta["genere"]

    # Verificar original.md
    original_path = obra_dir / "original.md"
    if not original_path.exists():
        print(f"❌ No existeix original.md a {obra_dir}")
        sys.exit(1)

    # Llegir text
    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    text_original = netejar_metadades_font(text_original)

    # Detectar inici del contingut
    match = re.search(r'^(##\s+|[一二三四五六七八九十]+\s*$|[IVXLCDM]+\s*$)', text_original, re.MULTILINE)
    if match:
        text_narratiu = text_original[match.start():]
    else:
        text_narratiu = text_original

    # Treure peu de pàgina
    for footer in ['*Text de domini públic', '*Traducció de domini públic', '---\n\n*']:
        if footer in text_narratiu:
            text_narratiu = text_narratiu.split(footer)[0].strip()

    print("═" * 60)
    print(f"  TRADUCCIÓ: {titol}")
    print(f"  Autor: {autor}")
    print(f"  Llengua: {llengua} → català")
    print(f"  Gènere: {genere}")
    print(f"  Text: {len(text_narratiu)} caràcters")
    print("═" * 60)

    # Decidir chunking segons mida
    fer_chunking = len(text_narratiu) > 3000
    max_chars = 2500 if genere == "filosofia" else 3500

    config = ConfiguracioPipelineV2(
        directori_obra=obra_dir,
        fer_analisi_previa=True,
        crear_glossari=True,
        fer_chunking=fer_chunking,
        max_chars_chunk=max_chars,
        fer_avaluacio=True,
        fer_refinament=True,
        llindars=LlindarsAvaluacio(
            global_minim=7.5,
            max_iteracions=2,
        ),
        mostrar_dashboard=False,  # Worker no té navegador
    )

    # Executar pipeline
    pipeline = PipelineV2(config=config)
    resultat = pipeline.traduir(
        text=text_narratiu,
        llengua_origen=llengua,
        autor=autor,
        obra=titol,
        genere=genere,
    )

    # Guardar traducció
    traduccio_path = obra_dir / "traduccio.md"
    traduccio_final = f"""# {titol}
*{autor}*

Traduït del {llengua} per Biblioteca Arion

---

{resultat.traduccio_final}

---

*Traducció de domini públic.*
"""
    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(traduccio_final)

    print(f"\n✅ Traducció guardada a: {traduccio_path}")
    print(resultat.resum())

    # Post-processament
    if post_processar_traduccio:
        post_processar_traduccio(
            obra_dir=obra_dir,
            resultat=resultat,
            generar_portada_auto=False,  # Venice pot no estar disponible
            executar_build_auto=False,   # El heartbeat s'encarrega
        )

    # Eliminar .needs_fix o .fixing si existeix (traducció completada)
    for f in [".needs_fix", ".fixing"]:
        p = obra_dir / f
        if p.exists():
            p.unlink()
            print(f"   🗑️ Eliminat {f}")

    print("\n═" * 60)
    print("  ✅ TRADUCCIÓ PIPELINE V2 COMPLETADA")
    print("═" * 60)


if __name__ == "__main__":
    main()
