#!/usr/bin/env python3
"""Script de prova per verificar el funcionament del TranslatorAgent."""

from rich.console import Console
from rich.panel import Panel

from agents import TranslatorAgent, TranslationRequest

console = Console()


def main() -> None:
    console.print("\n[bold blue]Test del TranslatorAgent[/bold blue]\n")

    agent = TranslatorAgent(source_language="llatí")

    # Frase de prova: inici de "De Bello Gallico" de Juli Cèsar
    request = TranslationRequest(
        text="Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae, aliam Aquitani, tertiam qui ipsorum lingua Celtae, nostra Galli appellantur.",
        source_language="llatí",
        author="Juli Cèsar",
        work_title="De Bello Gallico",
    )

    console.print(Panel(request.text, title="Text original (llatí)", border_style="yellow"))

    console.print("\n[dim]Traduint...[/dim]\n")
    response = agent.translate(request)

    console.print(Panel(response.content, title="Traducció (català)", border_style="green"))

    console.print(f"\n[dim]Model: {response.model}[/dim]")
    console.print(f"[dim]Tokens: {response.usage['input_tokens']} entrada / {response.usage['output_tokens']} sortida[/dim]\n")


if __name__ == "__main__":
    main()
