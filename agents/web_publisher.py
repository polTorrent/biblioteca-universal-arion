"""Agent per publicar traduccions a la web (GitHub Pages).

Genera pàgines HTML a partir de les traduccions i actualitza l'índex.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

try:
    from agents.base_agent import AgentConfig, BaseAgent
    from agents.portadista import AgentPortadista, PortadistaConfig
except ImportError:
    from base_agent import AgentConfig, BaseAgent
    from portadista import AgentPortadista, PortadistaConfig


class ObraMetadata(BaseModel):
    """Metadades d'una obra per a publicació web."""

    # Identificadors
    slug: str = ""
    autor_dir: str = ""
    obra_dir: str = ""

    # Informació bàsica
    titol: str
    titol_original: str | None = None
    autor: str
    autor_original: str | None = None
    traductor: str = "Biblioteca Arion"

    # Dates i idioma
    any_original: str | None = None
    any_traduccio: int = Field(default_factory=lambda: datetime.now().year)
    llengua_original: str = "grec"

    # Descripció i estat
    descripcio: str = ""
    estat: Literal["esborrany", "revisat", "publicat"] = "esborrany"
    qualitat: float | None = None

    # Estadístiques
    paraules_original: int = 0
    paraules_traduccio: int = 0

    # Gènere per portada
    genere: str = "FIL"

    # Ruta portada
    portada_url: str | None = None


class WebPublisherConfig(BaseModel):
    """Configuració del WebPublisher."""

    # Directoris
    obres_dir: Path = Path("obres")
    templates_dir: Path = Path("web/templates")
    output_dir: Path = Path("docs")
    assets_dir: Path = Path("docs/assets")

    # Opcions
    generar_portades: bool = True
    base_url: str = ""
    site_url: str = "https://biblioteca-arion.github.io/biblioteca-universal-arion/"
    editorial: str = "Biblioteca Arion"

    # Markdown extensions
    md_extensions: list[str] = Field(default_factory=lambda: [
        "tables",
        "fenced_code",
        "footnotes",
        "attr_list",
        "def_list",
        "toc",
    ])


class WebPublisher(BaseAgent):
    """Agent que publica traduccions a la web."""

    agent_name = "WebPublisher"

    def __init__(
        self,
        config: AgentConfig | None = None,
        publisher_config: WebPublisherConfig | None = None,
    ) -> None:
        super().__init__(config)
        self.publisher_config = publisher_config or WebPublisherConfig()

        # Inicialitzar Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.publisher_config.templates_dir)),
            autoescape=True,
        )

        # Inicialitzar Markdown
        self.md = markdown.Markdown(
            extensions=self.publisher_config.md_extensions,
            output_format="html5",
        )

        # Portadista (lazy init)
        self._portadista: AgentPortadista | None = None

    @property
    def system_prompt(self) -> str:
        return "Agent de publicació web per a la Biblioteca Arion."

    @property
    def portadista(self) -> AgentPortadista | None:
        """Lazy initialization del portadista."""
        if self._portadista is None and self.publisher_config.generar_portades:
            try:
                self._portadista = AgentPortadista()
            except Exception as e:
                self.log_warning(f"No s'ha pogut inicialitzar el portadista: {e}")
        return self._portadista

    def _llegir_metadata(self, obra_path: Path) -> ObraMetadata | None:
        """Llegeix i parseja el metadata.yml d'una obra."""
        metadata_file = obra_path / "metadata.yml"
        if not metadata_file.exists():
            self.log_warning(f"No s'ha trobat metadata.yml a {obra_path}")
            return None

        try:
            with open(metadata_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Extreure dades de l'estructura YAML
            obra_data = data.get("obra", data)
            stats = data.get("estadistiques", {})
            revisio = data.get("revisio", {})

            # Crear slug
            autor_dir = obra_path.parent.name
            obra_dir = obra_path.name
            slug = f"{autor_dir}-{obra_dir}"

            # Determinar gènere per defecte segons llengua
            genere = obra_data.get("genere", "FIL")
            if obra_data.get("llengua_original") == "grec":
                genere = "FIL"

            return ObraMetadata(
                slug=slug,
                autor_dir=autor_dir,
                obra_dir=obra_dir,
                titol=obra_data.get("titol", obra_dir.title()),
                titol_original=obra_data.get("titol_original"),
                autor=obra_data.get("autor", autor_dir.title()),
                autor_original=obra_data.get("autor_original"),
                traductor=obra_data.get("traductor", "Biblioteca Arion"),
                any_original=str(obra_data.get("any_original", "")),
                any_traduccio=obra_data.get("any_traduccio", datetime.now().year),
                llengua_original=obra_data.get("llengua_original", "grec"),
                descripcio=obra_data.get("descripcio", ""),
                estat=revisio.get("estat", "esborrany"),
                qualitat=revisio.get("qualitat"),
                paraules_original=stats.get("paraules_original", 0),
                paraules_traduccio=stats.get("paraules_traduccio", 0),
                genere=genere,
            )
        except Exception as e:
            self.log_warning(f"Error llegint metadata de {obra_path}: {e}")
            return None

    def _convertir_markdown(self, contingut: str) -> str:
        """Converteix Markdown a HTML."""
        # Preprocessar sintaxi Pandoc-style a HTML
        # Convertir [text]{.class data-attr="val"} a <span class="class" data-attr="val">text</span>
        import re

        def pandoc_to_html(match):
            text = match.group(1)
            attrs = match.group(2)

            # Extreure classe
            class_match = re.search(r'\.(\w+)', attrs)
            class_attr = f' class="{class_match.group(1)}"' if class_match else ''

            # Extreure data-term
            data_match = re.search(r'data-term="([^"]+)"', attrs)
            data_attr = f' data-term="{data_match.group(1)}"' if data_match else ''

            return f'<span{class_attr}{data_attr}>{text}</span>'

        # Pattern per [text]{.class data-term="value"}
        contingut = re.sub(r'\[([^\]]+)\]\{([^}]+)\}', pandoc_to_html, contingut)

        self.md.reset()
        return self.md.convert(contingut)

    def _llegir_contingut(self, obra_path: Path, fitxer: str) -> str:
        """Llegeix i converteix un fitxer Markdown."""
        file_path = obra_path / fitxer
        if not file_path.exists():
            return ""

        try:
            contingut = file_path.read_text(encoding="utf-8")
            return self._convertir_markdown(contingut)
        except Exception as e:
            self.log_warning(f"Error llegint {file_path}: {e}")
            return ""

    def _llegir_glossari(self, obra_path: Path) -> list[dict]:
        """Llegeix el glossari d'una obra."""
        glossari_file = obra_path / "glossari.yml"
        if not glossari_file.exists():
            return []

        try:
            with open(glossari_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            termes = data.get("termes", data) if isinstance(data, dict) else data
            if not isinstance(termes, list):
                return []

            glossari = []
            for i, terme in enumerate(termes):
                if isinstance(terme, dict):
                    glossari.append({
                        "id": terme.get("id", str(i + 1)),
                        "grec": terme.get("original", terme.get("grec", terme.get("sanscrit", ""))),
                        "transliteracio": terme.get("transliteracio", ""),
                        "traduccio": terme.get("traduccio", terme.get("catala", "")),
                        "definicio": terme.get("definicio", terme.get("nota", "")),
                        "usos": terme.get("usos", []),
                    })
            return glossari
        except Exception as e:
            self.log_warning(f"Error llegint glossari de {obra_path}: {e}")
            return []

    def _llegir_notes(self, obra_path: Path) -> list[dict]:
        """Llegeix les notes d'una obra."""
        notes_file = obra_path / "notes.md"
        if not notes_file.exists():
            return []

        try:
            contingut = notes_file.read_text(encoding="utf-8")

            # Parsejar notes (format: ## [N] Títol\nContingut)
            notes = []
            import re
            pattern = r'##\s*\[(\d+)\]\s*(.*?)\n(.*?)(?=\n##\s*\[|\Z)'
            matches = re.finditer(pattern, contingut, re.DOTALL)

            for match in matches:
                nota_id = match.group(1)
                titol = match.group(2).strip()
                text = match.group(3).strip()
                notes.append({
                    "id": nota_id,
                    "titol": titol,
                    "contingut": self._convertir_markdown(text),
                    "refs": "",
                })

            # Si no hi ha notes amb format, retornar el contingut com una sola nota
            if not notes and contingut.strip():
                notes.append({
                    "id": "1",
                    "titol": "Notes",
                    "contingut": self._convertir_markdown(contingut),
                    "refs": "",
                })

            return notes
        except Exception as e:
            self.log_warning(f"Error llegint notes de {obra_path}: {e}")
            return []

    def _generar_portada(
        self, metadata: ObraMetadata, output_path: Path, obra_path: Path | None = None
    ) -> str | None:
        """Genera o copia la portada d'una obra.

        Primer busca si existeix portada.png a la carpeta de l'obra.
        Si no existeix i el portadista està disponible, en genera una de nova.
        """
        portada_filename = f"{metadata.slug}-portada.png"
        portada_dest = output_path / portada_filename

        # 1. Buscar portada existent a la carpeta de l'obra
        if obra_path:
            portada_existent = obra_path / "portada.png"
            if portada_existent.exists():
                shutil.copy(portada_existent, portada_dest)
                self.log_info(f"Portada copiada: {portada_existent.name} -> {portada_dest.name}")
                return f"assets/portades/{portada_filename}"

        # 2. Si no existeix, generar amb Venice.ai
        if not self.portadista:
            return None

        try:
            portada_data = {
                "titol": metadata.titol,
                "autor": metadata.autor,
                "genere": metadata.genere,
                "descripcio": metadata.descripcio,
            }

            self.log_info(f"Generant portada per a {metadata.titol}...")
            portada_bytes = self.portadista.generar_portada(portada_data)

            # Guardar
            portada_dest.write_bytes(portada_bytes)

            self.log_info(f"Portada guardada: {portada_dest}")
            return f"assets/portades/{portada_filename}"
        except Exception as e:
            self.log_warning(f"Error generant portada: {e}")
            return None

    def publicar_obra(
        self,
        obra_path: Path,
        generar_portada: bool | None = None,
    ) -> tuple[Path, ObraMetadata] | None:
        """Publica una obra individual a HTML.

        Args:
            obra_path: Ruta a la carpeta de l'obra (obres/autor/obra)
            generar_portada: Si True, genera portada nova. None usa config.

        Returns:
            Tupla (path HTML, metadades actualitzades) o None si error.
        """
        # Llegir metadata
        metadata = self._llegir_metadata(obra_path)
        if not metadata:
            return None

        self.log_info(f"Publicant: {metadata.titol} ({metadata.autor})")

        # Preparar directoris
        output_dir = self.publisher_config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        portades_dir = output_dir / "assets" / "portades"
        portades_dir.mkdir(parents=True, exist_ok=True)

        # Buscar o generar portada
        if generar_portada is None:
            generar_portada = self.publisher_config.generar_portades

        portada_filename = f"{metadata.slug}-portada.png"
        portada_dest = portades_dir / portada_filename

        # 1. Si ja existeix al directori de sortida, usar-la
        if portada_dest.exists():
            metadata.portada_url = f"assets/portades/{portada_filename}"
        # 2. Buscar portada a la carpeta de l'obra i copiar-la
        elif obra_path and (obra_path / "portada.png").exists():
            import shutil
            shutil.copy(obra_path / "portada.png", portada_dest)
            self.log_info(f"Portada copiada: portada.png -> {portada_dest.name}")
            metadata.portada_url = f"assets/portades/{portada_filename}"
        # 3. Generar nova portada si està activat
        elif generar_portada:
            metadata.portada_url = self._generar_portada(metadata, portades_dir, obra_path)

        # Llegir continguts
        contingut_original = self._llegir_contingut(obra_path, "original.md")
        contingut_traduccio = self._llegir_contingut(obra_path, "traduccio.md")
        glossari = self._llegir_glossari(obra_path)
        notes = self._llegir_notes(obra_path)

        # Renderitzar template
        try:
            template = self.jinja_env.get_template("obra.html")
            html = template.render(
                obra=metadata.model_dump(),
                contingut_original=contingut_original,
                contingut_traduccio=contingut_traduccio,
                glossari=glossari,
                notes=notes,
                bibliografia=None,
                base_url=self.publisher_config.base_url,
                site_url=self.publisher_config.site_url,
                active_page="",
            )

            # Guardar HTML
            output_file = output_dir / f"{metadata.slug}.html"
            output_file.write_text(html, encoding="utf-8")

            self.log_info(f"HTML generat: {output_file}")
            return (output_file, metadata)

        except Exception as e:
            self.log_warning(f"Error renderitzant template: {e}")
            return None

    def _descobrir_obres(self) -> list[Path]:
        """Descobreix totes les obres disponibles a qualsevol nivell."""
        obres_dir = self.publisher_config.obres_dir
        obres = []

        if not obres_dir.exists():
            self.log_warning(f"Directori d'obres no trobat: {obres_dir}")
            return obres

        # Buscar recursivament tots els directoris amb metadata.yml
        for metadata_file in obres_dir.rglob("metadata.yml"):
            obra_dir = metadata_file.parent
            # Excloure directoris ocults
            if not any(part.startswith(".") for part in obra_dir.parts):
                obres.append(obra_dir)

        return sorted(obres)

    def _generar_index(self, obres_metadata: list[ObraMetadata]) -> Path:
        """Genera la pàgina d'índex."""
        # Calcular estadístiques
        stats = {
            "total_obres": len(obres_metadata),
            "total_autors": len(set(o.autor for o in obres_metadata)),
            "total_paraules": sum(o.paraules_traduccio for o in obres_metadata),
        }

        # Preparar dades per al template
        obres_data = [
            {
                **o.model_dump(),
                "url": f"{o.slug}.html",
            }
            for o in sorted(obres_metadata, key=lambda x: (x.autor, x.titol))
        ]

        try:
            template = self.jinja_env.get_template("index.html")
            html = template.render(
                obres=obres_data,
                stats=stats,
                base_url=self.publisher_config.base_url,
                site_url=self.publisher_config.site_url,
                active_page="index",
            )

            output_file = self.publisher_config.output_dir / "index.html"
            output_file.write_text(html, encoding="utf-8")

            self.log_info(f"Índex generat: {output_file}")
            return output_file

        except Exception as e:
            self.log_warning(f"Error generant índex: {e}")
            return self.publisher_config.output_dir / "index.html"

    # Biografies dels autors
    BIOGRAFIES_AUTORS: dict[str, dict] = {
        "Akutagawa Ryūnosuke": {
            "bio": "Escriptor japonès (1892-1927), mestre del conte curt i figura cabdal de la literatura Taishō. Conegut per la seva prosa elegant i els seus relats psicològics, va influir profundament en la literatura japonesa moderna. El premi Akutagawa, el més prestigiós del Japó, porta el seu nom.",
            "imatge": "akutagawa.png",
        },
        "Anònim (tradició budista)": {
            "bio": "Els textos de la tradició Prajñāpāramitā van ser compilats entre els segles I aC i VI dC per mestres anònims de diverses escoles budistes. Representen l'essència del budisme Mahāyāna i la doctrina de la vacuïtat (śūnyatā).",
            "imatge": "budisme.png",
        },
        "Arthur Schopenhauer": {
            "bio": "Filòsof alemany (1788-1860), autor de 'El món com a voluntat i representació'. El seu pessimisme metafísic i la seva filosofia de la voluntat van influir en Nietzsche, Wagner, Freud i Wittgenstein. Fou un dels primers pensadors occidentals a integrar idees del budisme.",
            "imatge": "schopenhauer.png",
        },
        "Epictetus": {
            "bio": "Filòsof estoic grec (c. 50-135 dC), nascut esclau a Hieràpolis. Després de ser alliberat, va ensenyar filosofia a Roma i Nicòpolis. Les seves ensenyances, recollides pel seu deixeble Arrià, han inspirat pensadors des de Marc Aureli fins al estoïcisme modern.",
            "imatge": "epictetus.png",
        },
        "Heràclit d'Efes": {
            "bio": "Filòsof presocràtic grec (c. 535-475 aC), conegut com 'l'Obscur' pel seu estil enigmàtic. La seva doctrina del flux perpetu ('tot flueix'), la unitat dels contraris i el Logos com a principi còsmic el converteixen en un dels pensadors més influents de l'antiguitat.",
            "imatge": "heraclit.png",
        },
        "Plató": {
            "bio": "Filòsof atenenc (c. 428-348 aC), deixeble de Sòcrates i mestre d'Aristòtil. Fundador de l'Acadèmia, la primera institució d'educació superior d'Occident. Els seus diàlegs han definit la filosofia occidental durant més de dos mil·lennis.",
            "imatge": "plato.png",
        },
        "Sèneca": {
            "bio": "Filòsof estoic, dramaturg i home d'estat romà (c. 4 aC-65 dC). Tutor i conseller de Neró, les seves cartes i tractats morals són obres mestres de la prosa llatina i guies pràctiques per a la vida virtuosa que continuen inspirant lectors avui.",
            "imatge": "seneca.png",
        },
    }

    def _generar_autors(self, obres_metadata: list[ObraMetadata]) -> Path:
        """Genera la pàgina d'autors amb retrats i biografies."""
        # Agrupar obres per autor
        autors: dict[str, dict] = {}
        for obra in obres_metadata:
            if obra.autor not in autors:
                # Buscar biografia i imatge
                info_autor = self.BIOGRAFIES_AUTORS.get(obra.autor, {})
                autors[obra.autor] = {
                    "nom": obra.autor,
                    "nom_original": obra.autor_original,
                    "bio": info_autor.get("bio", ""),
                    "imatge": info_autor.get("imatge", ""),
                    "obres": [],
                }
            autors[obra.autor]["obres"].append(obra.model_dump())

        autors_list = sorted(autors.values(), key=lambda x: x["nom"])
        base = self.publisher_config.base_url

        try:
            html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Autors de la Biblioteca Arion - Traduccions obertes de clàssics universals al català">
    <meta name="author" content="Biblioteca Arion">
    <meta name="keywords" content="traduccions, clàssics, grec, llatí, alemany, català, filosofia, literatura, autors">

    <!-- Open Graph -->
    <meta property="og:title" content="Autors - Biblioteca Arion">
    <meta property="og:description" content="Autors de les traduccions obertes de clàssics universals al català">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{self.publisher_config.site_url}autors.html">
    <meta property="og:site_name" content="Biblioteca Arion">
    <meta property="og:locale" content="ca_ES">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Autors - Biblioteca Arion">
    <meta name="twitter:description" content="Autors de les traduccions obertes de clàssics universals al català">

    <title>Autors | Biblioteca Arion</title>

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Source+Serif+Pro:ital,wght@0,400;0,600;0,700;1,400&family=Lato:wght@400;500;700&family=GFS+Didot&display=swap" rel="stylesheet">

    <!-- Styles -->
    <link rel="stylesheet" href="{base}css/styles.css">

    <style>
        .autors-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--spacing-xl);
        }}

        .autor-card {{
            display: flex;
            gap: var(--spacing-xl);
            background-color: var(--color-bg-primary);
            border: 1px solid var(--color-border-light);
            border-radius: var(--radius-lg);
            padding: var(--spacing-xl);
            transition: all var(--transition-normal);
        }}

        .autor-card:hover {{
            border-color: var(--color-accent);
            box-shadow: var(--shadow-md);
        }}

        .autor-retrat {{
            flex-shrink: 0;
        }}

        .autor-retrat img {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--color-border-light);
            box-shadow: var(--shadow-md);
        }}

        .autor-info {{
            flex: 1;
        }}

        .autor-info h2 {{
            font-family: var(--font-titles);
            font-size: var(--font-size-2xl);
            font-weight: 600;
            margin-bottom: var(--spacing-xs);
            margin-top: 0;
            padding-bottom: 0;
            border-bottom: none;
        }}

        .autor-nom-original {{
            font-size: var(--font-size-sm);
            color: var(--color-text-muted);
            margin-bottom: var(--spacing-sm);
            font-style: italic;
        }}

        .autor-bio {{
            font-size: var(--font-size-sm);
            color: var(--color-text-secondary);
            line-height: var(--line-height-base);
            margin-bottom: var(--spacing-md);
        }}

        .autor-obres {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-wrap: wrap;
            gap: var(--spacing-sm);
        }}

        .autor-obres li {{
            padding: 0;
        }}

        .autor-obres a {{
            display: inline-block;
            font-size: var(--font-size-sm);
            padding: var(--spacing-xs) var(--spacing-sm);
            background-color: var(--color-bg-secondary);
            border-radius: var(--radius-sm);
            transition: all var(--transition-fast);
        }}

        .autor-obres a:hover {{
            background-color: var(--color-accent);
            color: white;
        }}

        @media (max-width: 768px) {{
            .autor-card {{
                flex-direction: column;
                align-items: center;
                text-align: center;
            }}

            .autor-obres {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <header class="site-header">
        <div class="container">
            <div class="header-inner">
                <div class="site-logo">
                    <a href="{base}index.html" class="site-brand">
                        <img src="{base}assets/logo/logo_arion_v1.png" alt="Logo Arion" class="site-logo-img">
                        <span class="site-title">Biblioteca Arion</span>
                    </a>
                </div>

                <div class="header-actions">
                    <button class="icon-btn theme-toggle" aria-label="Canviar tema" title="Mode fosc/clar">
                        <span class="theme-icon">🌙</span>
                    </button>
                    <a href="{base}index.html" class="btn-secondary" style="padding: 0.5rem 1rem;">Catàleg</a>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main>
        <section class="page-content">
            <div class="container">
                <header class="page-header text-center">
                    <h1>Autors</h1>
                    <p style="color: var(--color-text-muted); margin-top: var(--spacing-sm);">{len(autors_list)} autors traduïts</p>
                </header>

                <div class="autors-grid">
"""
            for autor in autors_list:
                imatge_html = ""
                if autor['imatge']:
                    imatge_path = self.publisher_config.output_dir / "assets" / "autors" / autor['imatge']
                    if imatge_path.exists():
                        imatge_html = f'''
                    <div class="autor-retrat">
                        <img src="{base}assets/autors/{autor['imatge']}" alt="Retrat de {autor['nom']}">
                    </div>'''

                # Crear slug i generar fitxa individual
                autor_slug = autor['nom'].lower().replace(' ', '-').replace('(', '').replace(')', '').replace("'", '')
                self._generar_fitxa_autor(autor, base)

                html += f"""
                    <article class="autor-card" id="{autor_slug}">
                        {imatge_html}
                        <div class="autor-info">
                            <h2><a href="{base}autor-{autor_slug}.html">{autor['nom']}</a></h2>
                            {f'<p class="autor-nom-original">{autor["nom_original"]}</p>' if autor['nom_original'] else ''}
                            {f'<p class="autor-bio">{autor["bio"]}</p>' if autor['bio'] else ''}
                            <ul class="autor-obres">
"""
                for obra in autor['obres']:
                    html += f"""                                <li><a href="{base}{obra['slug']}.html">{obra['titol']}</a></li>
"""
                html += """                            </ul>
                        </div>
                    </article>
"""

            html += f"""
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="site-footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-section">
                    <h4>Biblioteca Arion</h4>
                    <p>Biblioteca oberta i col·laborativa de traduccions al català d'obres clàssiques universals.</p>
                </div>

                <div class="footer-section">
                    <h4>Navegació</h4>
                    <ul>
                        <li><a href="{base}index.html">Catàleg d'obres</a></li>
                        <li><a href="{base}autors.html">Autors</a></li>
                        <li><a href="{base}glossari.html">Glossari general</a></li>
                    </ul>
                </div>

                <div class="footer-section">
                    <h4>Recursos</h4>
                    <ul>
                        <li><a href="{base}metodologia.html">Metodologia</a></li>
                        <li><a href="{base}collaborar.html">Col·laborar</a></li>
                        <li><a href="{base}contacte.html">Contacte</a></li>
                    </ul>
                </div>

                <div class="footer-section">
                    <h4>Llicència</h4>
                    <p><small>Textos originals de domini públic. Traduccions sota llicència oberta CC BY-SA 4.0.</small></p>
                    <p><small>© 2026 Biblioteca Arion</small></p>
                </div>
            </div>

            <div class="footer-bottom">
                <p>Fet amb dedicació per a la cultura catalana</p>
            </div>
        </div>
    </footer>

    <!-- Theme Toggle Script -->
    <script>
        const themeToggle = document.querySelector('.theme-toggle');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

        function setTheme(dark) {{
            document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
            themeToggle.textContent = dark ? '☀️' : '🌙';
            localStorage.setItem('theme', dark ? 'dark' : 'light');
        }}

        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {{
            setTheme(savedTheme === 'dark');
        }} else {{
            setTheme(prefersDark.matches);
        }}

        themeToggle.addEventListener('click', () => {{
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            setTheme(!isDark);
        }});
    </script>

    <script src="{base}js/app.js"></script>
</body>
</html>
"""
            output_file = self.publisher_config.output_dir / "autors.html"
            output_file.write_text(html, encoding="utf-8")

            self.log_info(f"Pàgina d'autors generada: {output_file}")
            return output_file

        except Exception as e:
            self.log_warning(f"Error generant pàgina d'autors: {e}")
            return self.publisher_config.output_dir / "autors.html"

    def _generar_fitxa_autor(self, autor: dict, base: str) -> Path:
        """Genera una fitxa individual per a un autor."""
        autor_slug = autor['nom'].lower().replace(' ', '-').replace('(', '').replace(')', '').replace("'", '')

        # Imatge de l'autor
        imatge_html = ""
        if autor['imatge']:
            imatge_path = self.publisher_config.output_dir / "assets" / "autors" / autor['imatge']
            if imatge_path.exists():
                imatge_html = f'<img src="{base}assets/autors/{autor["imatge"]}" alt="Retrat de {autor["nom"]}" class="autor-retrat-gran">'

        # Llista d'obres
        obres_html = ""
        for obra in autor['obres']:
            portada_html = ""
            if obra.get('portada_url'):
                portada_html = f'<img src="{base}{obra["portada_url"]}" alt="Portada de {obra["titol"]}" class="obra-mini-portada">'
            obres_html += f'''
                <a href="{base}{obra['slug']}.html" class="autor-obra-card">
                    {portada_html}
                    <div class="autor-obra-info">
                        <h3>{obra['titol']}</h3>
                        <p>{obra.get('llengua_original', '').capitalize()} · {obra.get('any_original', '')}</p>
                    </div>
                </a>'''

        html = f'''<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{autor['nom']} - Autor a la Biblioteca Arion">
    <title>{autor['nom']} | Biblioteca Arion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Source+Serif+Pro:ital,wght@0,400;0,600;0,700;1,400&family=Lato:wght@400;500;700&family=GFS+Didot&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{base}css/styles.css">
    <style>
        .autor-header {{
            text-align: center;
            padding: var(--spacing-3xl) 0;
            background: linear-gradient(180deg, var(--color-bg-secondary) 0%, var(--color-bg-primary) 100%);
        }}
        .autor-retrat-gran {{
            width: 180px;
            height: 180px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid var(--color-border-light);
            box-shadow: var(--shadow-lg);
            margin-bottom: var(--spacing-lg);
        }}
        .autor-header h1 {{
            font-family: var(--font-titles);
            font-size: var(--font-size-3xl);
            margin: 0 0 var(--spacing-xs);
        }}
        .autor-nom-original {{
            font-size: var(--font-size-lg);
            color: var(--color-text-muted);
            font-style: italic;
            margin: 0 0 var(--spacing-lg);
        }}
        .autor-bio {{
            max-width: 700px;
            margin: 0 auto;
            font-size: var(--font-size-base);
            line-height: var(--line-height-relaxed);
            color: var(--color-text-secondary);
        }}
        .autor-obres-section {{
            padding: var(--spacing-2xl) 0;
        }}
        .autor-obres-section h2 {{
            text-align: center;
            margin-bottom: var(--spacing-xl);
        }}
        .autor-obres-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: var(--spacing-lg);
            max-width: 900px;
            margin: 0 auto;
        }}
        .autor-obra-card {{
            display: flex;
            gap: var(--spacing-md);
            padding: var(--spacing-md);
            background: var(--color-bg-primary);
            border: 1px solid var(--color-border-light);
            border-radius: var(--radius-md);
            text-decoration: none;
            color: inherit;
            transition: all var(--transition-fast);
        }}
        .autor-obra-card:hover {{
            border-color: var(--color-accent);
            box-shadow: var(--shadow-md);
        }}
        .obra-mini-portada {{
            width: 60px;
            height: 90px;
            object-fit: cover;
            border-radius: var(--radius-sm);
            flex-shrink: 0;
        }}
        .autor-obra-info h3 {{
            font-family: var(--font-titles);
            font-size: var(--font-size-base);
            margin: 0 0 var(--spacing-xs);
        }}
        .autor-obra-info p {{
            font-size: var(--font-size-sm);
            color: var(--color-text-muted);
            margin: 0;
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="header-inner">
                <div class="site-logo">
                    <a href="{base}index.html" class="site-brand">
                        <img src="{base}assets/logo/logo_arion_v1.png" alt="Logo Arion" class="site-logo-img">
                        <span class="site-title">Biblioteca Arion</span>
                    </a>
                </div>
                <div class="header-actions">
                    <button class="icon-btn theme-toggle" aria-label="Canviar tema" title="Mode fosc/clar">
                        <span class="theme-icon">🌙</span>
                    </button>
                    <a href="{base}autors.html" class="btn-secondary" style="padding: 0.5rem 1rem;">Autors</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <section class="autor-header">
            <div class="container">
                {imatge_html}
                <h1>{autor['nom']}</h1>
                {f'<p class="autor-nom-original">{autor["nom_original"]}</p>' if autor['nom_original'] else ''}
                {f'<p class="autor-bio">{autor["bio"]}</p>' if autor['bio'] else ''}
            </div>
        </section>

        <section class="autor-obres-section">
            <div class="container">
                <h2>Obres traduïdes</h2>
                <div class="autor-obres-grid">
                    {obres_html}
                </div>
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <div class="footer-bottom">
                <p>© 2026 Biblioteca Universal Arion · Fet amb dedicació per a la cultura catalana</p>
            </div>
        </div>
    </footer>

    <script src="{base}js/app.js"></script>
</body>
</html>'''

        output_file = self.publisher_config.output_dir / f"autor-{autor_slug}.html"
        output_file.write_text(html, encoding="utf-8")
        self.log_info(f"Fitxa d'autor generada: {output_file}")
        return output_file

    def publicar_tot(
        self,
        generar_portades: bool | None = None,
        obres_filtrades: list[str] | None = None,
    ) -> dict:
        """Publica totes les obres i genera l'índex.

        Args:
            generar_portades: Si True, genera portades. None usa config.
            obres_filtrades: Si es proporciona, només publica aquestes obres (slugs).

        Returns:
            Dict amb estadístiques de publicació.
        """
        self.log_info("Iniciant publicació completa...")

        # Descobrir obres
        obres_paths = self._descobrir_obres()
        self.log_info(f"Trobades {len(obres_paths)} obres")

        # Publicar cada obra
        obres_publicades: list[ObraMetadata] = []
        errors: list[str] = []

        for obra_path in obres_paths:
            # Filtrar si cal
            if obres_filtrades:
                slug = f"{obra_path.parent.name}-{obra_path.name}"
                if slug not in obres_filtrades:
                    continue

            # Publicar (retorna metadades amb portada_url actualitzat)
            result = self.publicar_obra(obra_path, generar_portada=generar_portades)
            if result:
                _, metadata = result
                obres_publicades.append(metadata)
            else:
                errors.append(f"Error publicant: {obra_path}")

        # Generar índex i pàgines auxiliars
        # IMPORTANT: Només regenerar índex si NO hi ha filtre d'obres
        # Si hi ha filtre, només es publiquen les obres individuals sense tocar l'índex
        if obres_publicades and not obres_filtrades:
            self._generar_index(obres_publicades)
            self._generar_autors(obres_publicades)
        elif obres_filtrades:
            self.log_info("Obres filtrades: índex i autors NO regenerats (usar sense --obra per actualitzar)")

        # Copiar assets estàtics si no existeixen
        self._copiar_assets_estatics()

        # Resum
        return {
            "obres_publicades": len(obres_publicades),
            "errors": errors,
            "output_dir": str(self.publisher_config.output_dir),
            "obres": [o.slug for o in obres_publicades],
        }

    def _copiar_assets_estatics(self) -> None:
        """Copia CSS i JS si no existeixen."""
        output_dir = self.publisher_config.output_dir

        # CSS
        css_source = Path("web/static/css")
        css_dest = output_dir / "css"
        if css_source.exists() and not css_dest.exists():
            shutil.copytree(css_source, css_dest)
            self.log_info("CSS copiat")

        # JS
        js_source = Path("web/static/js")
        js_dest = output_dir / "js"
        if js_source.exists() and not js_dest.exists():
            shutil.copytree(js_source, js_dest)
            self.log_info("JS copiat")


def publicar_biblioteca(
    generar_portades: bool = False,
    obres: list[str] | None = None,
) -> dict:
    """Funció ràpida per publicar la biblioteca.

    Args:
        generar_portades: Si True, genera portades noves amb Venice.ai
        obres: Llista de slugs a publicar (None = totes)

    Returns:
        Estadístiques de publicació.
    """
    publisher = WebPublisher()
    return publisher.publicar_tot(
        generar_portades=generar_portades,
        obres_filtrades=obres,
    )


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("BIBLIOTECA ARION - WEB PUBLISHER")
    print("=" * 60)

    # Opcions CLI
    generar_portades = "--portades" in sys.argv

    if generar_portades:
        print("Mode: Amb generació de portades")
    else:
        print("Mode: Sense portades (usa --portades per generar-les)")

    print()

    result = publicar_biblioteca(generar_portades=generar_portades)

    print()
    print("=" * 60)
    print("RESULTAT")
    print("=" * 60)
    print(f"Obres publicades: {result['obres_publicades']}")
    print(f"Directori: {result['output_dir']}")

    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    if result['obres']:
        print("\nObres:")
        for obra in result['obres']:
            print(f"  - {obra}")
