#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
EDITORIAL CLÀSSICA - BUILD SCRIPT
Generador d'HTML a partir de contingut Markdown i YAML
Utilitza Jinja2 real per a templates
═══════════════════════════════════════════════════════════════════

Ús:
    python scripts/build.py                 # Construir tot
    python scripts/build.py --clean         # Netejar i reconstruir
    python scripts/build.py --watch         # Mode observació
"""

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Dependències externes
try:
    import yaml
except ImportError:
    print("❌ Error: PyYAML no instal·lat. Executa: pip install PyYAML")
    exit(1)

try:
    from jinja2 import Environment, FileSystemLoader
    from markupsafe import Markup
except ImportError:
    print("❌ Error: Jinja2 no instal·lat. Executa: pip install Jinja2")
    exit(1)

try:
    import markdown
    from markdown.extensions.footnotes import FootnoteExtension
except ImportError:
    print("❌ Error: python-markdown no instal·lat. Executa: pip install markdown")
    exit(1)


class MarkdownProcessor:
    """Processador de Markdown a HTML."""

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'extra',
                'smarty',
                'meta',
                FootnoteExtension(BACKLINK_TEXT='↩'),
            ],
            output_format='html5'
        )

    def convert(self, text: str) -> str:
        """Converteix Markdown a HTML."""
        self.md.reset()
        html = self.md.convert(text)
        return html

    def process_sections(self, text: str, lang: str = 'ca') -> str:
        """Processa text amb seccions numerades."""
        # Dividir per seccions (marcades amb ---)
        sections = re.split(r'\n---\s*\n', text)

        html_parts = []
        section_num = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Detectar si és un títol de capítol
            if section.startswith('# '):
                title_match = re.match(r'^# (.+)$', section, re.MULTILINE)
                if title_match:
                    title = title_match.group(1)
                    html_parts.append(f'<h2 class="section-title">{title}</h2>')
                    section = re.sub(r'^# .+\n*', '', section).strip()

            if section:
                section_num += 1
                section_id = f"{'orig' if lang == 'grc' else 'trad'}-{section_num}"
                parallel_id = f"{'trad' if lang == 'grc' else 'orig'}-{section_num}"

                # Processar termes del glossari
                section = self.process_terms(section)

                # Processar notes
                section = self.process_notes(section, section_num)

                html_content = self.convert(section)

                html_parts.append(f'''
                <div class="section" id="{section_id}" data-parallel="{parallel_id}">
                    <span class="section-number">[{section_num}]</span>
                    {html_content}
                </div>
                ''')

        return '\n'.join(html_parts)

    def process_terms(self, text: str) -> str:
        """Converteix [text]{.term data-term="id"} a HTML."""
        pattern = r'\[([^\]]+)\]\{\.term\s+data-term="([^"]+)"\}'
        replacement = r'<a href="#term-\2" class="term" data-term="\2">\1</a>'
        return re.sub(pattern, replacement, text)

    def process_notes(self, text: str, section_num: int) -> str:
        """Converteix [^n] a referències de notes."""
        def note_replacer(match):
            note_id = match.group(1)
            return f'<sup><a href="#nota-{note_id}" class="note-ref" id="ref-{note_id}">[{note_id}]</a></sup>'

        return re.sub(r'\[\^(\d+)\]', note_replacer, text)


class ContentLoader:
    """Carrega contingut d'una obra des dels fitxers."""

    def __init__(self, obra_path: Path):
        self.path = obra_path
        self.metadata = {}
        self.original = ""
        self.traduccio = ""
        self.notes = []
        self.glossari = []
        self.bibliografia = ""

    def load(self) -> bool:
        """Carrega tots els fitxers de l'obra."""
        if not self.path.exists():
            print(f"  ⚠️  Directori no trobat: {self.path}")
            return False

        # Metadata
        metadata_file = self.path / 'metadata.yml'
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = yaml.safe_load(f) or {}

        # Text original
        original_file = self.path / 'original.md'
        if original_file.exists():
            self.original = original_file.read_text(encoding='utf-8')

        # Traducció
        traduccio_file = self.path / 'traduccio.md'
        if traduccio_file.exists():
            self.traduccio = traduccio_file.read_text(encoding='utf-8')

        # Notes
        notes_file = self.path / 'notes.md'
        if notes_file.exists():
            self.notes = self.parse_notes(notes_file.read_text(encoding='utf-8'))

        # Glossari
        glossari_file = self.path / 'glossari.yml'
        if glossari_file.exists():
            with open(glossari_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self.glossari = data.get('termes', [])

        # Bibliografia
        biblio_file = self.path / 'bibliografia.md'
        if biblio_file.exists():
            self.bibliografia = biblio_file.read_text(encoding='utf-8')

        return True

    def parse_notes(self, text: str) -> List[Dict[str, Any]]:
        """Parseja fitxer de notes."""
        notes = []
        current_note = None
        md = MarkdownProcessor()

        for line in text.split('\n'):
            # Nova nota: ## [n] Títol
            match = re.match(r'^##\s*\[(\d+)\]\s*(.*)$', line)
            if match:
                if current_note:
                    current_note['contingut'] = Markup(md.convert('\n'.join(current_note['lines'])))
                    del current_note['lines']
                    notes.append(current_note)

                current_note = {
                    'id': match.group(1),
                    'titol': match.group(2).strip() or None,
                    'lines': [],
                    'refs': None
                }
            elif current_note:
                # Referències
                if line.startswith('> Vegeu:'):
                    current_note['refs'] = line[9:].strip()
                else:
                    current_note['lines'].append(line)

        # Última nota
        if current_note:
            current_note['contingut'] = Markup(md.convert('\n'.join(current_note['lines'])))
            del current_note['lines']
            notes.append(current_note)

        return notes


class BuildSystem:
    """Sistema de construcció principal."""

    def __init__(self, project_root: Path):
        self.root = project_root
        self.obres_dir = project_root / 'obres'
        self.docs_dir = project_root / 'docs'
        self.templates_dir = project_root / 'web' / 'templates'
        self.css_dir = project_root / 'web' / 'css'
        self.js_dir = project_root / 'web' / 'js'

        # Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False  # IMPORTANT: No escapar HTML
        )

        self.md = MarkdownProcessor()
        self.obres = []

    def build(self, clean: bool = False):
        """Construeix tot el lloc web."""
        print("═" * 60)
        print("EDITORIAL CLÀSSICA - BUILD")
        print("═" * 60)
        print()

        if clean:
            self.clean()

        # Crear directori docs
        self.docs_dir.mkdir(exist_ok=True)

        # Copiar fitxers estàtics
        self.copy_static()

        # Construir obres
        self.build_obres()

        # Construir índex
        self.build_index()

        print()
        print("═" * 60)
        print(f"✅ Construcció completada!")
        print(f"   Obres: {len(self.obres)}")
        print(f"   Sortida: {self.docs_dir}")
        print("═" * 60)

    def clean(self):
        """Neteja directori docs."""
        if self.docs_dir.exists():
            print("🗑️  Netejant docs/...")
            shutil.rmtree(self.docs_dir)
            print("   ✅ Netejat")
            print()

    def copy_static(self):
        """Copia CSS i JS."""
        print("📁 Copiant fitxers estàtics...")

        # CSS
        css_dest = self.docs_dir / 'css'
        css_dest.mkdir(exist_ok=True)
        if (self.css_dir / 'styles.css').exists():
            shutil.copy(self.css_dir / 'styles.css', css_dest / 'styles.css')
            print("   ✅ CSS copiat")

        # JS
        js_dest = self.docs_dir / 'js'
        js_dest.mkdir(exist_ok=True)
        if (self.js_dir / 'app.js').exists():
            shutil.copy(self.js_dir / 'app.js', js_dest / 'app.js')
            print("   ✅ JS copiat")

        print()

    def build_obres(self):
        """Construeix totes les obres."""
        print("📚 Construint obres...")
        print()

        if not self.obres_dir.exists():
            print(f"   ⚠️  Directori obres/ no existeix")
            return

        # Trobar totes les obres (estructura: obres/autor/obra/)
        for autor_dir in self.obres_dir.iterdir():
            if not autor_dir.is_dir():
                continue

            for obra_dir in autor_dir.iterdir():
                if not obra_dir.is_dir():
                    continue

                self.build_obra(obra_dir)

    def build_obra(self, obra_path: Path):
        """Construeix una obra individual."""
        slug = f"{obra_path.parent.name}-{obra_path.name}"
        print(f"   📖 {slug}...", end=' ')

        # Carregar contingut
        loader = ContentLoader(obra_path)
        if not loader.load():
            print("❌")
            return

        # Processar contingut
        contingut_original = Markup(
            self.md.process_sections(loader.original, lang='grc')
        )
        contingut_traduccio = Markup(
            self.md.process_sections(loader.traduccio, lang='ca')
        )

        # Bibliografia
        bibliografia = Markup(self.md.convert(loader.bibliografia)) if loader.bibliografia else None

        # Preparar dades de l'obra
        obra_data = loader.metadata.get('obra', {})
        obra = {
            'slug': slug,
            'titol': obra_data.get('titol', obra_path.name.title()),
            'titol_original': obra_data.get('titol_original'),
            'autor': obra_data.get('autor', obra_path.parent.name.title()),
            'autor_original': obra_data.get('autor_original'),
            'traductor': obra_data.get('traductor', 'Editorial Clàssica'),
            'llengua_original': obra_data.get('llengua_original', 'grec'),
            'any_original': obra_data.get('any_original'),
            'any_traduccio': obra_data.get('any_traduccio', datetime.now().year),
            'descripcio': obra_data.get('descripcio'),
            'estat': loader.metadata.get('revisio', {}).get('estat', 'esborrany'),
            'qualitat': loader.metadata.get('revisio', {}).get('qualitat'),
        }

        # Renderitzar template
        template = self.env.get_template('obra.html')
        html = template.render(
            base_url='',
            site_url='https://editorial-classica.cat',
            obra=obra,
            contingut_original=contingut_original,
            contingut_traduccio=contingut_traduccio,
            notes=loader.notes,
            glossari=loader.glossari,
            bibliografia=bibliografia,
        )

        # Guardar
        output_file = self.docs_dir / f"{slug}.html"
        output_file.write_text(html, encoding='utf-8')

        self.obres.append(obra)
        print("✅")

    def build_index(self):
        """Construeix pàgina índex."""
        print()
        print("📑 Construint índex...")

        # Estadístiques
        stats = {
            'total_obres': len(self.obres),
            'total_autors': len(set(o['autor'] for o in self.obres)),
            'total_paraules': sum(len(o.get('descripcio', '').split()) * 100 for o in self.obres),
        }

        # Renderitzar
        template = self.env.get_template('index.html')
        html = template.render(
            base_url='',
            site_url='https://editorial-classica.cat',
            active_page='index',
            obres=self.obres,
            stats=stats,
        )

        # Guardar
        output_file = self.docs_dir / 'index.html'
        output_file.write_text(html, encoding='utf-8')

        print("   ✅ Índex generat")


def main():
    parser = argparse.ArgumentParser(description='Build Editorial Clàssica')
    parser.add_argument('--clean', action='store_true', help='Netejar abans de construir')
    parser.add_argument('--watch', action='store_true', help='Mode observació')
    args = parser.parse_args()

    # Directori del projecte
    project_root = Path(__file__).parent.parent

    # Construir
    builder = BuildSystem(project_root)
    builder.build(clean=args.clean)

    # Mode watch
    if args.watch:
        print()
        print("👀 Mode watch activat. Prem Ctrl+C per sortir.")
        try:
            import time
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n✋ Aturat")


if __name__ == '__main__':
    main()
