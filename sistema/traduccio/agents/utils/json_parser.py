"""Utilitats per a parsing JSON robust amb fallbacks consistents.

Proporciona funcions d'extracció segures que:
- Mai llancen excepcions
- Retornen valors per defecte consistents
- Opcionalment loguejen errors per diagnòstic
"""

from typing import Any, Callable

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS DE FALLBACK
# Valors estàndard per quan el parsing falla
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_PUNTUACIO = 7.0  # Puntuació neutra (ni aprovat ni suspès clar)
DEFAULT_CONFIANCA = 0.5  # Confiança mitjana
DEFAULT_FALLBACK_TEXT = ""


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONS D'EXTRACCIÓ SEGURES
# ═══════════════════════════════════════════════════════════════════════════════

def safe_float(
    data: dict[str, Any] | None,
    key: str,
    default: float = DEFAULT_PUNTUACIO,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float:
    """Extreu un float de forma segura.

    Args:
        data: Diccionari amb les dades.
        key: Clau a buscar.
        default: Valor per defecte si no es troba o és invàlid.
        min_val: Valor mínim permès (opcional).
        max_val: Valor màxim permès (opcional).

    Returns:
        Float extret o valor per defecte.
    """
    if data is None:
        return default

    value = data.get(key)
    if value is None:
        return default

    try:
        result = float(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except (ValueError, TypeError):
        return default


def safe_int(
    data: dict[str, Any] | None,
    key: str,
    default: int = 0,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Extreu un int de forma segura.

    Args:
        data: Diccionari amb les dades.
        key: Clau a buscar.
        default: Valor per defecte si no es troba o és invàlid.
        min_val: Valor mínim permès (opcional).
        max_val: Valor màxim permès (opcional).

    Returns:
        Int extret o valor per defecte.
    """
    if data is None:
        return default

    value = data.get(key)
    if value is None:
        return default

    try:
        result = int(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except (ValueError, TypeError):
        return default


def safe_str(
    data: dict[str, Any] | None,
    key: str,
    default: str = DEFAULT_FALLBACK_TEXT,
) -> str:
    """Extreu un string de forma segura.

    Args:
        data: Diccionari amb les dades.
        key: Clau a buscar.
        default: Valor per defecte si no es troba.

    Returns:
        String extret o valor per defecte.
    """
    if data is None:
        return default

    value = data.get(key)
    if value is None:
        return default

    return str(value)


def safe_list(
    data: dict[str, Any] | None,
    key: str,
    item_parser: Callable[[Any], Any] | None = None,
    default: list | None = None,
) -> list:
    """Extreu una llista de forma segura.

    Args:
        data: Diccionari amb les dades.
        key: Clau a buscar.
        item_parser: Funció per parsejar cada element (opcional).
        default: Llista per defecte ([] si None).

    Returns:
        Llista extreta o valor per defecte.
    """
    if default is None:
        default = []

    if data is None:
        return default

    value = data.get(key)
    if value is None or not isinstance(value, list):
        return default

    if item_parser is None:
        return value

    # Parsejar cada element, ignorant els que fallen
    result = []
    for item in value:
        try:
            parsed = item_parser(item)
            if parsed is not None:
                result.append(parsed)
        except Exception:
            continue

    return result


def safe_dict(
    data: dict[str, Any] | None,
    key: str,
    default: dict | None = None,
) -> dict:
    """Extreu un diccionari de forma segura.

    Args:
        data: Diccionari amb les dades.
        key: Clau a buscar.
        default: Diccionari per defecte ({} si None).

    Returns:
        Diccionari extret o valor per defecte.
    """
    if default is None:
        default = {}

    if data is None:
        return default

    value = data.get(key)
    if value is None or not isinstance(value, dict):
        return default

    return value
