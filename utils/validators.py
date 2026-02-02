"""Validadors d'entrada per al pipeline de traducció."""

import re
from dataclasses import dataclass
from enum import Enum


class SeverityLevel(Enum):
    """Nivells de severitat per als missatges de validació."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Resultat d'una validació.

    Attributes:
        valid: True si no hi ha errors (pot haver-hi warnings).
        messages: Llista de tuples (severitat, missatge).
    """

    valid: bool
    messages: list[tuple[SeverityLevel, str]]

    def has_errors(self) -> bool:
        """Retorna True si hi ha algun error."""
        return any(sev == SeverityLevel.ERROR for sev, _ in self.messages)

    def has_warnings(self) -> bool:
        """Retorna True si hi ha algun warning."""
        return any(sev == SeverityLevel.WARNING for sev, _ in self.messages)

    def summary(self) -> str:
        """Retorna un resum formatat dels missatges."""
        if not self.messages:
            return "✅ Validació correcta"

        lines = []
        for sev, msg in self.messages:
            icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}[sev.value]
            lines.append(f"{icon} {msg}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def validar_text_entrada(
    text: str,
    llengua_origen: str,
    max_chars: int = 100_000,
    min_chars: int = 50,
) -> ValidationResult:
    """Valida el text abans de traduir.

    Comprova longitud, llengua d'origen i caràcters problemàtics.

    Args:
        text: Text a validar.
        llengua_origen: Llengua declarada (grec, llati, angles, etc.).
        max_chars: Màxim de caràcters permesos.
        min_chars: Mínim de caràcters requerits.

    Returns:
        ValidationResult amb els avisos/errors trobats.
    """
    messages: list[tuple[SeverityLevel, str]] = []

    # Verificar que text és string
    if not isinstance(text, str):
        messages.append((
            SeverityLevel.ERROR,
            f"El text ha de ser una cadena, però és {type(text).__name__}."
        ))
        return ValidationResult(valid=False, messages=messages)

    # Longitud màxima
    if len(text) > max_chars:
        messages.append((
            SeverityLevel.ERROR,
            f"Text massa llarg ({len(text):,} chars > {max_chars:,}). Divideix-lo primer."
        ))
    elif len(text) > max_chars * 0.8:
        messages.append((
            SeverityLevel.WARNING,
            f"Text molt llarg ({len(text):,} chars). Considera dividir-lo."
        ))

    # Text buit o massa curt
    text_stripped = text.strip()
    if len(text_stripped) == 0:
        messages.append((
            SeverityLevel.ERROR,
            "Text buit. No hi ha res a traduir."
        ))
    elif len(text_stripped) < min_chars:
        messages.append((
            SeverityLevel.ERROR,
            f"Text massa curt per traduir ({len(text_stripped)} chars < {min_chars})."
        ))

    # Detecció bàsica de llengua (heurística simple)
    indicadors_llengua = {
        "grec": ["τ", "ὁ", "καὶ", "τὸ", "ἐν", "δὲ", "ἡ", "τῶν"],
        "llati": ["que", "est", "non", "sed", "cum", "enim", "atque", "autem"],
        "alemany": ["und", "der", "die", "das", "ist", "nicht", "ein", "zu"],
        "angles": ["the", "and", "is", "of", "to", "in", "that", "it"],
        "frances": ["le", "la", "les", "de", "et", "est", "une", "des"],
        "italia": ["il", "la", "di", "che", "è", "non", "una", "per"],
        "japones": ["の", "は", "を", "に", "が", "と", "で", "も"],
        "xines": ["的", "是", "不", "了", "在", "人", "有", "我"],
    }

    text_lower = text.lower()
    llengua_norm = llengua_origen.lower().replace("í", "i").replace("è", "e")

    if llengua_norm in indicadors_llengua:
        indicadors = indicadors_llengua[llengua_norm]
        trobats = sum(1 for ind in indicadors if ind in text_lower)
        if trobats < 2:
            messages.append((
                SeverityLevel.WARNING,
                f"El text no sembla ser en {llengua_origen}. Verifica la llengua d'origen."
            ))

    # Caràcters de control (excloent newlines, tabs, etc.)
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
        messages.append((
            SeverityLevel.WARNING,
            "El text conté caràcters de control. Es netejaran automàticament."
        ))

    # Caràcters NULL
    if '\x00' in text:
        messages.append((
            SeverityLevel.ERROR,
            "El text conté caràcters NULL (\\x00). No es pot processar."
        ))

    # Percentatge de caràcters no imprimibles
    non_printable = sum(1 for c in text if not c.isprintable() and c not in '\n\r\t')
    if non_printable > len(text) * 0.1:
        messages.append((
            SeverityLevel.WARNING,
            f"Alt percentatge de caràcters no imprimibles ({non_printable/len(text)*100:.1f}%)."
        ))

    valid = not any(sev == SeverityLevel.ERROR for sev, _ in messages)
    return ValidationResult(valid=valid, messages=messages)


def netejar_text(text: str) -> str:
    """Neteja el text d'elements problemàtics.

    Elimina caràcters de control, normalitza espais i salts de línia.

    Args:
        text: Text a netejar.

    Returns:
        Text netejat.
    """
    if not isinstance(text, str):
        return str(text)

    # Eliminar caràcters de control (excepte newlines i tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    # Normalitzar espais múltiples (excepte al principi de línia per preservar indentació)
    text = re.sub(r'(?<!\n) +', ' ', text)

    # Normalitzar salts de línia múltiples (màxim 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Eliminar espais al final de cada línia
    text = re.sub(r' +\n', '\n', text)

    return text.strip()


def validar_glossari(glossari: dict | list) -> ValidationResult:
    """Valida l'estructura d'un glossari.

    Args:
        glossari: Glossari a validar (dict o llista d'entrades).

    Returns:
        ValidationResult amb els avisos/errors trobats.
    """
    messages: list[tuple[SeverityLevel, str]] = []

    if isinstance(glossari, dict):
        entries = glossari.get("termes", glossari.get("entries", []))
    elif isinstance(glossari, list):
        entries = glossari
    else:
        messages.append((
            SeverityLevel.ERROR,
            f"Format de glossari invàlid: {type(glossari).__name__}"
        ))
        return ValidationResult(valid=False, messages=messages)

    if not entries:
        messages.append((
            SeverityLevel.WARNING,
            "El glossari és buit."
        ))
        return ValidationResult(valid=True, messages=messages)

    # Verificar cada entrada
    ids_vistos = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            messages.append((
                SeverityLevel.ERROR,
                f"Entrada {i}: format invàlid (esperava dict, rebut {type(entry).__name__})"
            ))
            continue

        # Camps requerits
        entry_id = entry.get("id")
        if not entry_id:
            messages.append((
                SeverityLevel.WARNING,
                f"Entrada {i}: manca camp 'id'"
            ))
        elif entry_id in ids_vistos:
            messages.append((
                SeverityLevel.WARNING,
                f"Entrada {i}: ID duplicat '{entry_id}'"
            ))
        else:
            ids_vistos.add(entry_id)

        if not entry.get("traduccio") and not entry.get("traducció"):
            messages.append((
                SeverityLevel.WARNING,
                f"Entrada {i} ({entry_id or '?'}): manca traducció"
            ))

    valid = not any(sev == SeverityLevel.ERROR for sev, _ in messages)
    return ValidationResult(valid=valid, messages=messages)


def validar_metadata(metadata: dict) -> ValidationResult:
    """Valida el metadata d'una obra.

    Args:
        metadata: Diccionari amb metadata de l'obra.

    Returns:
        ValidationResult amb els avisos/errors trobats.
    """
    messages: list[tuple[SeverityLevel, str]] = []

    camps_requerits = ["titol", "autor", "llengua_origen"]
    camps_recomanats = ["any_original", "genere", "estat"]

    for camp in camps_requerits:
        if camp not in metadata or not metadata[camp]:
            messages.append((
                SeverityLevel.ERROR,
                f"Manca camp requerit: '{camp}'"
            ))

    for camp in camps_recomanats:
        if camp not in metadata or not metadata[camp]:
            messages.append((
                SeverityLevel.WARNING,
                f"Manca camp recomanat: '{camp}'"
            ))

    # Validar estat si existeix
    estats_valids = ["en_progres", "complet", "revisat", "publicat"]
    if "estat" in metadata and metadata["estat"] not in estats_valids:
        messages.append((
            SeverityLevel.WARNING,
            f"Estat '{metadata['estat']}' no és un valor estàndard: {estats_valids}"
        ))

    valid = not any(sev == SeverityLevel.ERROR for sev, _ in messages)
    return ValidationResult(valid=valid, messages=messages)
