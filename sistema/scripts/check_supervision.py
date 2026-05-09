#!/usr/bin/env python3
"""check_supervision.py — Busca traduccions sense validar"""
import os
from pathlib import Path

def main():
    project = Path(os.path.expanduser('~/biblioteca-universal-arion'))
    obres_dir = project / 'obres'
    tasks_done = project / 'sistema/tasks/done'
    
    if not obres_dir.exists():
        return
    
    for categoria in obres_dir.iterdir():
        if not categoria.is_dir(): continue
        for autor in categoria.iterdir():
            if not autor.is_dir(): continue
            for obra in autor.iterdir():
                if not obra.is_dir(): continue
                
                files = list(obra.iterdir())
                filenames = [f.name for f in files]
                
                has_translation = any(
                    f.suffix in ('.md', '.txt') and any(k in f.name.lower() for k in ['traduccio', 'traducció', 'catala', 'català', 'chapter', 'capitol'])
                    for f in files
                )
                if not has_translation: continue
                
                has_metadata = 'metadata.yml' in filenames or 'metadata.json' in filenames
                has_validated = '.validated' in filenames
                
                if has_validated: continue
                
                obra_name = obra.name
                has_recent_review = False
                if tasks_done.exists():
                    for done_file in tasks_done.glob('*.json'):
                        try:
                            content = done_file.read_text()
                            if 'supervis' in content.lower() and obra_name in content.lower():
                                has_recent_review = True
                                break
                        except: pass
                
                if has_recent_review: continue
                
                relpath = str(obra.relative_to(project))
                
                if not has_metadata:
                    print(f'MISSING_META|{relpath}|{autor.name}|{obra_name}')
                else:
                    print(f'NEEDS_REVIEW|{relpath}|{autor.name}|{obra_name}')

if __name__ == '__main__':
    main()
