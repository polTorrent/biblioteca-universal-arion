"""Agents v2 - Sistema de traducció millorat amb avaluació dimensional."""

from agents.v2.models import (
    # Models d'anàlisi pre-traducció
    AnalisiPreTraduccio,
    ParaulaClau,
    RecursLiterari,
    RepteTraduccio,
    ContextTraduccioEnriquit,
    # Models d'avaluació
    AvaluacioFidelitat,
    AvaluacioVeuAutor,
    AvaluacioFluidesa,
    FeedbackFusionat,
    ProblemaFidelitat,
    ContextAvaluacio,
    LlindarsAvaluacio,
)
from agents.v2.avaluador_dimensional import (
    AvaluadorDimensional,
    AvaluadorFidelitat,
    AvaluadorVeuAutor,
    AvaluadorFluidesa,
    FusionadorFeedback,
)
from agents.v2.analitzador_pre import (
    AnalitzadorPreTraduccio,
    SelectorExemplesFewShot,
)
from agents.v2.traductor_enriquit import (
    TraductorEnriquit,
    TraductorAmbAnalisi,
    ResultatTraduccio,
)
from agents.v2.refinador_iteratiu import (
    RefinadorIteratiu,
    AgentRefinador,
    RefinadorPerDimensio,
    ResultatRefinament,
    IteracioRefinament,
)
from agents.v2.pipeline_v2 import (
    PipelineV2,
    ConfiguracioPipelineV2,
    ResultatPipelineV2,
    ResultatChunk,
    EstatPipeline,
)

__all__ = [
    # Models anàlisi pre-traducció
    "AnalisiPreTraduccio",
    "ParaulaClau",
    "RecursLiterari",
    "RepteTraduccio",
    "ContextTraduccioEnriquit",
    # Models avaluació
    "AvaluacioFidelitat",
    "AvaluacioVeuAutor",
    "AvaluacioFluidesa",
    "FeedbackFusionat",
    "ProblemaFidelitat",
    "ContextAvaluacio",
    "LlindarsAvaluacio",
    # Agents
    "AnalitzadorPreTraduccio",
    "SelectorExemplesFewShot",
    "TraductorEnriquit",
    "TraductorAmbAnalisi",
    "ResultatTraduccio",
    "AvaluadorDimensional",
    "AvaluadorFidelitat",
    "AvaluadorVeuAutor",
    "AvaluadorFluidesa",
    "FusionadorFeedback",
    "RefinadorIteratiu",
    "AgentRefinador",
    "RefinadorPerDimensio",
    "ResultatRefinament",
    "IteracioRefinament",
    # Pipeline
    "PipelineV2",
    "ConfiguracioPipelineV2",
    "ResultatPipelineV2",
    "ResultatChunk",
    "EstatPipeline",
]
