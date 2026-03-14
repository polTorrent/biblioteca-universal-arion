#!/usr/bin/env python3
"""Temporary script to debug pipeline execution."""
import os, sys, re
os.environ['CLAUDECODE'] = '1'
sys.path.insert(0, '.')
from pathlib import Path
import yaml

obra_dir = Path('obres/oriental/yoshida-kenko/tsurezuregusa')

meta_path = obra_dir / 'metadata.yml'
with open(meta_path) as f:
    meta = yaml.safe_load(f)
obra = meta.get('obra', meta)
titol = obra.get('titol', obra_dir.name)
autor = obra.get('autor', obra_dir.parent.name)
llengua = obra.get('llengua_original', 'llatí')
genere = obra.get('genere', 'narrativa')

original_path = obra_dir / 'original.md'
with open(original_path) as f:
    text_original = f.read()

print(f'Text original: {len(text_original)} chars')

match = re.search(r'^(##\s+|[一二三四五六七八九十]+\s*$|[IVXLCDM]+\s*$)', text_original, re.MULTILINE)
if match:
    text_narratiu = text_original[match.start():]
    print(f'Content starts at char {match.start()}')
else:
    text_narratiu = text_original
    print('No match found, using full text')

# Strip footers
for footer in ['*Text de domini públic', '*Traducció de domini públic']:
    if footer in text_narratiu:
        text_narratiu = text_narratiu.split(footer)[0].strip()

print(f'Text narratiu: {len(text_narratiu)} chars')

from agents.v2 import PipelineV2, ConfiguracioPipelineV2
from agents.v2.models import LlindarsAvaluacio

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
print('Pipeline created, starting translation...')
sys.stdout.flush()

try:
    resultat = pipeline.traduir(
        text=text_narratiu,
        llengua_origen=llengua,
        autor=autor,
        obra=titol,
        genere=genere,
    )
    print(f'DONE! Translation length: {len(resultat.traduccio_final)}')
    print(resultat.resum())

    traduccio_path = obra_dir / 'traduccio.md'
    traduccio_final = f"# {titol}\n*{autor}*\n\nTraduït del {llengua} per Biblioteca Arion\n\n---\n\n{resultat.traduccio_final}\n\n---\n\n*Traducció de domini públic.*\n"
    with open(traduccio_path, 'w', encoding='utf-8') as f:
        f.write(traduccio_final)
    print(f'Saved to {traduccio_path}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
