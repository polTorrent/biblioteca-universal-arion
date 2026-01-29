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

    def process_sections(self, text: str, lang: str = 'ca', glossari: list = None) -> str:
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

                # Processar termes del glossari (suporta V1 i V2)
                section = self.process_terms(section, glossari)

                # Processar notes
                section = self.process_notes(section, section_num)

                html_content = self.convert(section)

                html_parts.append(f'''
                <div class="section" id="{section_id}" data-parallel="{parallel_id}">
                    {html_content}
                </div>
                ''')

        return '\n'.join(html_parts)

    def process_terms(self, text: str, glossari: list = None) -> str:
        """Converteix termes del glossari a HTML.

        Suporta dos formats:
        1. Format V1: [text]{.term data-term="id"}
        2. Format V2: terme[T]
        """
        # Format V1: [text]{.term data-term="id"}
        pattern_v1 = r'\[([^\]]+)\]\{\.term\s+data-term="([^"]+)"\}'
        replacement_v1 = r'<a href="#term-\2" class="term" data-term="\2">\1</a>'
        text = re.sub(pattern_v1, replacement_v1, text)

        # Format V2: terme[T] - requereix glossari per buscar l'id
        if glossari:
            text = self.process_term_markers(text, glossari)

        return text

    def process_term_markers(self, text: str, glossari: list) -> str:
        """Converteix terme[T] a enllaços del glossari (format V2)."""
        if not glossari:
            return text

        # Crear diccionari de termes coneguts
        termes_coneguts = {}
        for terme in glossari:
            term_id = terme.get('id', '')
            # Afegir variants: transliteracio, traduccio
            trans = terme.get('transliteracio', '').lower()
            trad = terme.get('traduccio', '').lower()
            if trans:
                termes_coneguts[trans] = term_id
            if trad:
                termes_coneguts[trad] = term_id
            # Afegir també l'id com a clau
            if term_id:
                termes_coneguts[term_id.lower()] = term_id

        # Patró simple: paraula[T]
        pattern = r'(\S+)\[T\]'

        def replacer(match):
            terme = match.group(1)
            terme_lower = terme.lower()
            if terme_lower in termes_coneguts:
                term_id = termes_coneguts[terme_lower]
                return f'<a href="#term-{term_id}" class="term" data-term="{term_id}">{terme}</a>'
            # Si no trobat, retornar el terme sense marca [T]
            return terme

        return re.sub(pattern, replacer, text)

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

    def _strip_v2_header(self, text: str) -> str:
        """Elimina la capçalera de metadades V2 del text de traducció.

        La capçalera V2 té el format:
        # Títol
        ## Subtítol
        **Autor:** ...
        **Metadades de qualitat:**
        - ...
        ---
        # Títol repetit (opcional)
        Autor repetit (opcional)

        ## I (primer capítol real)
        """
        if not text:
            return text

        lines = text.split('\n')
        content_start = 0

        # Buscar el primer separador --- que indica fi de capçalera
        for i, line in enumerate(lines):
            if line.strip() == '---':
                content_start = i + 1
                break

        if content_start > 0:
            # Ara buscar el primer capítol real (## seguit de número romà o català)
            remaining_lines = lines[content_start:]
            chapter_start = 0

            for i, line in enumerate(remaining_lines):
                stripped = line.strip()
                # Detectar inici de capítol: ## I, ## II, ## 1, ## Capítol, etc.
                if stripped.startswith('## '):
                    chapter_title = stripped[3:].strip()
                    # Si és un número romà, número aràbic, o paraula de capítol
                    if (self._is_chapter_marker(chapter_title)):
                        chapter_start = i
                        break

            return '\n'.join(remaining_lines[chapter_start:]).strip()

        return text

    def _is_chapter_marker(self, text: str) -> bool:
        """Detecta si el text és un marcador de capítol vàlid."""
        text = text.strip()
        # Números romans
        if re.match(r'^[IVXLCDM]+$', text, re.IGNORECASE):
            return True
        # Números aràbics
        if re.match(r'^\d+$', text):
            return True
        # Paraules catalanes de números
        catalan_numbers = ['un', 'dos', 'tres', 'quatre', 'cinc', 'sis', 'set',
                          'vuit', 'nou', 'deu', 'onze', 'dotze', 'tretze',
                          'catorze', 'quinze', 'setze', 'disset', 'divuit',
                          'dinou', 'vint']
        if text.lower() in catalan_numbers:
            return True
        return False

    def _strip_title_author(self, text: str) -> str:
        """Elimina títol i autor del principi del text original.

        Busca el primer capítol (## I, ## 1, etc.) i retorna tot a partir d'allà.
        """
        if not text:
            return text

        lines = text.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Detectar inici de capítol: ## seguit de número
            if stripped.startswith('## '):
                chapter_title = stripped[3:].strip()
                if self._is_chapter_marker(chapter_title):
                    return '\n'.join(lines[i:]).strip()

        return text

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
            raw_original = original_file.read_text(encoding='utf-8')
            # Eliminar títol/autor del principi (començar des del primer capítol)
            self.original = self._strip_title_author(raw_original)

        # Traducció
        traduccio_file = self.path / 'traduccio.md'
        if traduccio_file.exists():
            raw_traduccio = traduccio_file.read_text(encoding='utf-8')
            # Eliminar capçalera V2 amb metadades si existeix
            self.traduccio = self._strip_v2_header(raw_traduccio)

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

        # Construir pàgines de mecenatge
        self.build_mecenatge()

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

        # Fitxers CSS a copiar
        css_files = [
            'styles.css',
            'mecenatge.css',
            'perfil.css',
            'usuari-public.css',
            'favorits-carret.css'
        ]

        for css_file in css_files:
            if (self.css_dir / css_file).exists():
                shutil.copy(self.css_dir / css_file, css_dest / css_file)
                print(f"   ✅ {css_file} copiat")

        # JS
        js_dest = self.docs_dir / 'js'
        js_dest.mkdir(exist_ok=True)

        # Fitxers JS a copiar
        js_files = [
            'app.js',
            'mecenatge.js',
            'supabase-client.js',
            'auth-manager.js',
            'gamification.js',
            'profile-manager.js',
            'usuari-public.js',
            'favorits-carret.js'
        ]

        for js_file in js_files:
            if (self.js_dir / js_file).exists():
                shutil.copy(self.js_dir / js_file, js_dest / js_file)
                print(f"   ✅ {js_file} copiat")

        # Copiar dades JSON
        data_src = self.root / 'data'
        data_dest = self.docs_dir / 'data'
        data_dest.mkdir(exist_ok=True)
        for json_file in data_src.glob('*.json'):
            shutil.copy(json_file, data_dest / json_file.name)
        print("   ✅ Dades JSON copiades")

        # Copiar assets (logo, etc.)
        assets_src = self.root / 'assets'
        assets_dest = self.docs_dir / 'assets'
        if assets_src.exists():
            if assets_dest.exists():
                shutil.rmtree(assets_dest)
            shutil.copytree(assets_src, assets_dest)
            print("   ✅ Assets copiats")

        # Copiar portades des de múltiples fonts
        portades_src = self.root / 'web' / 'assets' / 'portades'
        portades_dest = self.docs_dir / 'assets' / 'portades'
        portades_dest.mkdir(parents=True, exist_ok=True)

        count = 0

        # 1. Copiar des de web/assets/portades/
        if portades_src.exists():
            for portada in portades_src.glob('*.png'):
                shutil.copy(portada, portades_dest / portada.name)
                count += 1
            for portada in portades_src.glob('*.jpg'):
                shutil.copy(portada, portades_dest / portada.name)
                count += 1

        # 2. Copiar des de carpetes d'obres (obres/.../portada.png)
        # i també sincronitzar a web/assets/portades/ per futures builds
        for metadata_file in self.obres_dir.rglob('metadata.yml'):
            obra_dir = metadata_file.parent
            slug = f"{obra_dir.parent.name}-{obra_dir.name}"

            for ext in ['png', 'jpg']:
                portada_obra = obra_dir / f'portada.{ext}'
                if portada_obra.exists():
                    dest_name = f"{slug}-portada.{ext}"
                    dest_path = portades_dest / dest_name
                    web_path = portades_src / dest_name

                    # Copiar a docs/
                    if not dest_path.exists():
                        shutil.copy(portada_obra, dest_path)
                        count += 1

                    # Sincronitzar a web/assets/portades/ per futures builds
                    if not web_path.exists():
                        portades_src.mkdir(parents=True, exist_ok=True)
                        shutil.copy(portada_obra, web_path)
                    break

        print(f"   ✅ {count} portades copiades")

        # Copiar retrats d'autors
        autors_dest = self.docs_dir / 'assets' / 'autors'
        autors_dest.mkdir(parents=True, exist_ok=True)
        for obra_dir in self.obres_dir.rglob('*'):
            if obra_dir.is_dir():
                for retrat in obra_dir.glob('retrat_*.png'):
                    shutil.copy(retrat, autors_dest / retrat.name)
                for retrat in obra_dir.glob('retrat_*.jpg'):
                    shutil.copy(retrat, autors_dest / retrat.name)
        print("   ✅ Retrats d'autors copiats")

        print()

    def build_obres(self):
        """Construeix totes les obres."""
        print("📚 Construint obres...")
        print()

        if not self.obres_dir.exists():
            print(f"   ⚠️  Directori obres/ no existeix")
            return

        # Trobar totes les obres buscant metadata.yml recursivament
        for metadata_file in self.obres_dir.rglob('metadata.yml'):
            obra_dir = metadata_file.parent
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

        # Processar contingut (passant glossari per suportar marques [T])
        contingut_original = Markup(
            self.md.process_sections(loader.original, lang='grc', glossari=loader.glossari)
        )
        contingut_traduccio = Markup(
            self.md.process_sections(loader.traduccio, lang='ca', glossari=loader.glossari)
        )

        # Bibliografia
        bibliografia = Markup(self.md.convert(loader.bibliografia)) if loader.bibliografia else None

        # Preparar dades de l'obra
        obra_data = loader.metadata.get('obra', {})

        # Buscar portada (diferents patrons de nom)
        portada_url = None
        # Extreure nom autor i obra per a patrons alternatius
        autor_nom = obra_data.get('autor', '').split()[0].lower() if obra_data.get('autor') else obra_path.parent.name
        obra_nom = obra_path.name
        portada_patterns = [
            f"assets/portades/{slug}-portada.png",
            f"assets/portades/{obra_path.parent.name}-{obra_path.name}-portada.png",
            f"assets/portades/{obra_path.name}-portada.png",
            f"assets/portades/{autor_nom}-{obra_nom}-portada.png",
        ]
        for pattern in portada_patterns:
            if (self.docs_dir / pattern).exists():
                portada_url = pattern
                break

        # Extreure estadístiques
        estadistiques = loader.metadata.get('estadistiques', {})

        # Extreure font original
        metadata_original = loader.metadata.get('metadata_original', {})
        edicio_base = metadata_original.get('edicio_base', {})

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
            'estat': (loader.metadata.get('revisio') or obra_data.get('revisio') or {}).get('estat', 'esborrany'),
            'qualitat': self._extract_quality(loader),
            'data_revisio': (loader.metadata.get('revisio') or obra_data.get('revisio') or {}).get('data_revisio') or (loader.metadata.get('revisio') or obra_data.get('revisio') or {}).get('data', '1900-01-01'),
            'portada_url': portada_url,
            # Camps addicionals
            'seccions': loader.metadata.get('seccions'),
            'paraules_original': estadistiques.get('paraules_original'),
            'paraules_traduccio': estadistiques.get('paraules_traduccio'),
            'font_original': edicio_base.get('titol'),
            'font_url': edicio_base.get('url'),
            'contribuidors': loader.metadata.get('contribuidors', []),
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

    def _extract_quality(self, loader: ContentLoader) -> Optional[float]:
        """Extreu la qualitat de la traducció.

        Busca en ordre:
        1. metadata.yml (revisio.qualitat)
        2. Capçalera del traduccio.md (format V2: "Puntuació mitjana: X.X/10")
        """
        # Primer intentar metadata
        revisio = loader.metadata.get('revisio') or loader.metadata.get('obra', {}).get('revisio') or {}
        if revisio.get('qualitat'):
            return revisio['qualitat']

        # Fallback: extreure de capçalera traduccio.md (format V2)
        if loader.traduccio:
            # Buscar en les primeres 800 línies (capçalera)
            header = loader.traduccio[:2000]
            match = re.search(r'Puntuació mitjana:\s*([\d.]+)/10', header)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

        return None

    def build_index(self):
        """Construeix pàgina índex."""
        print()
        print("📑 Construint índex...")

        # Ordenar obres per data de revisió (més recent primer)
        self.obres.sort(key=lambda o: o.get('data_revisio', '1900-01-01'), reverse=True)

        # Estadístiques
        stats = {
            'total_obres': len(self.obres),
            'total_autors': len(set(o['autor'] for o in self.obres)),
            'total_paraules': sum(len((o.get('descripcio') or '').split()) * 100 for o in self.obres),
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

    def build_mecenatge(self):
        """Construeix les pàgines de mecenatge."""
        print()
        print("💝 Construint pàgines de mecenatge...")

        # Pàgines simples
        simple_pages = ['mecenatge', 'login', 'registre', 'pagament', 'proposta-traduccio', 'perfil', 'usuari']

        for page in simple_pages:
            template_file = f"{page}.html"
            if not (self.templates_dir / template_file).exists():
                print(f"   ⚠️  Template {template_file} no trobat")
                continue

            template = self.env.get_template(template_file)
            html = template.render(
                base_url='',
                site_url='https://biblioteca-arion.cat',
            )

            output_file = self.docs_dir / f"{page}.html"
            output_file.write_text(html, encoding='utf-8')
            print(f"   ✅ {page}.html generat")

        # Generar fitxes de micromecenatge per obres en crowdfunding
        self.build_micromecenatge_pages()

    def build_micromecenatge_pages(self):
        """Genera pàgines individuals per cada projecte de micromecenatge."""
        import json

        cataleg_file = self.root / 'data' / 'cataleg-traduccions.json'
        mecenatges_file = self.root / 'data' / 'mecenatges.json'

        if not cataleg_file.exists():
            print("   ⚠️  cataleg-traduccions.json no trobat")
            return

        with open(cataleg_file, 'r', encoding='utf-8') as f:
            cataleg = json.load(f)

        mecenatges = {}
        if mecenatges_file.exists():
            with open(mecenatges_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for m in data.get('mecenatges', []):
                    mecenatges[m['obra_id']] = m

        # Template de detall
        template_file = 'micromecenatge-detall.html'
        if not (self.templates_dir / template_file).exists():
            print(f"   ⚠️  Template {template_file} no trobat")
            return

        template = self.env.get_template(template_file)

        count = 0
        for obra in cataleg.get('obres', []):
            if obra.get('estat') == 'crowdfunding':
                mecenatge = mecenatges.get(obra['id'])
                recaptat = mecenatge.get('total', 0) if mecenatge else obra.get('recaptat', 0)
                objectiu = obra.get('cost_traduccio', 100)
                percentatge = min(round((recaptat / objectiu) * 100), 100)

                # Actualitzar obra amb valors de recaptat
                obra['recaptat'] = recaptat

                html = template.render(
                    base_url='',
                    site_url='https://biblioteca-arion.cat',
                    obra=obra,
                    mecenatge=mecenatge,
                    percentatge=percentatge,
                )

                output_file = self.docs_dir / f"micromecenatge-{obra['id']}.html"
                output_file.write_text(html, encoding='utf-8')
                count += 1

        print(f"   ✅ {count} fitxes de micromecenatge generades")


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
