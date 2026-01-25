#!/usr/bin/env python3
"""
Pipeline Editorial Complet per a El Convit de Plató.

Executa tots els agents seqüencialment:
1. CORRECTOR - Correcció normativa IEC
2. ESTIL - Poliment literari
3. GLOSSARISTA - Glossari i índex onomàstic
4. INVESTIGADOR - Context històric
5. EDICIÓ CRÍTICA - Notes a peu de pàgina
6. INTRODUCCIÓ - Pròleg i nota del traductor
7. PUBLICADOR EPUB - Generació de l'EPUB final
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Afegir el directori arrel al path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

from agents.corrector import CorrectorAgent, CorrectionRequest
from agents.agent_estil import EstilAgent, StyleRequest
from agents.glossarista import GlossaristaAgent, GlossaryRequest
from agents.investigador import InvestigadorAgent, ResearchRequest
from agents.edicio_critica import EdicioCriticaAgent, AnnotationRequest
from agents.introduccio import IntroduccioAgent, IntroductionRequest
from agents.publicador_epub import PublicadorEPUBAgent, PublishRequest, EPUBMetadata, EPUBStructure
from utils.logger import AgentLogger, VerbosityLevel, SessionStats


console = Console()


class EditorialPipeline:
    """Pipeline editorial complet."""

    def __init__(
        self,
        input_path: str,
        original_path: str | None,
        output_dir: str,
        verbosity: VerbosityLevel = VerbosityLevel.VERBOSE,
        author: str = "Plató",
        title: str = "El Convit",
    ):
        self.input_path = Path(input_path)
        self.original_path = Path(original_path) if original_path else None
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.author = author
        self.title = title
        self.verbosity = verbosity

        # Carregar textos
        self.text_traduit = self.input_path.read_text(encoding="utf-8")
        self.text_original = self.original_path.read_text(encoding="utf-8") if self.original_path else None

        # Logger
        self.logger = AgentLogger(
            verbosity=verbosity,
            log_dir=str(self.output_dir / "logs"),
            session_name="editorial_pipeline"
        )

        # Estadístiques globals
        self.stats = SessionStats()
        self.start_time = datetime.now()

        # Resultats intermedis
        self.results = {}

    def _log_stage(self, stage: str, message: str):
        """Mostra informació d'etapa."""
        if self.verbosity >= VerbosityLevel.NORMAL:
            console.print(Panel(f"[bold cyan]{message}[/bold cyan]", title=f"[bold yellow]{stage}[/bold yellow]"))

    def _log_result(self, stage: str, success: bool, details: str = ""):
        """Mostra resultat d'etapa."""
        if success:
            console.print(f"  [green]✓[/green] {stage}: {details}")
        else:
            console.print(f"  [red]✗[/red] {stage}: {details}")

    def _save_result(self, filename: str, content: str | dict):
        """Desa resultat a fitxer."""
        filepath = self.output_dir / filename
        if isinstance(content, dict):
            filepath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            filepath.write_text(content, encoding="utf-8")
        return filepath

    def run_corrector(self) -> bool:
        """Etapa 1: Correcció normativa."""
        self._log_stage("1/7 CORRECTOR", "Aplicant correcció normativa IEC...")

        try:
            agent = CorrectorAgent()
            request = CorrectionRequest(
                text=self.text_traduit,
                autor=self.author,
                titol=self.title,
                llengua="català"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Corregint...", total=None)
                response = agent.correct(request)
                progress.update(task, completed=True)

            if response.content:
                # Intentar parsejar JSON
                try:
                    result = json.loads(response.content)
                    text_corregit = result.get("text_corregit", response.content)
                    num_correccions = len(result.get("correccions", []))
                except json.JSONDecodeError:
                    text_corregit = response.content
                    num_correccions = 0

                self.results["text_corregit"] = text_corregit
                filepath = self._save_result("text_corregit.txt", text_corregit)

                self.stats.add_call(
                    agent_name="Corrector",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Corrector", True, f"{num_correccions} correccions, desat a {filepath.name}")
                return True
            else:
                self._log_result("Corrector", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Corrector", False, str(e))
            return False

    def run_estil(self) -> bool:
        """Etapa 2: Poliment literari."""
        self._log_stage("2/7 AGENT ESTIL", "Polint l'estil literari...")

        text_input = self.results.get("text_corregit", self.text_traduit)

        try:
            agent = EstilAgent()
            request = StyleRequest(
                text=text_input[:15000],  # Limitat per tokens
                genere="diàleg filosòfic",
                epoca="Grècia clàssica (s. IV aC)",
                estil_desitjat="Literari elevat però llegible",
                elements_preservar=["to filosòfic", "ironia socràtica", "registres dels personatges"]
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Polint estil...", total=None)
                response = agent.polish(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                    text_polit = result.get("text_polit", response.content)
                except json.JSONDecodeError:
                    text_polit = response.content

                self.results["text_polit"] = text_polit
                filepath = self._save_result("text_final_polit.txt", text_polit)

                self.stats.add_call(
                    agent_name="Estil",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Estil", True, f"Text polit desat a {filepath.name}")
                return True
            else:
                self._log_result("Estil", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Estil", False, str(e))
            return False

    def run_glossarista(self) -> bool:
        """Etapa 3: Creació de glossari i índex onomàstic."""
        self._log_stage("3/7 GLOSSARISTA", "Creant glossari i índex onomàstic...")

        text_input = self.results.get("text_corregit", self.text_traduit)

        try:
            agent = GlossaristaAgent()
            request = GlossaryRequest(
                text=text_input[:20000],  # Limitat per tokens
                autor=self.author,
                titol=self.title,
                llengua_original="grec",
                incloure_onomastic=True,
                incloure_llocs=True,
                incloure_conceptes=True
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Creant glossari...", total=None)
                response = agent.create_glossary(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                    glossari = result.get("glossari", [])
                    onomastic = result.get("index_onomastic", [])
                except json.JSONDecodeError:
                    result = {"contingut": response.content}
                    glossari = []
                    onomastic = []

                self.results["glossari"] = result

                filepath_glossari = self._save_result("glossari.json", result)
                if onomastic:
                    filepath_onomastic = self._save_result("index_onomastic.json", {"index": onomastic})

                self.stats.add_call(
                    agent_name="Glossarista",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Glossarista", True,
                    f"{len(glossari)} termes, {len(onomastic)} noms propis")
                return True
            else:
                self._log_result("Glossarista", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Glossarista", False, str(e))
            return False

    def run_investigador(self) -> bool:
        """Etapa 4: Investigació del context històric."""
        self._log_stage("4/7 INVESTIGADOR", "Investigant context històric...")

        try:
            agent = InvestigadorAgent()
            request = ResearchRequest(
                autor=self.author,
                titol=self.title,
                text=self.text_traduit[:10000],
                llengua_original="grec",
                tipus_recerca="context",
                arees=["context_historic", "tradicio_manuscrita", "recepcio"]
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Investigant...", total=None)
                response = agent.investigate(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                    context = result.get("context_historic", response.content)
                except json.JSONDecodeError:
                    context = response.content

                self.results["context_historic"] = context

                # Formatar com a Markdown
                if isinstance(context, dict):
                    md_content = f"# Context Històric: {self.title}\n\n"
                    for key, value in context.items():
                        md_content += f"## {key.replace('_', ' ').title()}\n\n{value}\n\n"
                else:
                    md_content = f"# Context Històric: {self.title}\n\n{context}"

                filepath = self._save_result("context_historic.md", md_content)

                self.stats.add_call(
                    agent_name="Investigador",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Investigador", True, f"Context desat a {filepath.name}")
                return True
            else:
                self._log_result("Investigador", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Investigador", False, str(e))
            return False

    def run_edicio_critica(self) -> bool:
        """Etapa 5: Anotació crítica."""
        self._log_stage("5/7 EDICIÓ CRÍTICA", "Afegint notes a peu de pàgina...")

        text_input = self.results.get("text_corregit", self.text_traduit)
        context = self.results.get("context_historic", "")

        try:
            agent = EdicioCriticaAgent(nivell="moderat")
            request = AnnotationRequest(
                text_original=self.text_original[:5000] if self.text_original else "",
                text_traduit=text_input[:10000],
                llengua_original="grec",
                autor=self.author,
                titol=self.title,
                context_investigador=context[:3000] if isinstance(context, str) else str(context)[:3000],
                nivell_detall="moderat"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Anotant...", total=None)
                response = agent.annotate(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                    text_anotat = result.get("text_anotat", "")
                    notes = result.get("notes", [])
                except json.JSONDecodeError:
                    text_anotat = response.content
                    notes = []

                self.results["text_anotat"] = text_anotat
                self.results["notes"] = notes

                filepath = self._save_result("text_amb_notes.txt", text_anotat)
                if notes:
                    self._save_result("notes_peu.json", {"notes": notes})

                self.stats.add_call(
                    agent_name="Edició Crítica",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Edició Crítica", True, f"{len(notes)} notes generades")
                return True
            else:
                self._log_result("Edició Crítica", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Edició Crítica", False, str(e))
            return False

    def run_introduccio(self) -> bool:
        """Etapa 6: Redacció de la introducció."""
        self._log_stage("6/7 INTRODUCCIÓ", "Redactant introducció i nota del traductor...")

        context = self.results.get("context_historic", "")

        try:
            agent = IntroduccioAgent(tipus="divulgativa")

            resum_obra = """El Convit (Simposi) és un diàleg platònic que narra un banquet a casa del
            poeta tràgic Agató, on diversos convidats fan discursos sobre l'amor (Eros). Inclou els
            famosos discursos de Pausànias sobre l'amor vulgar i celestial, el d'Aristòfanes sobre
            els éssers originaris partits en dos, el de Sòcrates transmetent l'ensenyament de Diotima
            sobre l'escala de l'amor cap a la Bellesa en si, i finalment l'elogi d'Alcibíades a Sòcrates."""

            request = IntroductionRequest(
                titol=self.title,
                autor=self.author,
                llengua_original="grec",
                resum_obra=resum_obra,
                context_historic=context[:5000] if isinstance(context, str) else str(context)[:5000],
                public_objectiu="Lector culte general, estudiants de filosofia i literatura",
                tipus="divulgativa",
                incloure_nota_traductor=True,
                criteris_traduccio="""Traducció directa del grec clàssic al català, buscant equilibri
                entre fidelitat al text original i fluïdesa en la llengua d'arribada. S'ha prioritzat
                el to filosòfic i l'oralitat del diàleg. Els termes tècnics grecs s'han traduït
                quan hi ha equivalent català (kalokagathia → bellesa i bondat) o s'han mantingut
                transliterats amb nota explicativa."""
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Redactant introducció...", total=None)
                response = agent.write_introduction(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                    intro = result.get("introduccio", {})
                    nota = result.get("nota_traductor", {})
                except json.JSONDecodeError:
                    intro = {"contingut": response.content}
                    nota = {}

                self.results["introduccio"] = intro
                self.results["nota_traductor"] = nota

                # Formatar com a Markdown
                md_content = f"# Introducció\n\n"
                if isinstance(intro, dict):
                    if "seccions" in intro:
                        for sec in intro["seccions"]:
                            md_content += f"## {sec.get('titol', '')}\n\n{sec.get('contingut', '')}\n\n"
                    else:
                        md_content += str(intro.get("contingut", intro))
                else:
                    md_content += str(intro)

                if nota:
                    md_content += f"\n---\n\n# Nota del Traductor\n\n"
                    md_content += nota.get("contingut", str(nota))

                filepath = self._save_result("introduccio.md", md_content)

                self.stats.add_call(
                    agent_name="Introducció",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Introducció", True, f"Introducció desada a {filepath.name}")
                return True
            else:
                self._log_result("Introducció", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Introducció", False, str(e))
            return False

    def run_publicador(self) -> bool:
        """Etapa 7: Generació de l'EPUB."""
        self._log_stage("7/7 PUBLICADOR EPUB", "Generant especificacions EPUB...")

        text_final = self.results.get("text_anotat",
                     self.results.get("text_polit",
                     self.results.get("text_corregit", self.text_traduit)))

        try:
            agent = PublicadorEPUBAgent()

            metadata = EPUBMetadata(
                titol=self.title,
                autor=self.author,
                traductor="Pipeline Editorial IA",
                llengua="ca",
                editorial="Editorial Clàssica",
                data_publicacio=datetime.now().strftime("%Y-%m-%d"),
                descripcio=f"Traducció catalana de {self.title} de {self.author}. "
                          "Edició bilingüe grec-català amb introducció, notes i glossari.",
                materies=["Filosofia antiga", "Literatura grega", "Plató"]
            )

            estructura = EPUBStructure(
                portada=True,
                introduccio=True,
                nota_traductor=True,
                text_principal=True,
                notes=bool(self.results.get("notes")),
                glossari=bool(self.results.get("glossari"))
            )

            intro_text = ""
            if "introduccio" in self.results:
                intro = self.results["introduccio"]
                if isinstance(intro, dict):
                    intro_text = str(intro.get("contingut", intro))
                else:
                    intro_text = str(intro)

            request = PublishRequest(
                metadata=metadata,
                estructura=estructura,
                text_original=self.text_original[:10000] if self.text_original else None,
                text_traduit=text_final[:15000],
                introduccio=intro_text[:5000] if intro_text else None,
                nota_traductor=str(self.results.get("nota_traductor", ""))[:3000],
                notes=self.results.get("notes"),
                glossari=self.results.get("glossari", {}).get("glossari"),
                format_bilingue=self.text_original is not None
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Generant EPUB...", total=None)
                response = agent.generate_epub_spec(request)
                progress.update(task, completed=True)

            if response.content:
                try:
                    result = json.loads(response.content)
                except json.JSONDecodeError:
                    result = {"especificacions": response.content}

                self.results["epub_spec"] = result
                filepath = self._save_result("epub_especificacions.json", result)

                # Crear estructura de directoris EPUB
                epub_dir = self.output_dir / "epub_files"
                epub_dir.mkdir(exist_ok=True)
                (epub_dir / "META-INF").mkdir(exist_ok=True)
                (epub_dir / "OEBPS").mkdir(exist_ok=True)
                (epub_dir / "OEBPS" / "text").mkdir(exist_ok=True)
                (epub_dir / "OEBPS" / "styles").mkdir(exist_ok=True)

                # Crear container.xml
                container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
                (epub_dir / "META-INF" / "container.xml").write_text(container_xml)

                # Crear CSS bàsic
                css = '''/* Estils per a El Convit de Plató */
body { font-family: Georgia, serif; line-height: 1.6; margin: 2em; }
h1, h2, h3 { font-family: "Palatino Linotype", Palatino, serif; }
.greek { font-style: italic; color: #666; }
.catalan { }
.footnote { font-size: 0.9em; }
.footnote-ref { vertical-align: super; font-size: 0.8em; }
blockquote { margin: 1em 2em; font-style: italic; }
'''
                (epub_dir / "OEBPS" / "styles" / "main.css").write_text(css)

                self.stats.add_call(
                    agent_name="Publicador EPUB",
                    duration=response.duration_seconds,
                    input_tokens=response.usage.get("input_tokens", 0),
                    output_tokens=response.usage.get("output_tokens", 0),
                    cost=response.cost_eur
                )

                self._log_result("Publicador EPUB", True,
                    f"Especificacions a {filepath.name}, estructura a epub_files/")
                return True
            else:
                self._log_result("Publicador EPUB", False, "No s'ha obtingut resposta")
                return False

        except Exception as e:
            self._log_result("Publicador EPUB", False, str(e))
            return False

    def print_summary(self):
        """Mostra resum final del pipeline."""
        duration = (datetime.now() - self.start_time).total_seconds()

        console.print()
        console.print(Panel.fit(
            "[bold green]PIPELINE EDITORIAL COMPLET[/bold green]",
            border_style="green"
        ))

        # Taula de resultats
        table = Table(title="Resum d'Etapes")
        table.add_column("Agent", style="cyan")
        table.add_column("Crides", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost (€)", justify="right")

        total_tokens = 0
        total_cost = 0.0
        for agent_name, agent_stats in self.stats.by_agent.items():
            table.add_row(
                agent_name,
                str(agent_stats["calls"]),
                f"{agent_stats['tokens']:,}",
                f"€{agent_stats['cost']:.4f}"
            )
            total_tokens += agent_stats["tokens"]
            total_cost += agent_stats["cost"]

        console.print(table)

        # Estadístiques globals
        console.print()
        console.print(f"[bold]Temps total:[/bold] {duration:.1f}s")
        console.print(f"[bold]Tokens totals:[/bold] {total_tokens:,}")
        console.print(f"[bold]Cost total:[/bold] €{total_cost:.4f}")

        # Fitxers generats
        console.print()
        console.print("[bold]Fitxers generats:[/bold]")
        for f in sorted(self.output_dir.glob("*")):
            if f.is_file():
                size = f.stat().st_size
                console.print(f"  • {f.name} ({size:,} bytes)")

        # Desar resum
        summary = {
            "temps_total_segons": duration,
            "tokens_totals": total_tokens,
            "cost_total_eur": total_cost,
            "agents": dict(self.stats.by_agent),
            "fitxers": [f.name for f in self.output_dir.glob("*") if f.is_file()]
        }
        self._save_result("pipeline_summary.json", summary)

    def run(self) -> bool:
        """Executa el pipeline complet."""
        console.print(Panel.fit(
            f"[bold]PIPELINE EDITORIAL: {self.title}[/bold]\n"
            f"Autor: {self.author}\n"
            f"Text: {len(self.text_traduit):,} caràcters",
            title="[yellow]Iniciant Pipeline[/yellow]"
        ))
        console.print()

        steps = [
            ("Corrector", self.run_corrector),
            ("Estil", self.run_estil),
            ("Glossarista", self.run_glossarista),
            ("Investigador", self.run_investigador),
            ("Edició Crítica", self.run_edicio_critica),
            ("Introducció", self.run_introduccio),
            ("Publicador EPUB", self.run_publicador),
        ]

        success = True
        for name, step_func in steps:
            console.print()
            result = step_func()
            if not result:
                console.print(f"[yellow]⚠ L'etapa {name} ha fallat, continuant...[/yellow]")
                # No aturem el pipeline, continuem amb la següent etapa

        self.print_summary()
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Editorial Complet per a textos clàssics"
    )
    parser.add_argument(
        "--input", "-i",
        default="output/symposium/EL_CONVIT_COMPLET.txt",
        help="Fitxer amb la traducció (default: output/symposium/EL_CONVIT_COMPLET.txt)"
    )
    parser.add_argument(
        "--original", "-o",
        default="data/originals/plato/symposium_greek.txt",
        help="Fitxer amb el text original grec"
    )
    parser.add_argument(
        "--output-dir", "-d",
        default="output/symposium/editorial",
        help="Directori de sortida"
    )
    parser.add_argument(
        "--author", "-a",
        default="Plató",
        help="Nom de l'autor"
    )
    parser.add_argument(
        "--title", "-t",
        default="El Convit",
        help="Títol de l'obra"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Mode silenciós"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mode verbós (default)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug"
    )

    args = parser.parse_args()

    # Determinar nivell de verbositat
    if args.debug:
        verbosity = VerbosityLevel.DEBUG
    elif args.quiet:
        verbosity = VerbosityLevel.QUIET
    else:
        verbosity = VerbosityLevel.VERBOSE

    # Verificar que existeix el fitxer d'entrada
    if not Path(args.input).exists():
        console.print(f"[red]Error: No es troba el fitxer {args.input}[/red]")
        sys.exit(1)

    # Verificar text original (opcional)
    original = args.original if Path(args.original).exists() else None
    if not original:
        console.print("[yellow]Avís: No es troba el text original, es generarà edició monolingüe[/yellow]")

    # Executar pipeline
    pipeline = EditorialPipeline(
        input_path=args.input,
        original_path=original,
        output_dir=args.output_dir,
        verbosity=verbosity,
        author=args.author,
        title=args.title
    )

    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
