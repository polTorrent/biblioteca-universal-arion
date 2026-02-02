#!/usr/bin/env python3
"""Script de diagnòstic del pipeline de traducció.

Verifica dependències, autenticació, checkpoints i mètriques
per assegurar que el pipeline està correctament configurat.

Ús:
    python scripts/diagnosticar_pipeline.py
"""

import sys
from pathlib import Path

# Afegir el directori arrel al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Fallback si rich no està disponible
class SimplePrinter:
    """Printer simple si rich no està disponible."""

    def print(self, text="", **kwargs):
        # Eliminar estils de rich
        import re
        clean_text = re.sub(r'\[/?[^\]]+\]', '', str(text))
        print(clean_text)


console = Console() if RICH_AVAILABLE else SimplePrinter()


def verificar_dependencies() -> bool:
    """Verifica que totes les dependències estan instal·lades."""
    console.print("\n[bold]1. Verificant dependències...[/bold]")

    dependencies = [
        ("anthropic", "API de Claude"),
        ("pydantic", "Validació de dades"),
        ("rich", "Output formatat"),
        ("tenacity", "Retry logic"),
        ("httpx", "Client HTTP"),
        ("dotenv", "Variables d'entorn"),
    ]

    all_ok = True
    for module, desc in dependencies:
        try:
            if module == "dotenv":
                __import__("dotenv")
            else:
                __import__(module)
            console.print(f"  ✅ {module} ({desc})")
        except ImportError:
            console.print(f"  ❌ {module} ({desc}) - NO INSTAL·LAT")
            all_ok = False

    return all_ok


def verificar_autenticacio() -> bool:
    """Verifica l'autenticació amb Claude."""
    console.print("\n[bold]2. Verificant autenticació...[/bold]")

    import subprocess

    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout.lower() + result.stderr.lower()

        if "subscription" in output or "authenticated" in output:
            console.print("  ✅ Autenticat via subscripció Claude")
            return True
        elif "api" in output:
            console.print("  ⚠️ Autenticat via API key (pot generar costos)")
            return True
        elif result.returncode != 0:
            console.print(f"  ❌ Error verificant autenticació")
            console.print(f"     Output: {result.stderr or result.stdout}")
            return False
        else:
            console.print("  ⚠️ Estat d'autenticació desconegut")
            console.print(f"     Output: {result.stdout}")
            return True

    except FileNotFoundError:
        console.print("  ❌ CLI de Claude no trobat")
        console.print("     Instal·la: npm install -g @anthropic-ai/claude-code")
        return False
    except subprocess.TimeoutExpired:
        console.print("  ⚠️ Timeout verificant autenticació")
        return False
    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        return False


def verificar_estructura() -> bool:
    """Verifica l'estructura del projecte."""
    console.print("\n[bold]3. Estructura del projecte...[/bold]")

    directoris_requerits = [
        ("agents", "Agents de traducció"),
        ("utils", "Utilitats"),
        ("obres", "Directori d'obres"),
    ]

    directoris_opcionals = [
        (".cache", "Cache del sistema"),
        ("dashboard", "Dashboard de monitorització"),
        ("core", "Mòduls core"),
    ]

    fitxers_requerits = [
        ("agents/base_agent.py", "Agent base"),
        ("utils/checkpointer.py", "Sistema de checkpoints"),
        ("utils/logger.py", "Sistema de logging"),
        ("utils/validators.py", "Validadors"),
        ("utils/metrics.py", "Sistema de mètriques"),
    ]

    all_ok = True

    # Directoris requerits
    for d, desc in directoris_requerits:
        if Path(d).exists():
            console.print(f"  ✅ {d}/ ({desc})")
        else:
            console.print(f"  ❌ {d}/ ({desc}) - NO EXISTEIX")
            all_ok = False

    # Directoris opcionals
    for d, desc in directoris_opcionals:
        if Path(d).exists():
            console.print(f"  ✅ {d}/ ({desc})")
        else:
            console.print(f"  ℹ️ {d}/ ({desc}) - Opcional, no existeix")

    # Fitxers requerits
    console.print("")
    for f, desc in fitxers_requerits:
        if Path(f).exists():
            console.print(f"  ✅ {f}")
        else:
            console.print(f"  ❌ {f} - NO EXISTEIX")
            all_ok = False

    return all_ok


def verificar_checkpoints() -> None:
    """Mostra l'estat dels checkpoints."""
    console.print("\n[bold]4. Checkpoints guardats...[/bold]")

    try:
        from utils.checkpointer import Checkpointer

        checkpointer = Checkpointer()

        # Usar el mètode nou si existeix
        if hasattr(checkpointer, 'llistar_sessions_detallat'):
            sessions = checkpointer.llistar_sessions_detallat()
        else:
            sessions = [{"sessio_id": s} for s in checkpointer.llistar_sessions()]

        if not sessions:
            console.print("  ℹ️ No hi ha sessions guardades")
            return

        if RICH_AVAILABLE:
            table = Table(title="Sessions")
            table.add_column("ID", style="cyan", max_width=20)
            table.add_column("Obra", max_width=25)
            table.add_column("Fase", max_width=15)
            table.add_column("Progrés", justify="center")
            table.add_column("Qualitat", justify="center")

            for s in sessions[:10]:  # Màxim 10
                if "error" in s:
                    table.add_row(s["sessio_id"], "[red]CORRUPTE[/red]", "-", "-", "-")
                else:
                    progres = f"{s.get('chunks_completats', '?')}/{s.get('chunks_total', '?')}"
                    obra = f"{s.get('autor', '?')} - {s.get('obra', '?')}"[:25]
                    qualitat = f"{s.get('qualitat_mitjana', 0):.1f}" if s.get('qualitat_mitjana') else "N/A"
                    table.add_row(
                        s["sessio_id"][:20],
                        obra,
                        s.get("fase", "?"),
                        progres,
                        qualitat,
                    )

            console.print(table)
        else:
            for s in sessions[:10]:
                if "error" in s:
                    console.print(f"  ❌ {s['sessio_id']}: CORRUPTE")
                else:
                    progres = f"{s.get('chunks_completats', '?')}/{s.get('chunks_total', '?')}"
                    console.print(f"  • {s['sessio_id']}: {s.get('fase', '?')} ({progres})")

    except ImportError:
        console.print("  ⚠️ No s'ha pogut importar Checkpointer")
    except Exception as e:
        console.print(f"  ⚠️ Error llegint checkpoints: {e}")


def verificar_metriques() -> None:
    """Mostra resum de mètriques."""
    console.print("\n[bold]5. Mètriques...[/bold]")

    try:
        from utils.metrics import MetricsCollector

        collector = MetricsCollector()
        metriques = collector.carregar_totes()

        if not metriques:
            console.print("  ℹ️ No hi ha mètriques guardades")
            return

        # Mostrar resum
        total_sessions = len(metriques)
        total_chunks = sum(m.get("chunks_processats", 0) for m in metriques)
        qualitats = [m["qualitat_mitjana"] for m in metriques if m.get("qualitat_mitjana")]

        console.print(f"  Sessions: {total_sessions}")
        console.print(f"  Chunks processats: {total_chunks}")
        if qualitats:
            console.print(f"  Qualitat mitjana: {sum(qualitats)/len(qualitats):.2f}/10")

    except ImportError:
        console.print("  ℹ️ Sistema de mètriques no disponible")
    except Exception as e:
        console.print(f"  ⚠️ Error llegint mètriques: {e}")


def verificar_agents() -> bool:
    """Verifica que els agents es poden importar."""
    console.print("\n[bold]6. Agents...[/bold]")

    agents = [
        ("agents.base_agent", "BaseAgent", "Agent base"),
        ("agents.v2.pipeline_v2", "PipelineV2", "Pipeline V2"),
        ("agents.glossarista", "GlossaristaAgent", "Glossarista"),
        ("agents.chunker_agent", "ChunkerAgent", "Chunker"),
    ]

    all_ok = True
    for module, class_name, desc in agents:
        try:
            mod = __import__(module, fromlist=[class_name])
            getattr(mod, class_name)
            console.print(f"  ✅ {desc}")
        except ImportError as e:
            console.print(f"  ⚠️ {desc} - No disponible ({e})")
        except AttributeError:
            console.print(f"  ❌ {desc} - Classe no trobada")
            all_ok = False
        except Exception as e:
            console.print(f"  ❌ {desc} - Error: {e}")
            all_ok = False

    return all_ok


def verificar_variables_entorn() -> None:
    """Verifica variables d'entorn importants."""
    console.print("\n[bold]7. Variables d'entorn...[/bold]")

    import os

    variables = [
        ("CLAUDECODE", "Mode Claude Code (subscripció)"),
        ("ANTHROPIC_API_KEY", "API Key d'Anthropic"),
    ]

    for var, desc in variables:
        value = os.getenv(var)
        if value:
            if "KEY" in var or "SECRET" in var:
                # No mostrar valors sensibles
                console.print(f"  ✅ {var}: [CONFIGURAT]")
            else:
                console.print(f"  ✅ {var}: {value}")
        else:
            console.print(f"  ℹ️ {var}: No configurat ({desc})")


def main():
    """Funció principal de diagnòstic."""
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold blue]🔍 Diagnòstic del Pipeline de Traducció[/bold blue]",
            border_style="blue",
        ))
    else:
        console.print("=" * 50)
        console.print("  🔍 Diagnòstic del Pipeline de Traducció")
        console.print("=" * 50)

    resultats = {
        "dependencies": verificar_dependencies(),
        "autenticacio": verificar_autenticacio(),
        "estructura": verificar_estructura(),
        "agents": verificar_agents(),
    }

    verificar_checkpoints()
    verificar_metriques()
    verificar_variables_entorn()

    # Resum final
    console.print("\n" + "═" * 50)
    if all(resultats.values()):
        console.print("[bold green]✅ Tot correcte! El pipeline està llest.[/bold green]")
    else:
        console.print("[bold red]❌ Hi ha problemes a resoldre:[/bold red]")
        for nom, ok in resultats.items():
            if not ok:
                console.print(f"   • {nom}")

        console.print("\n[yellow]Suggeriments:[/yellow]")
        if not resultats.get("dependencies"):
            console.print("   pip install -e .")
        if not resultats.get("autenticacio"):
            console.print("   claude auth login")
        if not resultats.get("estructura"):
            console.print("   Verifica que estàs al directori correcte del projecte")

    console.print("═" * 50)

    return 0 if all(resultats.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
