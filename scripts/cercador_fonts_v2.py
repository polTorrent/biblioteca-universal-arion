#!/usr/bin/env python3
"""Cercador de Fonts V2 — Sistema per capes per obtenir textos de domini públic.

Arquitectura de 3 capes:
  Capa 1: APIs oficials (Gutenberg, Wikisource, Internet Archive, Aozora)
  Capa 2: Descàrrega HTTP directa (curl/wget amb headers normals)
  Capa 3: Integració worker/heartbeat per retry intel·ligent

Ús directe:
    python3 scripts/cercador_fonts_v2.py "Sèneca" "De Brevitate Vitae" "llatí"

Ús des del pipeline:
    from scripts.cercador_fonts_v2 import CercadorFontsV2
    cercador = CercadorFontsV2()
    resultat = cercador.obtenir_text("Sèneca", "De Brevitate Vitae", "llatí")
"""

import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

@dataclass
class FontTrobada:
    """Resultat d'una font localitzada."""
    nom_font: str          # "gutenberg", "wikisource", "internet_archive", etc.
    url: str               # URL directa al text
    titol: str
    autor: str
    llengua: str
    text: str | None = None  # Text complet si ja descarregat
    qualitat: int = 5        # 1-10
    format: str = "txt"      # txt, html, xml
    notes: str = ""


@dataclass
class ResultatCerca:
    """Resultat complet de la cerca multi-capa."""
    trobat: bool = False
    text: str | None = None
    font: FontTrobada | None = None
    fonts_provades: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    temps_total: float = 0.0


# ═══════════════════════════════════════════════════════════════
# MAPA D'AUTORS I OBRES → FONTS CONEGUDES
# ═══════════════════════════════════════════════════════════════

# IDs de Gutenberg per obres comunes (evita cercar cada cop)
GUTENBERG_IDS: dict[str, dict[str, int]] = {
    "plato": {
        "apologia": 1656,       # Apology (anglès, però útil)
        "criton": 1657,
        "republic": 1497,
        "phaedo": 1658,
    },
    "seneca": {
        "epistulae": 2091,
    },
    "marcus aurelius": {
        "meditations": 2680,
    },
    "epictetus": {
        "enchiridion": 45109,
        "discourses": 10661,
    },
    "kafka": {
        "metamorphosis": 5200,
        "trial": 7849,
    },
    "poe": {
        "tales": 2147,
        "raven": 17192,
    },
    "melville": {
        "bartleby": 11231,
    },
    "shakespeare": {
        "hamlet": 1524,
        "sonnets": 1041,
    },
    "dostoevsky": {
        "notes from underground": 600,
        "crime and punishment": 2554,
    },
    "chekhov": {
        "ward no 6": 13415,
    },
    "montaigne": {
        "essays": 3600,
    },
    "schopenhauer": {
        "fourfold root": 50966,
    },
    "sade": {
        "justine": 38070,  # Si existeix a Gutenberg
    },
}

# URLs directes per a fonts llatines/gregues
LATIN_LIBRARY_URLS: dict[str, dict[str, str]] = {
    "seneca": {
        "de-brevitate-vitae": "https://www.thelatinlibrary.com/sen/sen.brev.shtml",
        "epistulae": "https://www.thelatinlibrary.com/sen/seneca.ep1.shtml",
        "de-ira": "https://www.thelatinlibrary.com/sen/sen.ira1.shtml",
    },
    "marcus aurelius": {
        "meditationes": "https://www.thelatinlibrary.com/marcusaurelius.html",
    },
    "epictetus": {
        "enchiridion": "https://www.thelatinlibrary.com/epictetus.html",
    },
}

PERSEUS_URLS: dict[str, dict[str, str]] = {
    "plato": {
        "apologia": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0170",
        "criton": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0170%3Atext%3DCrito",
        "republic": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0168",
        "phaedo": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0170%3Atext%3DPhaedo",
    },
    "epictetus": {
        "enchiridion": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0235",
        "discourses": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0236",
    },
    "marcus aurelius": {
        "meditations": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A2008.01.0641",
    },
    "seneca": {
        "de-brevitate-vitae": "https://www.thelatinlibrary.com/sen/sen.brev.shtml",
        "epistulae": "https://www.thelatinlibrary.com/sen/seneca.ep1.shtml",
    },
    "sophocles": {
        "oedipus": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0191",
        "antigone": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0185",
    },
    "homer": {
        "iliad": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0133",
        "odyssey": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0135",
    },
    "heraclitus": {
        "fragments": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0248",
    },
}

WIKISOURCE_PAGES: dict[str, dict[str, tuple[str, str]]] = {
    # autor: {obra: (codi_llengua_wikisource, títol_pàgina)}
    "seneca": {
        "de-brevitate-vitae": ("la", "De Brevitate Vitae"),
        "epistulae": ("la", "Epistulae morales ad Lucilium"),
    },
    "plato": {
        "apologia": ("el", "Ἀπολογία Σωκράτους"),
    },
    "epictetus": {
        "enchiridion": ("el", "Ἐγχειρίδιον"),
    },
    "marc aureli": {
        "meditacions": ("el", "Τὰ εἰς ἑαυτόν"),
    },
    "kafka": {
        "die-verwandlung": ("de", "Die Verwandlung"),
        "la-transformacio": ("de", "Die Verwandlung"),
    },
    "montaigne": {
        "essais": ("fr", "Essais"),
        "de-l-amistat": ("fr", "Essais/Livre I/Chapitre XXVIII"),
    },
    "akutagawa": {
        "rashomon": ("ja", "羅生門"),
        "biombo-infern": ("ja", "地獄変"),
    },
}


# ═══════════════════════════════════════════════════════════════
# CAPA 1: APIs OFICIALS
# ═══════════════════════════════════════════════════════════════

class GutenbergAPI:
    """Cerca i descàrrega de Project Gutenberg via API."""

    BASE_URL = "https://gutendex.com/books"
    MIRROR = "https://www.gutenberg.org"

    @staticmethod
    def cercar(autor: str, titol: str) -> list[dict]:
        """Cerca llibres a Gutenberg per autor i/o títol."""
        params = {}
        if autor:
            params["author"] = autor
        if titol:
            params["search"] = titol

        url = f"{GutenbergAPI.BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", [])
        except Exception:
            return []

    @staticmethod
    def descarregar_text(book_id: int) -> str | None:
        """Descarrega el text complet d'un llibre per ID."""
        # Provar formats en ordre de preferència
        formats_urls = [
            f"{GutenbergAPI.MIRROR}/cache/epub/{book_id}/pg{book_id}.txt",
            f"{GutenbergAPI.MIRROR}/files/{book_id}/{book_id}-0.txt",
            f"{GutenbergAPI.MIRROR}/files/{book_id}/{book_id}.txt",
        ]

        for url in formats_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                    if len(text) > 500:
                        # Netejar capçalera/peu de Gutenberg
                        text = _netejar_gutenberg(text)
                        return text
            except Exception:
                continue
        return None

    @staticmethod
    def obtenir_per_id(book_id: int) -> FontTrobada | None:
        """Obté un text directament per ID de Gutenberg."""
        text = GutenbergAPI.descarregar_text(book_id)
        if text:
            return FontTrobada(
                nom_font="gutenberg",
                url=f"{GutenbergAPI.MIRROR}/ebooks/{book_id}",
                titol=f"Gutenberg #{book_id}",
                autor="",
                llengua="",
                text=text,
                qualitat=7,
                format="txt",
                notes=f"Descarregat directament de Project Gutenberg (ID: {book_id})",
            )
        return None


class WikisourceAPI:
    """Cerca i descàrrega de Wikisource via MediaWiki API."""

    @staticmethod
    def obtenir_text(codi_llengua: str, titol_pagina: str) -> str | None:
        """Obté el text d'una pàgina de Wikisource."""
        # API de MediaWiki per obtenir el contingut en text pla
        base = f"https://{codi_llengua}.wikisource.org/w/api.php"
        params = {
            "action": "query",
            "titles": titol_pagina,
            "prop": "extracts",
            "explaintext": "1",  # Text pla, sense HTML
            "format": "json",
        }
        url = f"{base}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if page_id == "-1":
                        return None  # Pàgina no trobada
                    extract = page_data.get("extract", "")
                    if len(extract) > 200:
                        return extract
        except Exception:
            pass

        # Fallback: obtenir HTML i netejar
        return WikisourceAPI._obtenir_html_net(codi_llengua, titol_pagina)

    @staticmethod
    def _obtenir_html_net(codi_llengua: str, titol_pagina: str) -> str | None:
        """Fallback: descarrega HTML i extreu text."""
        base = f"https://{codi_llengua}.wikisource.org/w/api.php"
        params = {
            "action": "parse",
            "page": titol_pagina,
            "prop": "text",
            "format": "json",
        }
        url = f"{base}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                html = data.get("parse", {}).get("text", {}).get("*", "")
                if html:
                    return _html_a_text(html)
        except Exception:
            pass
        return None

    @staticmethod
    def cercar(codi_llengua: str, terme: str) -> list[dict]:
        """Cerca pàgines a Wikisource."""
        base = f"https://{codi_llengua}.wikisource.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": terme,
            "srnamespace": "0",
            "srlimit": "10",
            "format": "json",
        }
        url = f"{base}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("query", {}).get("search", [])
        except Exception:
            return []


class InternetArchiveAPI:
    """Cerca i descàrrega d'Internet Archive."""

    @staticmethod
    def cercar(autor: str, titol: str, llengua: str = "") -> list[dict]:
        """Cerca textos a Internet Archive."""
        query_parts = []
        if autor:
            query_parts.append(f"creator:({autor})")
        if titol:
            query_parts.append(f"title:({titol})")
        query_parts.append("mediatype:(texts)")

        query = " AND ".join(query_parts)
        params = {
            "q": query,
            "fl[]": ["identifier", "title", "creator", "language", "description"],
            "rows": "10",
            "output": "json",
        }
        url = f"https://archive.org/advancedsearch.php?{urllib.parse.urlencode(params, doseq=True)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", {}).get("docs", [])
        except Exception:
            return []

    @staticmethod
    def descarregar_text(identifier: str) -> str | None:
        """Intenta descarregar el text d'un element d'Internet Archive."""
        # Primer, obtenir llista de fitxers
        meta_url = f"https://archive.org/metadata/{identifier}/files"
        try:
            req = urllib.request.Request(meta_url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                files = data.get("result", [])

            # Buscar fitxer .txt preferentment
            txt_files = [f for f in files if f.get("name", "").endswith(".txt")]
            if not txt_files:
                txt_files = [
                    f for f in files
                    if f.get("name", "").endswith((".htm", ".html"))
                ]

            if txt_files:
                fname = txt_files[0]["name"]
                dl_url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(fname)}"
                req2 = urllib.request.Request(dl_url, headers={"User-Agent": "BibliotecaArion/1.0"})
                with urllib.request.urlopen(req2, timeout=30) as resp2:
                    text = resp2.read().decode("utf-8", errors="replace")
                    if len(text) > 500:
                        return text
        except Exception:
            pass
        return None


class AozoraBunkoAPI:
    """Cerca i descàrrega d'Aozora Bunko (textos japonesos)."""

    @staticmethod
    def cercar(autor_jp: str = "", titol_jp: str = "") -> list[dict]:
        """Cerca a l'índex CSV d'Aozora Bunko."""
        # Aozora té un CSV públic amb totes les obres
        # Per simplicitat, usem la cerca directa per URL
        return []

    @staticmethod
    def descarregar_text(url: str) -> str | None:
        """Descarrega i decodifica text d'Aozora (Shift_JIS → UTF-8)."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Aozora usa Shift_JIS
                for encoding in ["shift_jis", "euc-jp", "utf-8"]:
                    try:
                        return raw.decode(encoding)
                    except UnicodeDecodeError:
                        continue
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════
# CAPA 2: DESCÀRREGA HTTP DIRECTA
# ═══════════════════════════════════════════════════════════════

class DescarregadorHTTP:
    """Descàrrega directa amb headers normals per evitar bloquejos."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "ca,en-US;q=0.7,en;q=0.3",
    }

    @staticmethod
    def descarregar(url: str, timeout: int = 30) -> str | None:
        """Descarrega una URL amb headers de navegador normal."""
        try:
            req = urllib.request.Request(url, headers=DescarregadorHTTP.HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                encoding = "utf-8"
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].strip()
                raw = resp.read()
                text = raw.decode(encoding, errors="replace")
                return text
        except Exception:
            return None

    @staticmethod
    def descarregar_amb_curl(url: str, timeout: int = 30) -> str | None:
        """Fallback: usa curl del sistema (més robust contra bloquejos)."""
        try:
            result = subprocess.run(
                [
                    "curl", "-sL",
                    "--max-time", str(timeout),
                    "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
                          "Gecko/20100101 Firefox/120.0",
                    "-H", "Accept: text/html,text/plain;q=0.9",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            if result.returncode == 0 and len(result.stdout) > 200:
                return result.stdout
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════
# UTILITATS DE NETEJA
# ═══════════════════════════════════════════════════════════════

def _netejar_gutenberg(text: str) -> str:
    """Elimina capçalera i peu de llicència de Gutenberg."""
    # Trobar inici del text real
    markers_start = [
        "*** START OF THE PROJECT GUTENBERG",
        "*** START OF THIS PROJECT GUTENBERG",
        "***START OF THE PROJECT GUTENBERG",
    ]
    markers_end = [
        "*** END OF THE PROJECT GUTENBERG",
        "*** END OF THIS PROJECT GUTENBERG",
        "***END OF THE PROJECT GUTENBERG",
        "End of the Project Gutenberg",
        "End of Project Gutenberg",
    ]

    for marker in markers_start:
        idx = text.find(marker)
        if idx != -1:
            newline = text.find("\n", idx)
            if newline != -1:
                text = text[newline + 1:]
            break
    else:
        # Fallback: eliminar capçalera típica ("Produced by...", etc.)
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines):
            stripped = line.strip().upper()
            if any(
                x in stripped
                for x in ["PRODUCED BY", "DISTRIBUTED PROOFREADING", "HTTP://", "TRANSCRIBER"]
            ):
                start = i + 1
                continue
            if stripped and start > 0:
                break
        if start > 0:
            text = "\n".join(lines[start:])

    for marker in markers_end:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            break

    return text.strip()


def _html_a_text(html: str) -> str:
    """Converteix HTML a text pla (bàsic, sense dependències)."""
    # Eliminar tags
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<h[1-6][^>]*>", "\n\n## ", text)
    text = re.sub(r"</h[1-6]>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    # Entitats HTML
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    # Netejar residus Perseus
    for noise in ["All Search Options", "view abbreviations", "Hide browse bar",
                   "Your current position", "Click anywhere", "Collections/Texts",
                   "Perseus Catalog", "Open Source", "Home", "Research", "Grants",
                   "About", "Help", '(Agamemnon', "denarius"]:
        text = text.replace(noise, "")
    # Eliminar línies curtes de navegació (< 30 chars i sense lletres gregues/llatines)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        # Mantenir línies amb contingut real
        if len(stripped) > 30 or any(ord(c) > 880 for c in stripped):
            cleaned.append(line)
        elif any(c.isalpha() for c in stripped) and len(stripped) > 5:
            cleaned.append(line)
    text = "\n".join(cleaned)
    # Netejar espais
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Netejar residus Wikisource
    text = re.sub(r"\[recensere\]", "", text)
    text = re.sub(r"\[modifica\]", "", text)
    text = text.replace("&#160;", " ")
    text = text.replace("&#8212;", "—")
    text = text.replace("&#8217;", "'")
    text = re.sub(r"&#\d+;", "", text)
    # Eliminar línia EPUB/MOBI/PDF/RTF/TXT
    text = re.sub(r"^.*EPUB.*MOBI.*PDF.*TXT.*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _normalitzar_nom(nom: str) -> str:
    """Normalitza un nom per a comparació (minúscules, sense accents simples)."""
    return nom.lower().replace("-", " ").replace("_", " ").strip()


def _trobar_obra_mapa(autor: str, obra: str, mapa: dict) -> Any | None:
    """Cerca flexible dins un mapa autor→obra."""
    autor_norm = _normalitzar_nom(autor)
    obra_norm = _normalitzar_nom(obra)

    for key_autor, obres in mapa.items():
        if key_autor in autor_norm or autor_norm in key_autor:
            for key_obra, valor in obres.items():
                if key_obra in obra_norm or obra_norm in key_obra:
                    return valor
    return None


# ═══════════════════════════════════════════════════════════════
# CERCADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════

class CercadorFontsV2:
    """Cercador de fonts multi-capa per a textos de domini públic."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[CercadorV2] {msg}")

    def obtenir_text(
        self,
        autor: str,
        titol: str,
        llengua: str = "llatí",
        obra_dir: Path | None = None,
    ) -> ResultatCerca:
        """Cerca multi-capa per obtenir un text de domini públic.

        Ordre de cerca:
        1. Mapa intern (URLs conegudes)
        2. Gutenberg API
        3. Wikisource API
        4. Internet Archive API
        5. Descàrrega HTTP directa (Latin Library, Perseus, etc.)

        Args:
            autor: Nom de l'autor.
            titol: Títol de l'obra.
            llengua: Llengua original del text.
            obra_dir: Directori de l'obra (per guardar original.md).

        Returns:
            ResultatCerca amb el text i metadades.
        """
        inici = time.time()
        resultat = ResultatCerca()

        self.log(f"Cercant: «{titol}» de {autor} ({llengua})")

        # ── Capa 0: Perseus (prioritat màxima per grec/llatí) ──
        if llengua.lower() in ["grec", "llatí", "greek", "latin"]:
            perseus_url = _trobar_obra_mapa(autor, titol, PERSEUS_URLS)
            if perseus_url:
                self.log(f"  🏛️ Perseus: {perseus_url[:60]}...")
                resultat.fonts_provades.append(f"perseus:{perseus_url[:40]}")
                html = DescarregadorHTTP.descarregar(perseus_url)
                if html and len(html) > 2000:
                    text = _html_a_text(html)
                    if text and len(text) > 500:
                        self.log(f"  ✅ Perseus: {len(text)} caràcters")
                        resultat.trobat = True
                        resultat.text = text
                        resultat.font = FontTrobada(
                            nom_font="perseus",
                            url=perseus_url,
                            titol=titol, autor=autor, llengua=llengua,
                            text=text, qualitat=9, format="txt",
                            notes="Text original de Perseus Digital Library",
                        )
                        resultat.temps_total = time.time() - inici
                        self._guardar_si_cal(resultat, obra_dir)
                        return resultat
                    else:
                        mida = len(text) if text else 0
                        resultat.errors.append(
                            f"Perseus: HTML rebut però text extret massa curt ({mida})"
                        )
                else:
                    resultat.errors.append("Perseus: descàrrega fallida o resposta curta")

        # ── Capa 1a: Wikisource mapa intern (prioritat per originals no-anglesos) ──
        if llengua.lower() not in ["anglès", "english"]:
            ws_info = _trobar_obra_mapa(autor, titol, WIKISOURCE_PAGES)
            if ws_info:
                ws_lang, ws_page = ws_info
                if ws_lang != "en":
                    self.log(f"  📜 Wikisource (original): {ws_lang}.wikisource.org/{ws_page}")
                    resultat.fonts_provades.append(f"wikisource_map:{ws_lang}/{ws_page}")
                    text = WikisourceAPI.obtenir_text(ws_lang, ws_page)
                    if text and len(text) > 500:
                        self.log(f"  ✅ Wikisource original: {len(text)} caràcters")
                        resultat.trobat = True
                        resultat.text = text
                        resultat.font = FontTrobada(
                            nom_font="wikisource",
                            url=f"https://{ws_lang}.wikisource.org/wiki/{urllib.parse.quote(ws_page)}",
                            titol=titol, autor=autor, llengua=llengua,
                            text=text, qualitat=9, format="txt",
                            notes="Text original via mapa intern",
                        )
                        resultat.temps_total = time.time() - inici
                        self._guardar_si_cal(resultat, obra_dir)
                        return resultat

        # ── Capa 1b: Mapa intern Gutenberg ──
        guten_id = _trobar_obra_mapa(autor, titol, GUTENBERG_IDS)
        if guten_id:
            self.log(f"  📖 Gutenberg ID conegut: {guten_id}")
            resultat.fonts_provades.append(f"gutenberg_id:{guten_id}")
            font = GutenbergAPI.obtenir_per_id(guten_id)
            if font and font.text and len(font.text) > 500:
                self.log(f"  ✅ Gutenberg: {len(font.text)} caràcters")
                resultat.trobat = True
                resultat.text = font.text
                resultat.font = font
                resultat.temps_total = time.time() - inici
                self._guardar_si_cal(resultat, obra_dir)
                return resultat
            else:
                resultat.errors.append(f"Gutenberg ID {guten_id}: text buit o massa curt")

        # ── Capa 1b: Wikisource (mapa intern) ──
        ws_info = _trobar_obra_mapa(autor, titol, WIKISOURCE_PAGES)
        if ws_info:
            ws_lang, ws_page = ws_info
            self.log(f"  📜 Wikisource: {ws_lang}.wikisource.org/{ws_page}")
            resultat.fonts_provades.append(f"wikisource:{ws_lang}/{ws_page}")
            text = WikisourceAPI.obtenir_text(ws_lang, ws_page)
            if text and len(text) > 500:
                self.log(f"  ✅ Wikisource: {len(text)} caràcters")
                resultat.trobat = True
                resultat.text = text
                resultat.font = FontTrobada(
                    nom_font="wikisource",
                    url=f"https://{ws_lang}.wikisource.org/wiki/{urllib.parse.quote(ws_page)}",
                    titol=titol, autor=autor, llengua=llengua,
                    text=text, qualitat=8, format="txt",
                )
                resultat.temps_total = time.time() - inici
                self._guardar_si_cal(resultat, obra_dir)
                return resultat
            else:
                resultat.errors.append(f"Wikisource {ws_lang}/{ws_page}: text buit o curt")

        # ── Capa 1c: Gutenberg cerca dinàmica ──
        # Per llengües no-angleses, prioritzar Wikisource (text original)
        # Gutenberg sovint té traduccions angleses, no originals
        if llengua.lower() not in ["anglès", "english"]:
            ws_langs = self._llengua_a_wikisource(llengua)
            for ws_lang in ws_langs:
                if ws_lang == "en":
                    continue  # Saltar anglès per a cerca d'originals
                self.log(f"  🔍 Cercant original a Wikisource ({ws_lang})...")
                resultat.fonts_provades.append(f"wikisource_original:{ws_lang}")
                resultats_ws = WikisourceAPI.cercar(ws_lang, titol)
                for hit in resultats_ws[:3]:
                    ws_title = hit.get("title", "")
                    self.log(f"  📜 Provant: {ws_title}")
                    text = WikisourceAPI.obtenir_text(ws_lang, ws_title)
                    if text and len(text) > 500:
                        self.log(f"  ✅ Wikisource original: {len(text)} caràcters")
                        resultat.trobat = True
                        resultat.text = text
                        resultat.font = FontTrobada(
                            nom_font="wikisource",
                            url=f"https://{ws_lang}.wikisource.org/wiki/{urllib.parse.quote(ws_title)}",
                            titol=ws_title, autor=autor, llengua=llengua,
                            text=text, qualitat=9, format="txt",
                            notes="Text original (no traducció)",
                        )
                        resultat.temps_total = time.time() - inici
                        self._guardar_si_cal(resultat, obra_dir)
                        return resultat

        self.log("  🔍 Cercant a Gutenberg API...")
        resultat.fonts_provades.append("gutenberg_search")
        resultats_guten = GutenbergAPI.cercar(autor, titol)
        for book in resultats_guten[:3]:
            book_id = book.get("id")
            if not book_id:
                continue
            self.log(f"  📖 Provant Gutenberg #{book_id}: {book.get('title', '?')}")
            text = GutenbergAPI.descarregar_text(book_id)
            if text and len(text) > 500:
                self.log(f"  ✅ Gutenberg #{book_id}: {len(text)} caràcters")
                resultat.trobat = True
                resultat.text = text
                resultat.font = FontTrobada(
                    nom_font="gutenberg",
                    url=f"https://www.gutenberg.org/ebooks/{book_id}",
                    titol=book.get("title", titol),
                    autor=autor, llengua=llengua,
                    text=text, qualitat=7, format="txt",
                    notes=f"Trobat via cerca: {book.get('title')}",
                )
                resultat.temps_total = time.time() - inici
                self._guardar_si_cal(resultat, obra_dir)
                return resultat

        # ── Capa 1d: Wikisource cerca dinàmica ──
        ws_langs = self._llengua_a_wikisource(llengua)
        for ws_lang in ws_langs:
            self.log(f"  🔍 Cercant a Wikisource ({ws_lang})...")
            resultat.fonts_provades.append(f"wikisource_search:{ws_lang}")
            resultats_ws = WikisourceAPI.cercar(ws_lang, f"{autor} {titol}")
            for hit in resultats_ws[:3]:
                ws_title = hit.get("title", "")
                self.log(f"  📜 Provant: {ws_title}")
                text = WikisourceAPI.obtenir_text(ws_lang, ws_title)
                if text and len(text) > 500:
                    self.log(f"  ✅ Wikisource: {len(text)} caràcters")
                    resultat.trobat = True
                    resultat.text = text
                    resultat.font = FontTrobada(
                        nom_font="wikisource",
                        url=f"https://{ws_lang}.wikisource.org/wiki/{urllib.parse.quote(ws_title)}",
                        titol=ws_title, autor=autor, llengua=llengua,
                        text=text, qualitat=8, format="txt",
                    )
                    resultat.temps_total = time.time() - inici
                    self._guardar_si_cal(resultat, obra_dir)
                    return resultat

        # ── Capa 1e: Internet Archive ──
        self.log("  🔍 Cercant a Internet Archive...")
        resultat.fonts_provades.append("internet_archive")
        resultats_ia = InternetArchiveAPI.cercar(autor, titol, llengua)
        for doc in resultats_ia[:3]:
            ia_id = doc.get("identifier")
            if not ia_id:
                continue
            self.log(f"  📦 Provant IA: {ia_id}")
            text = InternetArchiveAPI.descarregar_text(ia_id)
            if text and len(text) > 500:
                self.log(f"  ✅ Internet Archive: {len(text)} caràcters")
                resultat.trobat = True
                resultat.text = text
                resultat.font = FontTrobada(
                    nom_font="internet_archive",
                    url=f"https://archive.org/details/{ia_id}",
                    titol=doc.get("title", titol),
                    autor=autor, llengua=llengua,
                    text=text, qualitat=6, format="txt",
                )
                resultat.temps_total = time.time() - inici
                self._guardar_si_cal(resultat, obra_dir)
                return resultat

        # ── Capa 2: Descàrrega directa d'URLs conegudes ──
        urls_directes = self._urls_directes(autor, titol)
        for nom, url in urls_directes:
            self.log(f"  🌐 Descarregant: {nom} ({url[:60]}...)")
            resultat.fonts_provades.append(f"http:{nom}")
            text = DescarregadorHTTP.descarregar(url)
            if not text or len(text) < 500:
                text = DescarregadorHTTP.descarregar_amb_curl(url)
            if text and len(text) > 500:
                # Si és HTML, convertir a text
                if "<html" in text.lower() or "<body" in text.lower():
                    text = _html_a_text(text)
                if len(text) > 500:
                    self.log(f"  ✅ {nom}: {len(text)} caràcters")
                    resultat.trobat = True
                    resultat.text = text
                    resultat.font = FontTrobada(
                        nom_font=nom, url=url,
                        titol=titol, autor=autor, llengua=llengua,
                        text=text, qualitat=6, format="txt",
                    )
                    resultat.temps_total = time.time() - inici
                    self._guardar_si_cal(resultat, obra_dir)
                    return resultat
            resultat.errors.append(f"{nom}: descàrrega fallida o text curt")

        # ── Cap font trobada ──
        resultat.temps_total = time.time() - inici
        self.log(f"  ❌ Cap font trobada ({resultat.temps_total:.1f}s)")
        self.log(f"     Provades: {', '.join(resultat.fonts_provades)}")
        return resultat

    def _urls_directes(self, autor: str, titol: str) -> list[tuple[str, str]]:
        """Retorna llista de (nom_font, url) per descàrrega directa."""
        urls = []

        # Latin Library
        ll_url = _trobar_obra_mapa(autor, titol, LATIN_LIBRARY_URLS)
        if ll_url:
            urls.append(("latin_library", ll_url))

        # Perseus
        perseus_url = _trobar_obra_mapa(autor, titol, PERSEUS_URLS)
        if perseus_url:
            urls.append(("perseus", perseus_url))

        return urls

    def _llengua_a_wikisource(self, llengua: str) -> list[str]:
        """Retorna codis de llengua per Wikisource."""
        mapa = {
            "llatí": ["la", "en"],
            "grec": ["el", "grc", "en"],
            "anglès": ["en"],
            "alemany": ["de"],
            "francès": ["fr"],
            "italià": ["it"],
            "japonès": ["ja"],
            "xinès": ["zh"],
            "rus": ["ru"],
            "sànscrit": ["sa", "en"],
        }
        return mapa.get(llengua.lower(), ["en"])

    def _guardar_si_cal(self, resultat: ResultatCerca, obra_dir: Path | None) -> None:
        """Guarda el text a original.md si tenim obra_dir."""
        if not obra_dir or not resultat.text or not resultat.font:
            return

        obra_dir = Path(obra_dir)
        obra_dir.mkdir(parents=True, exist_ok=True)

        original_path = obra_dir / "original.md"
        capçalera = f"""# {resultat.font.titol}
**Autor:** {resultat.font.autor}
**Font:** [{resultat.font.nom_font}]({resultat.font.url})
**Llengua:** {resultat.font.llengua}

---

"""
        original_path.write_text(capçalera + resultat.text, encoding="utf-8")
        self.log(f"  💾 Guardat a {original_path}")

        # Guardar info de font
        font_info = {
            "font": resultat.font.nom_font,
            "url": resultat.font.url,
            "qualitat": resultat.font.qualitat,
            "data_descarrega": time.strftime("%Y-%m-%d %H:%M:%S"),
            "caracters": len(resultat.text),
        }
        font_path = obra_dir / ".font_info.json"
        font_path.write_text(json.dumps(font_info, indent=2, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    """Execució directa des de terminal."""
    if len(sys.argv) < 3:
        print("Ús: python3 cercador_fonts_v2.py <autor> <títol> [llengua] [obra_dir]")
        print('Ex:  python3 cercador_fonts_v2.py "Sèneca" "De Brevitate Vitae" "llatí"')
        sys.exit(1)

    autor = sys.argv[1]
    titol = sys.argv[2]
    llengua = sys.argv[3] if len(sys.argv) > 3 else "llatí"
    obra_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    cercador = CercadorFontsV2(verbose=True)
    resultat = cercador.obtenir_text(autor, titol, llengua, obra_dir)

    print("\n" + "=" * 60)
    if resultat.trobat:
        print(f"✅ TROBAT: {resultat.font.nom_font}")
        print(f"   URL: {resultat.font.url}")
        print(f"   Caràcters: {len(resultat.text)}")
        print(f"   Temps: {resultat.temps_total:.1f}s")
        print("\nPrimers 500 caràcters:")
        print("-" * 40)
        print(resultat.text[:500])
    else:
        print(f"❌ No trobat")
        print(f"   Fonts provades: {', '.join(resultat.fonts_provades)}")
        print(f"   Errors: {'; '.join(resultat.errors)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
