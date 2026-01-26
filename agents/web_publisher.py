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
                        "id": i + 1,
                        "grec": terme.get("original", terme.get("grec", "")),
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

        # Generar portada si cal
        if generar_portada is None:
            generar_portada = self.publisher_config.generar_portades

        if generar_portada:
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
        """Descobreix totes les obres disponibles."""
        obres_dir = self.publisher_config.obres_dir
        obres = []

        if not obres_dir.exists():
            self.log_warning(f"Directori d'obres no trobat: {obres_dir}")
            return obres

        for autor_dir in obres_dir.iterdir():
            if not autor_dir.is_dir() or autor_dir.name.startswith("."):
                continue

            for obra_dir in autor_dir.iterdir():
                if not obra_dir.is_dir() or obra_dir.name.startswith("."):
                    continue

                # Verificar que té metadata.yml
                if (obra_dir / "metadata.yml").exists():
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

    def _generar_autors(self, obres_metadata: list[ObraMetadata]) -> Path:
        """Genera la pàgina d'autors."""
        # Agrupar obres per autor
        autors: dict[str, dict] = {}
        for obra in obres_metadata:
            if obra.autor not in autors:
                autors[obra.autor] = {
                    "nom": obra.autor,
                    "nom_original": obra.autor_original,
                    "obres": [],
                }
            autors[obra.autor]["obres"].append(obra.model_dump())

        autors_list = sorted(autors.values(), key=lambda x: x["nom"])

        try:
            # Template senzill per autors
            html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autors | Biblioteca Arion</title>
    <link rel="stylesheet" href="{self.publisher_config.base_url}css/styles.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="header-inner">
                <div class="site-logo">
                    <a href="{self.publisher_config.base_url}index.html" class="site-title">Biblioteca Arion</a>
                    <p class="site-tagline">Traduccions de clàssics universals al català</p>
                </div>
                <nav class="main-nav">
                    <ul>
                        <li><a href="{self.publisher_config.base_url}index.html">Catàleg</a></li>
                        <li><a href="{self.publisher_config.base_url}autors.html" class="active">Autors</a></li>
                        <li><a href="{self.publisher_config.base_url}sobre.html">Sobre</a></li>
                    </ul>
                </nav>
            </div>
        </div>
    </header>
    <main>
        <section class="page-content">
            <div class="container">
                <h1 class="text-center">Autors</h1>
                <div class="autors-grid" style="display: grid; gap: 2rem; margin-top: 2rem;">
"""
            for autor in autors_list:
                html += f"""
                    <article class="autor-card">
                        <h2>{autor['nom']}</h2>
                        {"<p><em>" + autor['nom_original'] + "</em></p>" if autor['nom_original'] else ""}
                        <ul>
"""
                for obra in autor['obres']:
                    html += f"""                            <li><a href="{self.publisher_config.base_url}{obra['slug']}.html">{obra['titol']}</a></li>
"""
                html += """                        </ul>
                    </article>
"""

            html += """
                </div>
            </div>
        </section>
    </main>
    <footer class="site-footer">
        <div class="container">
            <p class="text-center">Biblioteca Arion - Traduccions obertes de clàssics universals</p>
        </div>
    </footer>
    <script src="js/app.js"></script>
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
        if obres_publicades:
            self._generar_index(obres_publicades)
            self._generar_autors(obres_publicades)

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
