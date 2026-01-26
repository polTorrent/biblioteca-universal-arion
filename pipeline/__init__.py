# Pipeline de processament editorial
from pipeline.translation_pipeline import (
    AccumulatedContext,
    ChunkResult,
    GlossaryEntry,
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    PipelineState,
    StageResult,
    TranslationPipeline,
)
from pipeline.portada_integration import (
    PortadaIntegration,
    afegir_portada_a_resultat,
    detectar_genere,
)

__all__ = [
    "AccumulatedContext",
    "ChunkResult",
    "GlossaryEntry",
    "PipelineConfig",
    "PipelineResult",
    "PipelineStage",
    "PipelineState",
    "StageResult",
    "TranslationPipeline",
    "PortadaIntegration",
    "afegir_portada_a_resultat",
    "detectar_genere",
]
