"""Generador de la web d'Arion: carregador de contingut (metadata i obres)."""

import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from markupsafe import Markup

from .markdown import MarkdownProcessor


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

        # Buscar el primer marcador de capítol real (## Pròleg, ## I, ## Llibre Primer, etc.)
        # Això preserva pròlegs i prefacis com a contingut real
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('## '):
                chapter_title = stripped[3:].strip()
                if self._is_chapter_marker(chapter_title):
                    return '\n'.join(lines[i:]).strip()

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
        # Pròlegs, prefacis i seccions preliminars
        prefacis = ['pròleg', 'prefaci', 'introducció', 'avant-propos',
                     'vorrede', 'vorwort', 'einleitung', 'preface', 'prologue',
                     'prooemium', 'prolegomena', 'prefazione', 'préface']
        if text.lower() in prefacis:
            return True
        # Marcadors de llibre/part (ex: "Llibre Primer", "Erstes Buch", "Part I")
        if re.match(r'^(Llibre|Buch|Book|Part|Livre|Libro)\s+', text, re.IGNORECASE):
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
                # Referències - processar markdown per cursives, etc.
                if line.startswith('> Vegeu:'):
                    refs_text = line[9:].strip()
                    # Convertir markdown inline (cursives, negreta)
                    refs_html = md.convert(refs_text)
                    # Eliminar <p> tags que markdown afegeix
                    refs_html = re.sub(r'^<p>(.*)</p>$', r'\1', refs_html.strip())
                    current_note['refs'] = Markup(refs_html)
                else:
                    current_note['lines'].append(line)

        # Última nota
        if current_note:
            current_note['contingut'] = Markup(md.convert('\n'.join(current_note['lines'])))
            del current_note['lines']
            notes.append(current_note)

        return notes
