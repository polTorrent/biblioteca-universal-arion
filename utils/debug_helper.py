"""Helper per debug ràpid des de qualsevol lloc.

Proporciona funcions d'accés ràpid al sistema de debugging TDD.

Ús:
    >>> from utils.debug_helper import debug_rapido
    >>> debug_rapido("El validador no detecta errors de format")
"""

import os
from pathlib import Path

# Assegurar mode subscripció
os.environ.setdefault("CLAUDECODE", "1")


def debug_rapido(descripcio: str, fitxers: list[str] | None = None) -> bool:
    """
    Helper per debug ràpid.

    Executa el flux complet de debugging: reproduir + arreglar.

    Args:
        descripcio: Descripció del bug a investigar.
        fitxers: Llista de fitxers relacionats amb el bug.

    Returns:
        True si s'ha resolt, False si no.

    Example:
        >>> from utils.debug_helper import debug_rapido
        >>> debug_rapido("El validador no detecta errors de format")
        True
    """
    from agents.debug import DebugOrchestrator

    orchestrator = DebugOrchestrator(verbose=True)
    result = orchestrator.debug(
        descripcio=descripcio,
        fitxers_context=fitxers,
    )

    return result.exit


def debug_fitxer(fitxer: str, descripcio: str = "Bug detectat") -> bool:
    """
    Debug centrat en un fitxer específic.

    Args:
        fitxer: Camí al fitxer amb el bug.
        descripcio: Descripció del bug (opcional).

    Returns:
        True si s'ha resolt, False si no.

    Example:
        >>> from utils.debug_helper import debug_fitxer
        >>> debug_fitxer("agents/cost.py", "Error amb decimals")
        True
    """
    return debug_rapido(descripcio, fitxers=[fitxer])


def reproduir_nomes(descripcio: str, fitxers: list[str] | None = None) -> "BugReport | None":
    """
    Només reprodueix el bug sense intentar arreglar-lo.

    Útil per crear tests de regressió o analitzar bugs.

    Args:
        descripcio: Descripció del bug.
        fitxers: Fitxers relacionats.

    Returns:
        BugReport amb el test que falla, o None si no s'ha pogut reproduir.

    Example:
        >>> from utils.debug_helper import reproduir_nomes
        >>> report = reproduir_nomes("Error amb textos buits")
        >>> if report:
        ...     print(f"Test guardat a: {report.test_file}")
    """
    from agents.debug import DebugOrchestrator

    orchestrator = DebugOrchestrator(verbose=True)
    result = orchestrator.debug(
        descripcio=descripcio,
        fitxers_context=fitxers,
        dry_run=True,
    )

    return result.bug_report


def debug_amb_commit(descripcio: str, fitxers: list[str] | None = None) -> bool:
    """
    Debug amb auto-commit si el fix és exitós.

    Args:
        descripcio: Descripció del bug.
        fitxers: Fitxers relacionats.

    Returns:
        True si s'ha resolt i fet commit, False si no.

    Example:
        >>> from utils.debug_helper import debug_amb_commit
        >>> debug_amb_commit("Bug a la funció X", ["src/utils.py"])
        True
    """
    from agents.debug import DebugOrchestrator

    orchestrator = DebugOrchestrator(verbose=True)
    result = orchestrator.debug(
        descripcio=descripcio,
        fitxers_context=fitxers,
        auto_commit=True,
    )

    return result.exit


# Aliases per comoditat
debug = debug_rapido
fix_bug = debug_rapido
