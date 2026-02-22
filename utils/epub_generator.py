"""Generador automàtic d'EPUB per a la Biblioteca Universal Arion.

Recull els documents Markdown d'una obra i les seves metadades YAML globals,
empelta les imatges pregenerades i els processa fins a exportar un llibre digital autònom.
"""

import os
import yaml
import markdown
from pathlib import Path
from bs4 import BeautifulSoup
from ebooklib import epub

def generar_epub(dir_obra: str, output_path: str = None) -> str:
    """Genera l'arxiu EPUB d'una obra a partir d'un directori donat."""
    obra_path = Path(dir_obra)
    
    # Llegir metadades YAML
    yaml_files = list(obra_path.glob("*.yml")) + list(obra_path.glob("*.yaml"))
    metadades = {}
    if yaml_files:
        with open(yaml_files[0], 'r', encoding='utf-8') as f:
            metadades = yaml.safe_load(f) or {}

    titol = metadades.get('titol', obra_path.name.capitalize())
    autor = metadades.get('autor', 'Autor Desconegut')
    idioma = metadades.get('idioma', 'ca')
    
    llibre = epub.EpubBook()
    llibre.set_title(titol)
    llibre.set_language(idioma)
    llibre.add_author(autor)
    llibre.add_metadata('DC', 'description', metadades.get('descripcio', ''))

    # Cerca imatge de portada
    portada = None
    extensions_img = ['.jpg', '.jpeg', '.png']
    for ext in extensions_img:
        p = obra_path / f"portada{ext}"
        if p.exists():
            portada = p
            break
            
    if portada:
        with open(portada, 'rb') as f:
            llibre.set_cover("portada.jpg", f.read())

    # Trobar i processar fitxers Markdown (.md)
    md_files = sorted(obra_path.glob("*.md"))
    capitols = []
    nav_links = []

    for index, md_file in enumerate(md_files):
        with open(md_file, 'r', encoding='utf-8') as f:
            contingut_md = f.read()
        
        # Converteix MD a HTML
        html_contingut = markdown.markdown(contingut_md)
        base_name = md_file.stem
        
        # Converteix HTML en capítol EPUB
        capitol = epub.EpubHtml(title=base_name, file_name=f"{base_name}.xhtml", lang=idioma)
        capitol.content = f'<h1>{base_name}</h1>{html_contingut}'
        llibre.add_item(capitol)
        capitols.append(capitol)
        nav_links.append(capitol)

    # Definir la taula de continguts (TOC) i estructura del llibre (spine)
    llibre.toc = tuple(nav_links)
    llibre.add_item(epub.EpubNcx())
    llibre.add_item(epub.EpubNav())
    
    # Comprovar si tenim portada per incloure-la visualment o establir l'spine per defecte
    spine = ['nav'] + capitols
    llibre.spine = spine

    if output_path is None:
        out_name = f"{titol.replace(' ', '_')}.epub"
        output_path = obra_path / out_name
        
    epub.write_epub(str(output_path), llibre, {})
    return str(output_path)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Ús: python epub_generator.py <ruta/a/obra>")
        sys.exit(1)
    
    ruta = sys.argv[1]
    out_epub = generar_epub(ruta)
    print(f"EPUB generat a: {out_epub}")
