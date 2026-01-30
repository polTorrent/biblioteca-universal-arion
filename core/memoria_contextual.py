"""Memòria contextual per mantenir coherència entre chunks.

Guarda decisions de traducció, personatges, estil i context
per assegurar consistència al llarg de tota l'obra.
"""

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# FUNCIONS AUXILIARS
# =============================================================================

def normalitzar_text(text: str) -> str:
    """Normalitza text per a cerques (minúscules, sense accents).

    Args:
        text: Text a normalitzar.

    Returns:
        Text normalitzat sense accents i en minúscules.
    """
    # Convertir a minúscules
    text = text.lower().strip()

    # Eliminar accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    # Eliminar espais múltiples
    text = re.sub(r"\s+", " ", text)

    return text


# =============================================================================
# MODELS PYDANTIC
# =============================================================================

class TraduccioRegistrada(BaseModel):
    """Registre d'una traducció consistent."""

    original: str
    traduccio: str
    context: str | None = None
    justificacio: str | None = None
    primera_aparicio: str  # chunk_id


class Personatge(BaseModel):
    """Informació d'un personatge."""

    nom_original: str
    nom_traduit: str
    tractament: str | None = None  # "tu", "vós", "vostè"
    descripcio: str | None = None


class DecisioEstil(BaseModel):
    """Decisió estilística presa."""

    tipus: str  # "registre", "temps_verbal", "dialecte", etc.
    decisio: str
    justificacio: str | None = None


class ContextInvestigacio(BaseModel):
    """Context de la investigació sobre l'obra."""

    autor_bio: str | None = None
    context_historic: str | None = None
    context_obra: str | None = None
    influencies: list[str] = Field(default_factory=list)
    temes_principals: list[str] = Field(default_factory=list)


class MemoriaContextualData(BaseModel):
    """Estructura de dades de la memòria contextual."""

    traduccions: dict[str, TraduccioRegistrada] = Field(default_factory=dict)
    personatges: dict[str, Personatge] = Field(default_factory=dict)
    decisions_estil: list[DecisioEstil] = Field(default_factory=list)
    context_investigacio: ContextInvestigacio | None = None
    notes_pendents: list[str] = Field(default_factory=list)


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class MemoriaContextual:
    """Memòria contextual per mantenir coherència entre chunks.

    Guarda decisions de traducció per reutilitzar-les i assegurar
    consistència al llarg de tota l'obra.

    Exemple d'ús:
        memoria = MemoriaContextual()

        # Registrar traducció
        memoria.registrar_traduccio(
            original="ἀρετή",
            traduccio="virtut",
            context="Sòcrates parla de l'areté",
            justificacio="Terme filosòfic estàndard",
            chunk_id="chunk_1"
        )

        # Obtenir per consistència
        if memoria.existeix_traduccio("ἀρετή"):
            trad = memoria.obtenir_traduccio("ἀρετή")
            print(f"Usar: {trad.traduccio}")

        # Generar context pel traductor
        context = memoria.generar_context_per_traductor()
    """

    def __init__(self) -> None:
        """Inicialitza la memòria contextual buida."""
        self._data = MemoriaContextualData()
        print("[MemoriaContextual] Inicialitzada")

    # =========================================================================
    # TRADUCCIONS
    # =========================================================================

    def registrar_traduccio(
        self,
        original: str,
        traduccio: str,
        context: str | None = None,
        justificacio: str | None = None,
        chunk_id: str = "desconegut",
    ) -> None:
        """Registra una traducció per mantenir consistència.

        Args:
            original: Terme original.
            traduccio: Com s'ha traduït.
            context: On apareix (opcional).
            justificacio: Per què aquesta opció (opcional).
            chunk_id: Identificador del chunk on apareix primer.
        """
        clau = normalitzar_text(original)

        # No sobreescriure si ja existeix (mantenir primera decisió)
        if clau in self._data.traduccions:
            print(f"[MemoriaContextual] Traducció ja existent: '{original}' → '{self._data.traduccions[clau].traduccio}'")
            return

        self._data.traduccions[clau] = TraduccioRegistrada(
            original=original,
            traduccio=traduccio,
            context=context,
            justificacio=justificacio,
            primera_aparicio=chunk_id,
        )
        print(f"[MemoriaContextual] Registrada traducció: '{original}' → '{traduccio}'")

    def obtenir_traduccio(self, original: str) -> TraduccioRegistrada | None:
        """Obté una traducció registrada.

        Args:
            original: Terme original a cercar.

        Returns:
            TraduccioRegistrada si existeix, None altrament.
        """
        clau = normalitzar_text(original)
        return self._data.traduccions.get(clau)

    def existeix_traduccio(self, original: str) -> bool:
        """Comprova si existeix una traducció registrada.

        Args:
            original: Terme original a cercar.

        Returns:
            True si existeix, False altrament.
        """
        clau = normalitzar_text(original)
        return clau in self._data.traduccions

    def obtenir_totes_traduccions(self) -> list[TraduccioRegistrada]:
        """Retorna totes les traduccions registrades.

        Returns:
            Llista de traduccions.
        """
        return list(self._data.traduccions.values())

    # =========================================================================
    # PERSONATGES
    # =========================================================================

    def registrar_personatge(
        self,
        nom_original: str,
        nom_traduit: str,
        tractament: str | None = None,
        descripcio: str | None = None,
    ) -> None:
        """Registra un personatge i el seu tractament.

        Args:
            nom_original: Nom en l'idioma original.
            nom_traduit: Nom traduït al català.
            tractament: "tu", "vós", "vostè" (opcional).
            descripcio: Breu descripció del personatge (opcional).
        """
        clau = normalitzar_text(nom_original)

        self._data.personatges[clau] = Personatge(
            nom_original=nom_original,
            nom_traduit=nom_traduit,
            tractament=tractament,
            descripcio=descripcio,
        )
        tractament_str = f" (tractament: {tractament})" if tractament else ""
        print(f"[MemoriaContextual] Registrat personatge: '{nom_original}' → '{nom_traduit}'{tractament_str}")

    def obtenir_personatge(self, nom: str) -> Personatge | None:
        """Obté informació d'un personatge.

        Args:
            nom: Nom del personatge (original o traduït).

        Returns:
            Personatge si existeix, None altrament.
        """
        clau = normalitzar_text(nom)

        # Cercar per nom original
        if clau in self._data.personatges:
            return self._data.personatges[clau]

        # Cercar per nom traduït
        for p in self._data.personatges.values():
            if normalitzar_text(p.nom_traduit) == clau:
                return p

        return None

    def obtenir_tots_personatges(self) -> list[Personatge]:
        """Retorna tots els personatges registrats.

        Returns:
            Llista de personatges.
        """
        return list(self._data.personatges.values())

    # =========================================================================
    # DECISIONS D'ESTIL
    # =========================================================================

    def afegir_decisio_estil(
        self,
        tipus: str,
        decisio: str,
        justificacio: str | None = None,
    ) -> None:
        """Afegeix una decisió estilística.

        Args:
            tipus: Tipus de decisió ("registre", "temps_verbal", "dialecte", etc.).
            decisio: La decisió presa.
            justificacio: Per què (opcional).
        """
        # Comprovar si ja existeix una decisió del mateix tipus
        for d in self._data.decisions_estil:
            if d.tipus == tipus:
                print(f"[MemoriaContextual] Decisió d'estil '{tipus}' ja existent: '{d.decisio}'")
                return

        self._data.decisions_estil.append(DecisioEstil(
            tipus=tipus,
            decisio=decisio,
            justificacio=justificacio,
        ))
        print(f"[MemoriaContextual] Decisió d'estil: {tipus} → '{decisio}'")

    def obtenir_decisions_estil(self, tipus: str | None = None) -> list[DecisioEstil]:
        """Obté decisions d'estil, opcionalment filtrades per tipus.

        Args:
            tipus: Tipus a filtrar (opcional, None = totes).

        Returns:
            Llista de decisions.
        """
        if tipus is None:
            return self._data.decisions_estil.copy()

        return [d for d in self._data.decisions_estil if d.tipus == tipus]

    # =========================================================================
    # CONTEXT D'INVESTIGACIÓ
    # =========================================================================

    def establir_context_investigacio(self, context: ContextInvestigacio) -> None:
        """Estableix el context de la investigació sobre l'obra.

        Args:
            context: ContextInvestigacio amb la informació.
        """
        self._data.context_investigacio = context
        print("[MemoriaContextual] Context d'investigació establert")

    def obtenir_context_investigacio(self) -> ContextInvestigacio | None:
        """Obté el context d'investigació.

        Returns:
            ContextInvestigacio si existeix, None altrament.
        """
        return self._data.context_investigacio

    # =========================================================================
    # NOTES PENDENTS
    # =========================================================================

    def afegir_nota_pendent(self, nota: str) -> None:
        """Afegeix una nota pendent per l'Anotador.

        Args:
            nota: Text de la nota.
        """
        self._data.notes_pendents.append(nota)
        print(f"[MemoriaContextual] Nota pendent afegida: '{nota[:50]}...'")

    def obtenir_notes_pendents(self) -> list[str]:
        """Obté les notes pendents.

        Returns:
            Llista de notes.
        """
        return self._data.notes_pendents.copy()

    def buidar_notes_pendents(self) -> list[str]:
        """Buida i retorna les notes pendents.

        Returns:
            Llista de notes que s'han buidat.
        """
        notes = self._data.notes_pendents.copy()
        self._data.notes_pendents = []
        print(f"[MemoriaContextual] Buidat {len(notes)} notes pendents")
        return notes

    # =========================================================================
    # EXPORTAR / IMPORTAR
    # =========================================================================

    def exportar(self) -> dict[str, Any]:
        """Exporta les dades per guardar amb EstatPipeline.

        Returns:
            Diccionari amb totes les dades.
        """
        return self._data.model_dump()

    def importar(self, dades: dict[str, Any]) -> None:
        """Importa dades des d'EstatPipeline.

        Args:
            dades: Diccionari amb les dades exportades.
        """
        try:
            self._data = MemoriaContextualData.model_validate(dades)
            print(f"[MemoriaContextual] Importades {len(self._data.traduccions)} traduccions, "
                  f"{len(self._data.personatges)} personatges, "
                  f"{len(self._data.decisions_estil)} decisions d'estil")
        except Exception as e:
            print(f"[MemoriaContextual] Error important dades: {e}")
            self._data = MemoriaContextualData()

    # =========================================================================
    # GENERACIÓ DE CONTEXT
    # =========================================================================

    def generar_context_per_traductor(self) -> str:
        """Genera text de context per passar al TraductorEnriquit.

        Inclou:
        - Traduccions ja fetes (per consistència)
        - Personatges i tractaments
        - Decisions d'estil
        - Context de la investigació

        Returns:
            Text formatat amb el context.
        """
        seccions: list[str] = []

        # === DECISIONS D'ESTIL ===
        if self._data.decisions_estil:
            linies = ["## Decisions d'estil"]
            for d in self._data.decisions_estil:
                linia = f"- **{d.tipus}**: {d.decisio}"
                if d.justificacio:
                    linia += f" ({d.justificacio})"
                linies.append(linia)
            seccions.append("\n".join(linies))

        # === PERSONATGES ===
        if self._data.personatges:
            linies = ["## Personatges"]
            for p in self._data.personatges.values():
                linia = f"- **{p.nom_original}** → {p.nom_traduit}"
                if p.tractament:
                    linia += f" [tractament: {p.tractament}]"
                if p.descripcio:
                    linia += f" — {p.descripcio}"
                linies.append(linia)
            seccions.append("\n".join(linies))

        # === TRADUCCIONS CONSISTENTS ===
        if self._data.traduccions:
            linies = ["## Traduccions establertes (mantenir consistència)"]
            for t in self._data.traduccions.values():
                linia = f"- **{t.original}** → {t.traduccio}"
                if t.justificacio:
                    linia += f" ({t.justificacio})"
                linies.append(linia)
            seccions.append("\n".join(linies))

        # === CONTEXT D'INVESTIGACIÓ ===
        ctx = self._data.context_investigacio
        if ctx:
            linies = ["## Context de l'obra"]

            if ctx.autor_bio:
                linies.append(f"\n### Sobre l'autor\n{ctx.autor_bio}")

            if ctx.context_historic:
                linies.append(f"\n### Context històric\n{ctx.context_historic}")

            if ctx.context_obra:
                linies.append(f"\n### Sobre l'obra\n{ctx.context_obra}")

            if ctx.temes_principals:
                linies.append(f"\n### Temes principals\n- " + "\n- ".join(ctx.temes_principals))

            if ctx.influencies:
                linies.append(f"\n### Influències\n- " + "\n- ".join(ctx.influencies))

            seccions.append("\n".join(linies))

        if not seccions:
            return ""

        return "\n\n".join(seccions)

    # =========================================================================
    # RESUM
    # =========================================================================

    def resum(self) -> str:
        """Retorna un resum llegible de la memòria contextual.

        Returns:
            String amb el resum formatat.
        """
        d = self._data

        linies = [
            "═" * 60,
            "               MEMÒRIA CONTEXTUAL",
            "═" * 60,
            "",
            f"Traduccions registrades: {len(d.traduccions)}",
            f"Personatges: {len(d.personatges)}",
            f"Decisions d'estil: {len(d.decisions_estil)}",
            f"Context d'investigació: {'Sí' if d.context_investigacio else 'No'}",
            f"Notes pendents: {len(d.notes_pendents)}",
            "",
        ]

        # Traduccions
        if d.traduccions:
            linies.append("─" * 60)
            linies.append("                    TRADUCCIONS")
            linies.append("─" * 60)
            for t in list(d.traduccions.values())[:10]:  # Màxim 10
                linies.append(f"  {t.original} → {t.traduccio}")
            if len(d.traduccions) > 10:
                linies.append(f"  ... i {len(d.traduccions) - 10} més")
            linies.append("")

        # Personatges
        if d.personatges:
            linies.append("─" * 60)
            linies.append("                    PERSONATGES")
            linies.append("─" * 60)
            for p in d.personatges.values():
                tractament = f" [{p.tractament}]" if p.tractament else ""
                linies.append(f"  {p.nom_original} → {p.nom_traduit}{tractament}")
            linies.append("")

        # Decisions d'estil
        if d.decisions_estil:
            linies.append("─" * 60)
            linies.append("                 DECISIONS D'ESTIL")
            linies.append("─" * 60)
            for dec in d.decisions_estil:
                linies.append(f"  {dec.tipus}: {dec.decisio}")
            linies.append("")

        linies.append("═" * 60)

        return "\n".join(linies)

    # =========================================================================
    # PROPIETATS
    # =========================================================================

    @property
    def num_traduccions(self) -> int:
        """Nombre de traduccions registrades."""
        return len(self._data.traduccions)

    @property
    def num_personatges(self) -> int:
        """Nombre de personatges registrats."""
        return len(self._data.personatges)

    @property
    def num_decisions_estil(self) -> int:
        """Nombre de decisions d'estil."""
        return len(self._data.decisions_estil)

    @property
    def te_context_investigacio(self) -> bool:
        """Si té context d'investigació establert."""
        return self._data.context_investigacio is not None
