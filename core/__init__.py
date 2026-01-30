# core/__init__.py
"""Mòdul core per a la gestió d'estat i memòria del pipeline."""

from core.estat_pipeline import EstatPipeline
from core.memoria_contextual import (
    MemoriaContextual,
    ContextInvestigacio,
    TraduccioRegistrada,
    Personatge,
    DecisioEstil,
)
from core.validador_final import (
    ValidadorFinal,
    ResultatValidacio,
    ItemValidacio,
)

__all__ = [
    # Estat
    "EstatPipeline",
    # Memòria
    "MemoriaContextual",
    "ContextInvestigacio",
    "TraduccioRegistrada",
    "Personatge",
    "DecisioEstil",
    # Validador
    "ValidadorFinal",
    "ResultatValidacio",
    "ItemValidacio",
]
