"""Test del pipeline integrat amb tots els agents."""

from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline
from utils.logger import VerbosityLevel

# Text de prova del Banquet de Plató
TEST_TEXT = """
ΑΠΟΛΛΟΔΩΡΟΣ. Δοκῶ μοι περὶ ὧν πυνθάνεσθε οὐκ ἀμελέτητος εἶναι.
καὶ γὰρ ἐτύγχανον πρῴην εἰς ἄστυ οἴκοθεν ἀνιὼν Φαληρόθεν,
τῶν ἐπιτηδείων τις ὄπισθεν κατιδών με πόρρωθεν ἐκάλεσέ τε
παίζων καί, Φαληρεύς, ἔφη, οὗτος, ὦ Ἀπολλόδωρε, οὐ περιμένεις;
"""


def test_pipeline_simple():
    """Test del pipeline amb text curt (sense chunking)."""
    print("=" * 80)
    print("TEST 1: Pipeline amb text curt (sense chunking)")
    print("=" * 80)

    config = PipelineConfig(
        enable_chunking=False,
        enable_glossary=False,
        enable_correction=True,
        correction_level="normal",
        max_revision_rounds=1,
        verbosity=VerbosityLevel.NORMAL,
        save_intermediate=True,
    )

    pipeline = TranslationPipeline(config)

    result = pipeline.run(
        text=TEST_TEXT,
        source_language="grec",
        author="Plató",
        work_title="El Banquet",
    )

    pipeline.display_result(result)

    print("\n✅ Test completat!")
    print(f"Puntuació: {result.quality_score}/10")
    print(f"Cost: €{result.total_cost_eur:.4f}")
    print(f"Tokens: {result.total_tokens:,}")
    print(f"Durada: {result.total_duration_seconds:.1f}s")
    print(f"Etapes: {len(result.stages)}")


def test_pipeline_chunked():
    """Test del pipeline amb chunking i tots els agents."""
    print("\n" + "=" * 80)
    print("TEST 2: Pipeline amb chunking i tots els agents")
    print("=" * 80)

    # Text més llarg per forçar chunking
    long_text = TEST_TEXT * 20

    config = PipelineConfig(
        enable_chunking=True,
        enable_glossary=True,
        enable_correction=True,
        correction_level="normal",
        max_tokens_per_chunk=1500,
        min_tokens_per_chunk=300,
        overlap_tokens=50,
        max_revision_rounds=1,
        verbosity=VerbosityLevel.VERBOSE,
        save_intermediate=True,
        use_dashboard=False,
    )

    pipeline = TranslationPipeline(config)

    result = pipeline.run(
        text=long_text,
        source_language="grec",
        author="Plató",
        work_title="El Banquet",
    )

    pipeline.display_result(result)

    print("\n✅ Test completat!")
    print(f"Chunks processats: {len(result.chunk_results)}")
    print(f"Puntuació mitjana: {result.quality_score}/10")
    print(f"Cost total: €{result.total_cost_eur:.4f}")
    print(f"Tokens: {result.total_tokens:,}")
    print(f"Durada: {result.total_duration_seconds:.1f}s")

    # Mostrar informació del glossari
    if result.accumulated_context.glossary:
        print(f"\nGlossari: {len(result.accumulated_context.glossary)} termes")
        for term_key, entry in list(result.accumulated_context.glossary.items())[:5]:
            print(f"  - {entry.term_original} → {entry.term_translated}")


def test_agents_individually():
    """Test individual de cada agent."""
    print("\n" + "=" * 80)
    print("TEST 3: Agents individuals")
    print("=" * 80)

    from agents import (
        ChunkerAgent,
        ChunkingRequest,
        TranslatorAgent,
        TranslationRequest,
        ReviewerAgent,
        ReviewRequest,
        CorrectorAgent,
        CorrectionRequest,
        GlossaristaAgent,
        GlossaryRequest,
    )

    # 1. ChunkerAgent
    print("\n1️⃣ ChunkerAgent")
    chunker = ChunkerAgent()
    chunking_result = chunker.chunk(
        ChunkingRequest(
            text=TEST_TEXT,
            max_tokens=500,
            source_language="grec",
        )
    )
    print(f"   ✅ {chunking_result.total_chunks} chunks creats")

    # 2. GlossaristaAgent
    print("\n2️⃣ GlossaristaAgent")
    glossarist = GlossaristaAgent()
    glossary_response = glossarist.create_glossary(
        GlossaryRequest(
            text="",
            text_original=TEST_TEXT,
            llengua_original="grec",
        )
    )
    print(f"   ✅ Glossari generat ({len(glossary_response.content)} caràcters)")

    # 3. TranslatorAgent
    print("\n3️⃣ TranslatorAgent")
    translator = TranslatorAgent()
    translation_response = translator.translate(
        TranslationRequest(
            text=TEST_TEXT[:500],
            source_language="grec",
            author="Plató",
        )
    )
    print(f"   ✅ Traducció: {translation_response.content[:100]}...")

    # 4. ReviewerAgent
    print("\n4️⃣ ReviewerAgent")
    reviewer = ReviewerAgent()
    review_response = reviewer.review(
        ReviewRequest(
            original_text=TEST_TEXT[:500],
            translated_text=translation_response.content,
            source_language="grec",
        )
    )
    print(f"   ✅ Revisió completada")

    # 5. CorrectorAgent
    print("\n5️⃣ CorrectorAgent")
    corrector = CorrectorAgent()
    correction_response = corrector.correct(
        CorrectionRequest(
            text=translation_response.content,
            nivell="normal",
        )
    )
    print(f"   ✅ Correcció completada")

    print("\n✅ Tots els agents funcionen correctament!")


if __name__ == "__main__":
    import sys

    # Afegir opcions de test
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "simple":
            test_pipeline_simple()
        elif test_type == "chunked":
            test_pipeline_chunked()
        elif test_type == "agents":
            test_agents_individually()
        else:
            print("ús: python test_integrated_pipeline.py [simple|chunked|agents]")
    else:
        # Executar tots els tests
        test_agents_individually()
        test_pipeline_simple()
        # test_pipeline_chunked()  # Comentat perquè és llarg i costós
