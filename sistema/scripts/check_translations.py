#!/usr/bin/env python3
"""check_translations.py — Analitza obra-queue.json i genera tasques FETCH/TRANSLATE"""
import json, os, sys

# Importar resolució canònica d'autors
sys.path.insert(0, os.path.join(os.path.expanduser('~/biblioteca-universal-arion'), 'sistema/config'))
from author_resolver import resolve_author, slugify

def task_exists_in_dir(titol, directory):
    if not os.path.isdir(directory): return False
    for f in os.listdir(directory):
        if f.endswith('.json'):
            try:
                if titol.lower() in open(os.path.join(directory, f)).read().lower():
                    return True
            except: pass
    return False

def main():
    project = os.path.expanduser('~/biblioteca-universal-arion')
    queue_path = os.path.join(project, 'sistema/state/obra-queue.json')
    tasks_dir = os.path.join(project, 'sistema/tasks')
    
    if not os.path.isfile(queue_path):
        sys.exit(0)
    
    queue = json.load(open(queue_path))
    
    for obra in queue.get('obres', []):
        status = obra.get('status', 'pending')
        if status in ('done', 'skip', 'validated'):
            continue
        
        autor = obra['autor']
        titol = obra['titol']
        llengua = obra.get('llengua', 'desconeguda')
        categoria = obra.get('categoria', 'filosofia')
        
        obra_dir_rel = obra.get('obra_dir', '')
        if obra_dir_rel:
            obra_dir = os.path.join(project, obra_dir_rel)
        else:
            slug_autor = resolve_author(autor, categoria)
            slug_titol = slugify(titol)
            obra_dir = os.path.join(project, 'obres', categoria, slug_autor, slug_titol)
        
        has_original = os.path.isfile(os.path.join(obra_dir, 'original.md'))
        has_translation = False
        has_dir = os.path.isdir(obra_dir)
        if has_dir:
            files = os.listdir(obra_dir)
            has_translation = any(
                f.endswith('.md') and any(k in f.lower() for k in ['traduccio', 'traducció', 'catala', 'català', 'chapter', 'capitol'])
                for f in files
            )
        
        if task_exists_in_dir(titol, os.path.join(tasks_dir, 'pending')):
            continue
        if task_exists_in_dir(titol, os.path.join(tasks_dir, 'running')):
            continue
        
        obra_dir_rel = obra_dir_rel or os.path.relpath(obra_dir, project)
        
        if has_translation:
            continue
        elif has_original:
            print(f'TRANSLATE|{autor}|{titol}|{llengua}|{obra_dir_rel}|{categoria}')
        else:
            print(f'FETCH|{autor}|{titol}|{llengua}|{obra_dir_rel}|{categoria}')

if __name__ == '__main__':
    main()
