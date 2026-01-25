#!/usr/bin/env python3
"""Script de prova per verificar el funcionament del pipeline complet."""

from pipeline import PipelineConfig, TranslationPipeline


def main() -> None:
    # Configuració del pipeline
    config = PipelineConfig(
        max_revision_rounds=2,
        min_quality_score=7.0,
        save_intermediate=True,
    )

    pipeline = TranslationPipeline(config)

    # Text de prova: inici de "De Bello Gallico" de Juli Cèsar
    text = """Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae,
aliam Aquitani, tertiam qui ipsorum lingua Celtae, nostra Galli appellantur.
Hi omnes lingua, institutis, legibus inter se differunt."""

    # Executar el pipeline
    result = pipeline.run(
        text=text,
        source_language="llatí",
        author="Juli Cèsar",
        work_title="De Bello Gallico",
    )

    # Mostrar resultats
    pipeline.display_result(result)


if __name__ == "__main__":
    main()
