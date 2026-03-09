#!/usr/bin/env python3
"""Debug script per la pipeline."""
import os, sys
os.environ['CLAUDECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("DEBUG: script starting", flush=True)

from pathlib import Path

obra_dir = Path(sys.argv[1]) if os.path.isabs(sys.argv[1]) else Path(__file__).parent.parent / sys.argv[1]
print(f"DEBUG: obra_dir exists: {obra_dir.exists()}", flush=True)

original_path = obra_dir / 'original.md'
print(f"DEBUG: original.md size: {original_path.stat().st_size}", flush=True)

with open(original_path) as f:
    text = f.read()
print(f"DEBUG: text length: {len(text)}", flush=True)

from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio
print("DEBUG: Pipeline imported OK", flush=True)

config = ConfiguracioPipelineV2(
    directori_obra=obra_dir,
    fer_analisi_previa=True,
    crear_glossari=True,
    fer_chunking=True,
    max_chars_chunk=3500,
    fer_avaluacio=True,
    fer_refinament=True,
    llindars=LlindarsAvaluacio(global_minim=7.5, max_iteracions=2),
    mostrar_dashboard=False,
)
pipeline = PipelineV2(config=config)
print("DEBUG: Pipeline created, starting traduir...", flush=True)

try:
    resultat = pipeline.traduir(
        text=text,
        llengua_origen="llatí",
        autor="Petroni",
        obra="Cena Trimalchionis",
        genere="narrativa",
    )
    print(f"DEBUG: traduir returned: {type(resultat)}", flush=True)
    print(resultat.resum(), flush=True)
except Exception as e:
    print(f"DEBUG: Error: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
