#!/usr/bin/env python3
"""
Pipeline complet per traduir l'Enchiridion d'Epictetus (caps 1-5)
Executa: Chunker → Glossari → Traducció → Revisió → Correcció → Formatatge Web
"""

import json
from pathlib import Path
from datetime import datetime

from agents import (
    ChunkerAgent,
    ChunkingRequest,
    GlossaristaAgent,
    GlossaryRequest,
    TranslatorAgent,
    TranslationRequest,
    ReviewerAgent,
    ReviewRequest,
    CorrectorAgent,
    CorrectionRequest,
    FormatterAgent,
    FormattingRequest,
    WorkMetadata,
    Section,
    FormatterGlossaryEntry,
)
from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline
from utils.logger import VerbosityLevel, get_logger

def main():
    print("=" * 80)
    print("TRADUCCIÓ COMPLETA - Enchiridion d'Epictetus (Capítols 1-5)")
    print("=" * 80)
    print()

    # Llegir text grec
    text_path = Path("data/originals/epictetus/enchiridion_caps_1-5_grec.txt")
    text_grec = text_path.read_text(encoding="utf-8")

    print(f"📖 Text grec carregat: {len(text_grec)} caràcters")
    print()

    # Configurar pipeline
    config = PipelineConfig(
        enable_chunking=True,
        enable_glossary=True,
        enable_correction=True,
        correction_level="normal",
        max_tokens_per_chunk=1500,  # Petit per fer 1 chunk per capítol
        min_tokens_per_chunk=100,
        overlap_tokens=50,
        max_revision_rounds=2,
        min_quality_score=7.0,
        verbosity=VerbosityLevel.NORMAL,
        save_intermediate=True,
        output_dir=Path("output/epictetus"),
    )

    # Executar pipeline
    print("🔄 Executant pipeline de traducció...")
    print()

    pipeline = TranslationPipeline(config)

    result = pipeline.run(
        text=text_grec,
        source_language="grec",
        author="Epictetus",
        work_title="Enchiridion (Ἐγχειρίδιον)",
    )

    print()
    print("=" * 80)
    print("RESULTATS DEL PIPELINE")
    print("=" * 80)
    print(f"✅ Traducció completada!")
    print(f"   Chunks: {len(result.chunk_results)}")
    print(f"   Qualitat: {result.quality_score:.2f}/10" if result.quality_score else "   Qualitat: N/A")
    print(f"   Revisions: {result.revision_rounds}")
    print(f"   Tokens: {result.total_tokens:,}")
    print(f"   Cost: €{result.total_cost_eur:.4f}")
    print(f"   Temps: {result.total_duration_seconds:.1f}s")
    print()

    # Glossari generat
    if result.accumulated_context.glossary:
        print(f"📚 Glossari generat: {len(result.accumulated_context.glossary)} termes")
        for i, (term_key, entry) in enumerate(result.accumulated_context.glossary.items()):
            if i >= 5:
                print(f"   ... i {len(result.accumulated_context.glossary) - 5} més")
                break
            print(f"   - {entry.term_original} → {entry.term_translated}")
        print()

    # Preparar metadades per formatar
    print("📝 Formatant per web...")

    formatter = FormatterAgent()

    # Convertir glossari
    glossary_entries = []
    for term_key, entry in result.accumulated_context.glossary.items():
        glossary_entries.append(FormatterGlossaryEntry(
            term=entry.term_translated,
            original=entry.term_original,
            definition=entry.context or "Terme estoic fonamental.",
        ))

    # Crear metadades
    metadata = WorkMetadata(
        title="Enchiridion",
        author="Epictetus",
        original_author="Ἐπίκτητος (Epíktētos)",
        original_title="Ἐγχειρίδιον (Enkheirídion)",
        translator="Editorial Clàssica",
        source_language="grec",
        period="Època romana (s. II dC)",
        genre="Filosofia estoica",
        date=datetime.now().strftime("%Y-%m-%d"),
        status="revisat",
        quality_score=result.quality_score,
        revision_rounds=result.revision_rounds,
        total_cost_eur=result.total_cost_eur,
        tags=["filosofia", "estoïcisme", "ètica", "manual"],
    )

    # Crear seccions a partir dels chunks
    sections = []
    introduction = """L'*Enchiridion* (Ἐγχειρίδιον, "manual" o "llibret de mà") és una obra breu que recull els ensenyaments fonamentals d'Epictetus, filòsof estoic del segle II dC.

Compilat pel seu deixeble Arrià, aquest manual pràctic presenta els principis essencials de l'ètica estoica: la distinció entre el que depèn de nosaltres i el que no, l'acceptació serena del destí, i el control de les nostres opinions i desitjos.

Aquesta traducció presenta els primers cinc capítols, que estableixen les bases del pensament estoic."""

    for i, chunk_result in enumerate(result.chunk_results, 1):
        sections.append(Section(
            title=f"Capítol {i}",
            level=2,
            content=chunk_result.translated_text,
            type="capítol",
            themes=["estoïcisme", "ètica"],
        ))

    # Notes del traductor
    notes = [
        "**Ἐφ' ἡμῖν / οὐκ ἐφ' ἡμῖν**: Distinció fonamental estoica entre allò que depèn de nosaltres (les nostres opinions, desitjos, aversions) i allò que no (el cos, les possessions, la reputació).",
        "**Προαίρεσις** (prohaíresis): Terme clau que designa la capacitat de decisió racional, la voluntat o elecció moral.",
        "**Φαντασία** (phantasía): Impressió o representació mental. Els estoics distingeixen entre la impressió inicial i l'assentiment que li donem.",
    ]

    # Bibliografia
    bibliography = [
        "**Edicions crítiques**:",
        "- Schenkl, H. (1916). *Epicteti Dissertationes ab Arriano digestae*. Leipzig: Teubner.",
        "- Oldfather, W. A. (1925-1928). *Epictetus: The Discourses and Manual*, 2 vols. Harvard: Loeb Classical Library.",
        "",
        "**Traduccions de referència**:",
        "- Boter, G. (2007). *Epicteto: Disertaciones, Manual, Fragmentos*. Madrid: Gredos.",
        "- Hard, R. (1995). *The Discourses of Epictetus*. London: Everyman.",
        "",
        "**Estudis**:",
        "- Long, A. A. (2002). *Epictetus: A Stoic and Socratic Guide to Life*. Oxford: Clarendon Press.",
        "- Dobbin, R. (1998). *Epictetus: Discourses Book I*. Oxford: Clarendon Press.",
    ]

    # Formatar obra completa
    request = FormattingRequest(
        metadata=metadata,
        introduction=introduction,
        sections=sections,
        glossary=glossary_entries,
        translator_notes=notes,
        bibliography=bibliography,
        output_path=Path("obres/epictetus-enchiridion-caps1-5.md"),
    )

    markdown = formatter.format_work(request)

    print(f"✅ Markdown generat: obres/epictetus-enchiridion-caps1-5.md")
    print(f"   Mida: {len(markdown)} caràcters")
    print()

    # Mostrar fragment
    print("=" * 80)
    print("FRAGMENT DE LA TRADUCCIÓ")
    print("=" * 80)
    print()
    lines = result.final_translation.split('\n')[:15]
    for line in lines:
        print(line)
    print("...")
    print()

    print("=" * 80)
    print("✅ PIPELINE COMPLETAT!")
    print("=" * 80)
    print()
    print("Pròxims passos:")
    print("  1. Revisa: obres/epictetus-enchiridion-caps1-5.md")
    print("  2. Build web: python3 scripts/build.py --clean")
    print("  3. Serveix: bash scripts/serve.sh")
    print()

    # Guardar resum
    summary = {
        "obra": "Enchiridion d'Epictetus (capítols 1-5)",
        "autor": "Epictetus",
        "data": datetime.now().isoformat(),
        "chunks": len(result.chunk_results),
        "qualitat": result.quality_score,
        "revisions": result.revision_rounds,
        "tokens": result.total_tokens,
        "cost_eur": result.total_cost_eur,
        "temps_segons": result.total_duration_seconds,
        "glossari_termes": len(result.accumulated_context.glossary),
        "fitxer_markdown": "obres/epictetus-enchiridion-caps1-5.md",
    }

    summary_path = Path("output/epictetus/resum_traduccio.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"📊 Resum desat a: {summary_path}")
    print()

if __name__ == "__main__":
    main()
