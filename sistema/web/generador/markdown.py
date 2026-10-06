"""Generador de la web d'Arion: processador de Markdown a HTML."""

import re

import markdown
from markdown.extensions.footnotes import FootnoteExtension


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
            trans = (terme.get('transliteracio') or '').lower()
            trad = (terme.get('traduccio') or '').lower()
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
        """Converteix [^n] o [n] a referències de notes.

        Accepta dos formats:
        - [^1] format estàndard markdown footnotes
        - [1] format simplificat usat per alguns traductors
        """
        def note_replacer(match):
            note_id = match.group(1)
            return f'<sup><a href="#nota-{note_id}" class="note-ref" id="ref-{note_id}">[{note_id}]</a></sup>'

        # Acceptar tant [^1] com [1] (però no [text] genèric - només números)
        return re.sub(r'\[\^?(\d+)\]', note_replacer, text)
