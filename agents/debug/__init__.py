"""Mòdul d'agents per debugging amb arquitectura TDD.

Proporciona un sistema de dos agents especialitzats per detectar
i arreglar bugs de forma sistemàtica:

- BugReproducerAgent: Analitza bugs i crea tests que fallen
- BugFixerAgent: Arregla codi fins que els tests passin
- DebugOrchestrator: Coordina el flux complet

Ús bàsic:
    >>> from agents.debug import DebugOrchestrator
    >>> orchestrator = DebugOrchestrator()
    >>> result = orchestrator.debug(
    ...     descripcio="La funció retorna None amb entrada buida",
    ...     fitxers_context=["src/utils.py"]
    ... )
    >>> print(result.resum())

CLI:
    python -m agents.debug "descripció del bug" --files fitxer.py --verbose
"""

from agents.debug.bug_fixer import BugFixerAgent
from agents.debug.bug_reproducer import BugReproducerAgent
from agents.debug.debug_orchestrator import DebugOrchestrator
from agents.debug.models import BugFix, BugReport, DebugResult

__all__ = [
    "BugReproducerAgent",
    "BugFixerAgent",
    "DebugOrchestrator",
    "BugReport",
    "BugFix",
    "DebugResult",
]
