"""Models de dades per al sistema de traducció v2."""

from typing import Literal
from pydantic import BaseModel, Field


# =============================================================================
# ANÀLISI PRE-TRADUCCIÓ
# =============================================================================

class ParaulaClau(BaseModel):
    """Una paraula o terme clau identificat al text original."""

    terme: str = Field(..., description="El terme en la llengua original")
    transliteracio: str | None = Field(default=None, description="Transliteració si cal")
    categoria: Literal[
        "concepte_central",
        "terme_tecnic",
        "culturema",
        "nom_propi",
        "expressio_idiomatica",
        "ambiguitat_intencional",
    ] = Field(default="concepte_central")
    importancia: Literal["critica", "alta", "mitjana"] = Field(default="alta")
    context: str = Field(default="", description="Context on apareix")
    recomanacio_traduccio: str = Field(
        default="",
        description="Suggeriment de com tractar aquest terme"
    )


class RecursLiterari(BaseModel):
    """Un recurs literari o figura retòrica detectada."""

    tipus: Literal[
        "metafora",
        "comparacio",
        "al·literacio",
        "anafora",
        "paral·lelisme",
        "antitesi",
        "ironia",
        "hiperbole",
        "metonimia",
        "personificacio",
        "repeticio",
        "ritme",
        "rima",
        "ambiguitat",
        "joc_paraules",
        "altre",
    ]
    descripcio: str = Field(..., description="Descripció del recurs")
    exemple: str = Field(default="", description="Fragment on apareix")
    estrategia_traduccio: str = Field(
        default="",
        description="Com preservar o adaptar aquest recurs"
    )


class RepteTraduccio(BaseModel):
    """Un repte o dificultat anticipada per a la traducció."""

    tipus: Literal[
        "sintaxi",
        "lexic",
        "cultural",
        "estilistic",
        "ambiguitat",
        "intertextualitat",
        "registre",
        "ritme_so",
        "joc_paraules",
        "referencia_obscura",
    ]
    descripcio: str = Field(..., description="Descripció del repte")
    fragment: str = Field(default="", description="Fragment afectat")
    dificultat: Literal["alta", "mitjana", "baixa"] = Field(default="mitjana")
    estrategia_suggerida: str = Field(
        default="",
        description="Estratègia recomanada per abordar-lo"
    )


class AnalisiPreTraduccio(BaseModel):
    """Resultat complet de l'anàlisi pre-traducció."""

    # Identificació
    llengua_origen: str = Field(default="llatí")
    genere_detectat: str = Field(default="narrativa")
    registre: Literal["formal", "informal", "literari", "col·loquial", "tecnic", "solemne"] = Field(
        default="literari"
    )

    # Anàlisi de la veu
    to_autor: str = Field(
        default="",
        description="Descripció del to i veu de l'autor (ironia, solemnitat, humor...)"
    )
    estil_caracteristic: str = Field(
        default="",
        description="Trets estilístics distintius (frases curtes, subordinació complexa...)"
    )
    ritme_cadencia: str = Field(
        default="",
        description="Descripció del ritme i cadència del text"
    )

    # Elements clau
    paraules_clau: list[ParaulaClau] = Field(default_factory=list)
    recursos_literaris: list[RecursLiterari] = Field(default_factory=list)
    reptes_traduccio: list[RepteTraduccio] = Field(default_factory=list)

    # Recomanacions
    recomanacions_generals: str = Field(
        default="",
        description="Consells generals per a la traducció"
    )
    que_evitar: list[str] = Field(
        default_factory=list,
        description="Errors típics a evitar amb aquest text"
    )
    prioritats: list[str] = Field(
        default_factory=list,
        description="Aspectes prioritaris a preservar"
    )

    # Metadades
    confianca: float = Field(
        ge=0, le=1, default=0.8,
        description="Nivell de confiança en l'anàlisi (0-1)"
    )

    def resum(self) -> str:
        """Retorna un resum llegible de l'anàlisi."""
        linies = [
            "═══ ANÀLISI PRE-TRADUCCIÓ ═══",
            f"Llengua: {self.llengua_origen} | Gènere: {self.genere_detectat} | Registre: {self.registre}",
            "",
            "TO DE L'AUTOR:",
            f"  {self.to_autor}",
            "",
            "ESTIL CARACTERÍSTIC:",
            f"  {self.estil_caracteristic}",
        ]

        if self.paraules_clau:
            linies.append("")
            linies.append(f"PARAULES CLAU ({len(self.paraules_clau)}):")
            for p in self.paraules_clau[:5]:  # Màxim 5
                linies.append(f"  • {p.terme} [{p.categoria}]: {p.recomanacio_traduccio}")

        if self.recursos_literaris:
            linies.append("")
            linies.append(f"RECURSOS LITERARIS ({len(self.recursos_literaris)}):")
            for r in self.recursos_literaris[:5]:
                linies.append(f"  • {r.tipus}: {r.descripcio}")

        if self.reptes_traduccio:
            linies.append("")
            linies.append(f"REPTES ANTICIPATS ({len(self.reptes_traduccio)}):")
            for r in self.reptes_traduccio[:5]:
                linies.append(f"  • [{r.dificultat}] {r.tipus}: {r.descripcio}")

        if self.prioritats:
            linies.append("")
            linies.append("PRIORITATS:")
            for i, p in enumerate(self.prioritats[:3], 1):
                linies.append(f"  {i}. {p}")

        if self.que_evitar:
            linies.append("")
            linies.append("EVITAR:")
            for e in self.que_evitar[:3]:
                linies.append(f"  ✗ {e}")

        return "\n".join(linies)

    def to_context_traduccio(self) -> str:
        """Genera un text de context per passar al traductor."""
        seccions = []

        seccions.append("ANÀLISI DEL TEXT ORIGINAL")
        seccions.append("=" * 40)

        seccions.append(f"\nGènere: {self.genere_detectat}")
        seccions.append(f"Registre: {self.registre}")

        seccions.append(f"\nTO DE L'AUTOR:\n{self.to_autor}")
        seccions.append(f"\nESTIL:\n{self.estil_caracteristic}")

        if self.ritme_cadencia:
            seccions.append(f"\nRITME:\n{self.ritme_cadencia}")

        if self.paraules_clau:
            seccions.append("\nTERMES CLAU A TENIR EN COMPTE:")
            for p in self.paraules_clau:
                if p.recomanacio_traduccio:
                    seccions.append(f"  • {p.terme}: {p.recomanacio_traduccio}")

        if self.recursos_literaris:
            seccions.append("\nRECURSOS LITERARIS A PRESERVAR:")
            for r in self.recursos_literaris:
                if r.estrategia_traduccio:
                    seccions.append(f"  • {r.tipus}: {r.estrategia_traduccio}")

        if self.reptes_traduccio:
            seccions.append("\nREPTES ANTICIPATS:")
            for r in self.reptes_traduccio:
                seccions.append(f"  • {r.tipus}: {r.estrategia_suggerida}")

        seccions.append("\nRECOMANACIONS:")
        seccions.append(self.recomanacions_generals)

        if self.prioritats:
            seccions.append("\nPRIORITATS (en ordre):")
            for i, p in enumerate(self.prioritats, 1):
                seccions.append(f"  {i}. {p}")

        if self.que_evitar:
            seccions.append("\nEVITAR:")
            for e in self.que_evitar:
                seccions.append(f"  ✗ {e}")

        return "\n".join(seccions)


class ContextTraduccioEnriquit(BaseModel):
    """Context complet per a una traducció enriquida amb anàlisi prèvia."""

    text_original: str
    llengua_origen: str = "llatí"
    autor: str | None = None
    obra: str | None = None
    genere: str = "narrativa"

    # Anàlisi prèvia
    analisi: AnalisiPreTraduccio | None = None

    # Exemples few-shot (opcional)
    exemples_fewshot: list[dict] = Field(
        default_factory=list,
        description="Exemples de traduccions similars de qualitat"
    )

    # Glossari (opcional)
    glossari: dict[str, str] | None = None

    def to_prompt_context(self) -> str:
        """Genera el context complet per al prompt del traductor."""
        seccions = []

        if self.analisi:
            seccions.append(self.analisi.to_context_traduccio())
            seccions.append("")

        if self.exemples_fewshot:
            seccions.append("EXEMPLES DE TRADUCCIONS DE QUALITAT:")
            seccions.append("=" * 40)
            for ex in self.exemples_fewshot[:5]:
                seccions.append(f"\nOriginal: {ex.get('original', '')[:200]}")
                seccions.append(f"Traducció: {ex.get('traduccio', '')[:200]}")
                if ex.get('notes'):
                    seccions.append(f"Notes: {ex.get('notes')}")
            seccions.append("")

        if self.glossari:
            seccions.append("GLOSSARI:")
            seccions.append("=" * 40)
            for terme, traduccio in list(self.glossari.items())[:20]:
                seccions.append(f"  {terme} → {traduccio}")
            seccions.append("")

        return "\n".join(seccions)


# =============================================================================
# CONTEXT D'AVALUACIÓ
# =============================================================================

class ContextAvaluacio(BaseModel):
    """Context necessari per avaluar una traducció."""

    text_original: str = Field(..., description="Text en llengua origen")
    text_traduit: str = Field(..., description="Traducció a avaluar")
    llengua_origen: str = Field(default="llatí", description="Llengua del text original")
    autor: str | None = Field(default=None, description="Autor de l'obra")
    obra: str | None = Field(default=None, description="Títol de l'obra")
    genere: str = Field(default="narrativa", description="Gènere literari")
    descripcio_estil_autor: str | None = Field(
        default=None,
        description="Descripció de l'estil característic de l'autor"
    )
    glossari: dict[str, str] | None = Field(
        default=None,
        description="Glossari de termes clau i les seves traduccions"
    )
    max_chars: int = Field(
        default=8000,
        description="Límit de caràcters per a truncat de text en avaluacions"
    )


# =============================================================================
# AVALUACIÓ DE FIDELITAT
# =============================================================================

class ProblemaFidelitat(BaseModel):
    """Un problema de fidelitat detectat."""

    tipus: Literal["omissio", "addicio", "significat", "terminologia", "ambiguitat"]
    segment_original: str | None = Field(default=None, description="Fragment de l'original afectat")
    segment_traduit: str | None = Field(default=None, description="Fragment de la traducció")
    explicacio: str = Field(..., description="Explicació del problema")
    gravetat: int = Field(ge=0, le=3, default=1, description="Gravetat: 0=cap, 1=menor, 2=mitjà, 3=greu")


class AvaluacioFidelitat(BaseModel):
    """Resultat de l'avaluació de fidelitat."""

    puntuacio: float = Field(ge=0, le=10, description="Puntuació 0-10")
    problemes: list[ProblemaFidelitat] = Field(default_factory=list)
    feedback_refinament: str = Field(
        default="",
        description="Instruccions específiques per corregir problemes de fidelitat"
    )

    @property
    def te_problemes_greus(self) -> bool:
        """Retorna True si hi ha problemes de gravetat 3."""
        return any(p.gravetat == 3 for p in self.problemes)


# =============================================================================
# AVALUACIÓ DE VEU DE L'AUTOR
# =============================================================================

class SubavaluacioVeu(BaseModel):
    """Subavaluació d'un aspecte de la veu de l'autor."""

    puntuacio: float = Field(ge=0, le=10)
    observacions: str = Field(default="")


class AvaluacioVeuAutor(BaseModel):
    """Resultat de l'avaluació de preservació de la veu de l'autor."""

    puntuacio: float = Field(ge=0, le=10, description="Puntuació global 0-10")

    # Subavaluacions
    registre: SubavaluacioVeu = Field(
        default_factory=lambda: SubavaluacioVeu(puntuacio=5),
        description="Nivell de formalitat i registre"
    )
    to_emocional: SubavaluacioVeu = Field(
        default_factory=lambda: SubavaluacioVeu(puntuacio=5),
        description="Ironia, solemnitat, humor, etc."
    )
    ritme: SubavaluacioVeu = Field(
        default_factory=lambda: SubavaluacioVeu(puntuacio=5),
        description="Cadència, frases curtes/llargues"
    )
    idiosincrasies: SubavaluacioVeu = Field(
        default_factory=lambda: SubavaluacioVeu(puntuacio=5),
        description="Tics estilístics, vocabulari característic"
    )
    recursos_retorics: SubavaluacioVeu = Field(
        default_factory=lambda: SubavaluacioVeu(puntuacio=5),
        description="Figures retòriques, repeticions"
    )

    feedback_refinament: str = Field(
        default="",
        description="Instruccions per recuperar la veu de l'autor"
    )

    @property
    def es_despersonalitzat(self) -> bool:
        """Retorna True si la veu s'ha perdut significativament."""
        return self.puntuacio < 5


# =============================================================================
# AVALUACIÓ DE FLUÏDESA
# =============================================================================

class SubavaluacioFluidesa(BaseModel):
    """Subavaluació d'un aspecte de fluïdesa."""

    puntuacio: float = Field(ge=0, le=10)
    problemes: list[str] = Field(default_factory=list)


class ErrorNormatiu(BaseModel):
    """Un error de normativa detectat."""

    tipus: Literal["ortografia", "gramatica", "puntuacio", "lexic"]
    fragment: str
    correccio: str
    explicacio: str | None = None


class AvaluacioFluidesa(BaseModel):
    """Resultat de l'avaluació de fluïdesa en català."""

    puntuacio: float = Field(ge=0, le=10, description="Puntuació global 0-10")

    # Subavaluacions
    sintaxi: SubavaluacioFluidesa = Field(
        default_factory=lambda: SubavaluacioFluidesa(puntuacio=5),
        description="Ordre natural de paraules"
    )
    lexic: SubavaluacioFluidesa = Field(
        default_factory=lambda: SubavaluacioFluidesa(puntuacio=5),
        description="Vocabulari idiomàtic"
    )
    normativa: SubavaluacioFluidesa = Field(
        default_factory=lambda: SubavaluacioFluidesa(puntuacio=5),
        description="Correcció IEC"
    )
    llegibilitat: SubavaluacioFluidesa = Field(
        default_factory=lambda: SubavaluacioFluidesa(puntuacio=5),
        description="Facilitat de lectura"
    )

    errors_normatius: list[ErrorNormatiu] = Field(default_factory=list)
    calcs_detectats: list[str] = Field(
        default_factory=list,
        description="Estructures copiades d'altres llengües"
    )

    feedback_refinament: str = Field(
        default="",
        description="Instruccions per millorar la fluïdesa"
    )

    @property
    def te_calcs_greus(self) -> bool:
        """Retorna True si hi ha calcs evidents."""
        return len(self.calcs_detectats) >= 3


# =============================================================================
# FEEDBACK FUSIONAT
# =============================================================================

class FeedbackFusionat(BaseModel):
    """Feedback consolidat de les tres dimensions per al refinador."""

    # Puntuacions
    puntuacio_global: float = Field(ge=0, le=10, description="Puntuació ponderada")
    puntuacio_fidelitat: float = Field(ge=0, le=10)
    puntuacio_veu_autor: float = Field(ge=0, le=10)
    puntuacio_fluidesa: float = Field(ge=0, le=10)

    # Decisió
    aprovat: bool = Field(default=False, description="True si passa els llindars")
    requereix_revisio_humana: bool = Field(
        default=False,
        description="True si després de màx iteracions no s'arriba al llindar"
    )

    # Prioritats de refinament
    prioritat_1: str | None = Field(default=None, description="Dimensió més urgent")
    prioritat_2: str | None = Field(default=None)
    prioritat_3: str | None = Field(default=None)

    # Instruccions
    instruccions_refinament: str = Field(
        default="",
        description="Text consolidat per al refinador"
    )

    # Detall complet
    avaluacio_fidelitat: AvaluacioFidelitat | None = None
    avaluacio_veu_autor: AvaluacioVeuAutor | None = None
    avaluacio_fluidesa: AvaluacioFluidesa | None = None

    # Metadades
    iteracio: int = Field(default=1, description="Número d'iteració actual")

    def resum(self) -> str:
        """Retorna un resum llegible de l'avaluació."""
        estat = "APROVAT" if self.aprovat else "REQUEREIX REFINAMENT"
        linies = [
            f"=== AVALUACIÓ DIMENSIONAL ({estat}) ===",
            f"Puntuació global: {self.puntuacio_global:.1f}/10",
            f"  - Fidelitat:  {self.puntuacio_fidelitat:.1f}/10 (pes 25%)",
            f"  - Veu autor:  {self.puntuacio_veu_autor:.1f}/10 (pes 40%)",
            f"  - Fluïdesa:   {self.puntuacio_fluidesa:.1f}/10 (pes 35%)",
        ]

        if not self.aprovat:
            linies.append(f"\nPrioritat de refinament:")
            if self.prioritat_1:
                linies.append(f"  1. {self.prioritat_1}")
            if self.prioritat_2:
                linies.append(f"  2. {self.prioritat_2}")
            if self.prioritat_3:
                linies.append(f"  3. {self.prioritat_3}")

        return "\n".join(linies)


# =============================================================================
# CONSTANTS I CONFIGURACIÓ
# =============================================================================

class LlindarsAvaluacio(BaseModel):
    """Llindars per a l'aprovació de traduccions."""

    # Per aprovar directament
    global_minim: float = Field(default=8.0)
    veu_autor_minim: float = Field(default=7.5)
    fidelitat_minim: float = Field(default=7.0)
    fluidesa_minim: float = Field(default=7.0)

    # Per forçar refinament obligatori
    veu_autor_critic: float = Field(default=6.0)
    fidelitat_critic: float = Field(default=5.0)

    # Iteracions
    max_iteracions: int = Field(default=3)
    llindar_revisio_humana: float = Field(default=7.5)


# Configuració per defecte
LLINDARS_DEFAULT = LlindarsAvaluacio()

# Pesos de les dimensions
PESOS_DIMENSIONS = {
    "fidelitat": 0.25,
    "veu_autor": 0.40,
    "fluidesa": 0.35,
}
