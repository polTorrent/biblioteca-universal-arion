#!/usr/bin/env python3
"""update_queue_status.py — Actualitza estat a obra-queue.json"""
import json, os, unicodedata, re
from datetime import date

def slugify(text):
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def main():
    project = os.path.expanduser('~/biblioteca-universal-arion')
    queue_path = os.path.join(project, 'sistema/state/obra-queue.json')
    
    if not os.path.isfile(queue_path):
        print('queue_no_trobada')
        return
    
    queue = json.load(open(queue_path))
    updated = 0
    
    for obra in queue.get('obres', []):
        autor = obra['autor']
        titol = obra['titol']
        categoria = obra.get('categoria', 'filosofia')
        
        obra_dir_rel = obra.get('obra_dir', '')
        if obra_dir_rel:
            obra_dir = os.path.join(project, obra_dir_rel)
        else:
            obra_dir = os.path.join(project, 'obres', categoria, slugify(autor), slugify(titol))
        
        if os.path.isdir(obra_dir):
            files = os.listdir(obra_dir)
            has_md = any(f.endswith('.md') for f in files)
            has_meta = 'metadata.yml' in files or 'metadata.json' in files
            has_validated = '.validated' in files
            
            if has_validated: new_status = 'validated'
            elif has_md and has_meta: new_status = 'done'
            elif has_md or len(files) > 0: new_status = 'in_progress'
            else: new_status = 'pending'
        else:
            new_status = 'pending'
        
        if obra.get('status') != new_status:
            obra['status'] = new_status
            updated += 1
    
    if updated > 0:
        queue['updated_at'] = date.today().isoformat()
        with open(queue_path, 'w') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        print(f'{updated} obres actualitzades')
    else:
        print('cap_canvi')

if __name__ == '__main__':
    main()
