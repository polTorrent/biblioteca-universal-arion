"""Exemple complet d'ús del pipeline integrat amb tots els agents.

Aquest script mostra com utilitzar el pipeline de traducció amb:
- ChunkerAgent
- GlossaristaAgent
- TranslatorAgent
- ReviewerAgent
- CorrectorAgent
"""

from pathlib import Path
from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline
from utils.logger import VerbosityLevel


def traduir_banquet_plato():
    """Exemple: traduir un fragment del Banquet de Plató."""

    # Text original en grec (inici del Banquet)
    text_grec = """
ΑΠΟΛΛΟΔΩΡΟΣ. Δοκῶ μοι περὶ ὧν πυνθάνεσθε οὐκ ἀμελέτητος εἶναι.
καὶ γὰρ ἐτύγχανον πρῴην εἰς ἄστυ οἴκοθεν ἀνιὼν Φαληρόθεν,
τῶν ἐπιτηδείων τις ὄπισθεν κατιδών με πόρρωθεν ἐκάλεσέ τε
παίζων καί, Φαληρεύς, ἔφη, οὗτος, ὦ Ἀπολλόδωρε, οὐ περιμένεις;

κἀγὼ ἐπιστὰς ἔμεινα. ὁ δέ, Ἀπολλόδωρε, ἔφη, καὶ μέντοι ἄρτι
καὶ ἐζήτουν σε, βουλόμενος διαπυθέσθαι τὴν Ἀγάθωνος καὶ Σωκράτους
καὶ Ἀλκιβιάδου καὶ τῶν ἄλλων τῶν τότε ἐν τῷ δείπνῳ ὄντων περὶ
τῶν ἐρωτικῶν λόγων οἷοι ἦσαν. ἄλλος γάρ τίς μοι διηγεῖτο ἀκηκοὼς
Φοίνικος τοῦ Φιλίππου· ἔφη δὲ καὶ σὲ εἰδέναι.

ἀλλ᾽ οὐδὲν ἦν ὅτι ἐλέγετο σαφές. διήγησαι οὖν μοι σύ· σοὶ γὰρ
καὶ δικαιότατον τοὺς τοῦ ἑταίρου λόγους ἀπαγγέλλειν. πρῶτον δὲ
μοι λέγε, ἔφη, αὐτὸς παρεγένου ταύτῃ τῇ συνουσίᾳ ἢ οὔ;
"""

    # Configuració del pipeline
    config = PipelineConfig(
        # Activar/desactivar agents
        enable_chunking=True,       # Dividir el text en fragments
        enable_glossary=True,       # Crear glossari terminològic
        enable_correction=True,     # Corregir ortografia/gramàtica

        # Paràmetres de chunking
        max_tokens_per_chunk=2000,  # Mida màxima per chunk
        min_tokens_per_chunk=400,   # Mida mínima per chunk
        overlap_tokens=100,         # Solapament entre chunks

        # Paràmetres de revisió
        max_revision_rounds=2,      # Rondes màximes de revisió
        min_quality_score=7.0,      # Puntuació mínima acceptable

        # Correcció
        correction_level="normal",  # relaxat | normal | estricte

        # Gestió de costos
        cost_limit_eur=2.0,         # Límit de cost (None = sense límit)

        # Sortida i visualització
        output_dir=Path("output/banquet"),
        save_intermediate=True,
        verbosity=VerbosityLevel.NORMAL,
        use_dashboard=False,
    )

    print("=" * 80)
    print("TRADUCCIÓ DEL BANQUET DE PLATÓ")
    print("=" * 80)
    print(f"\nConfiguració:")
    print(f"  - Glossari: {'✅' if config.enable_glossary else '❌'}")
    print(f"  - Correcció: {'✅' if config.enable_correction else '❌'} ({config.correction_level})")
    print(f"  - Chunking: {'✅' if config.enable_chunking else '❌'}")
    print(f"  - Limit de cost: €{config.cost_limit_eur}")
    print()

    # Crear i executar pipeline
    pipeline = TranslationPipeline(config)

    result = pipeline.run(
        text=text_grec,
        source_language="grec",
        author="Plató",
        work_title="El Banquet (Συμπόσιον)",
    )

    # Mostrar resultats
    pipeline.display_result(result)

    # Estadístiques detallades
    print("\n" + "=" * 80)
    print("ESTADÍSTIQUES DETALLADES")
    print("=" * 80)

    print(f"\n📊 Processament:")
    print(f"   - Chunks: {len(result.chunk_results)}")
    print(f"   - Etapes: {len(result.stages)}")
    print(f"   - Revisions: {result.revision_rounds}")

    print(f"\n💰 Costos:")
    print(f"   - Tokens: {result.total_tokens:,}")
    print(f"   - Cost: €{result.total_cost_eur:.4f}")
    if result.chunk_results:
        avg_cost = result.total_cost_eur / len(result.chunk_results)
        print(f"   - Cost/chunk: €{avg_cost:.4f}")

    print(f"\n⏱️  Temps:")
    print(f"   - Durada: {result.total_duration_seconds:.1f}s")
    if result.chunk_results:
        avg_time = result.total_duration_seconds / len(result.chunk_results)
        print(f"   - Temps/chunk: {avg_time:.1f}s")

    print(f"\n✨ Qualitat:")
    print(f"   - Puntuació: {result.quality_score:.2f}/10" if result.quality_score else "   - Puntuació: N/A")

    # Mostrar glossari generat
    if result.accumulated_context.glossary:
        print(f"\n📚 Glossari generat ({len(result.accumulated_context.glossary)} termes):")
        for i, (term_key, entry) in enumerate(result.accumulated_context.glossary.items()):
            if i >= 10:  # Mostrar només primers 10
                print(f"   ... i {len(result.accumulated_context.glossary) - 10} més")
                break
            print(f"   - {entry.term_original} → {entry.term_translated}")

    # Mostrar correccions aplicades
    total_corrections = sum(
        cr.metadata.get("corrections_count", 0)
        for cr in result.chunk_results
    )
    if total_corrections > 0:
        print(f"\n✏️  Correccions aplicades: {total_corrections}")
        for cr in result.chunk_results:
            corrections = cr.metadata.get("corrections", [])
            if corrections:
                print(f"\n   Chunk {cr.chunk_id}:")
                for corr in corrections[:3]:  # Només primeres 3
                    print(f"      - {corr.get('tipus', '?')}: {corr.get('original', '')} → {corr.get('corregit', '')}")

    # Guardar traducció final
    output_file = config.output_dir / "traduccio_final.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(result.final_translation, encoding="utf-8")
    print(f"\n💾 Traducció guardada a: {output_file}")

    print("\n✅ Procés completat!")


def exemple_configuracions():
    """Mostra diferents configuracions possibles del pipeline."""

    print("\n" + "=" * 80)
    print("EXEMPLES DE CONFIGURACIONS")
    print("=" * 80)

    # 1. Configuració ràpida i econòmica
    print("\n1️⃣  Configuració RÀPIDA (sense glossari ni correcció)")
    config_rapida = PipelineConfig(
        enable_glossary=False,
        enable_correction=False,
        max_revision_rounds=1,
        verbosity=VerbosityLevel.QUIET,
    )
    print(f"   Cost estimat: ~50% menys")

    # 2. Configuració de qualitat màxima
    print("\n2️⃣  Configuració QUALITAT MÀXIMA")
    config_qualitat = PipelineConfig(
        enable_glossary=True,
        enable_correction=True,
        correction_level="estricte",
        max_revision_rounds=3,
        min_quality_score=8.5,
        verbosity=VerbosityLevel.VERBOSE,
    )
    print(f"   Cost estimat: ~150% més, però traducció excel·lent")

    # 3. Configuració equilibrada (recomanada)
    print("\n3️⃣  Configuració EQUILIBRADA (recomanada)")
    config_equilibrada = PipelineConfig(
        enable_glossary=True,
        enable_correction=True,
        correction_level="normal",
        max_revision_rounds=2,
        min_quality_score=7.0,
        cost_limit_eur=5.0,
    )
    print(f"   Bona relació qualitat/preu")

    # 4. Configuració per textos molt llargs
    print("\n4️⃣  Configuració TEXTOS LLARGS")
    config_llargs = PipelineConfig(
        enable_chunking=True,
        max_tokens_per_chunk=4000,
        min_tokens_per_chunk=1000,
        enable_glossary=True,  # Important per consistència
        enable_correction=False,  # Estalviar cost
        max_revision_rounds=1,
        cost_limit_eur=20.0,
    )
    print(f"   Optimitzat per llibres complets")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "configs":
        exemple_configuracions()
    else:
        traduir_banquet_plato()
