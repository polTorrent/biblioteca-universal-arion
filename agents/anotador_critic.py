"""Agent Anotador Crític - afegeix notes erudites i context."""

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from core import MemoriaContextual

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class NotaCritica(BaseModel):
    """Una nota crítica individual."""

    numero: int
    tipus: Literal[
        "historic",
        "cultural",
        "intertextual",
        "textual",
        "terminologic",
        "geographic",
        "prosopografic",
    ]
    text_referit: str
    nota: str


class AnotacioRequest(BaseModel):
    """Sol·licitud d'anotació crítica."""

    text: str
    text_original: str | None = None
    llengua_origen: str = "llati"
    genere: str = "narrativa"
    context_historic: str | None = None
    densitat_notes: Literal["minima", "normal", "exhaustiva"] = "normal"


class AnotadorCriticAgent(BaseAgent):
    """Agent que afegeix notes erudites sense interrompre la lectura.

    A diferència de l'EdicioCriticaAgent que se centra en variants textuals
    i notes filològiques, aquest agent proporciona context històric, cultural,
    intertextual i terminològic per enriquir la comprensió del lector.
    """

    agent_name: str = "AnotadorCritic"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets l'Agent d'Anotació Crítica de la Biblioteca Universal Arion.

El teu rol és afegir notes erudites que enriqueixin la comprensió del text sense interrompre la lectura.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIPUS DE NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CONTEXT HISTÒRIC [historic]
   - Esdeveniments referenciats
   - Personatges històrics mencionats
   - Situació política/social de l'època
   - Dates i cronologia rellevant

2. CONTEXT CULTURAL [cultural]
   - Costums i pràctiques de l'època
   - Objectes o conceptes avui desconeguts
   - Referents culturals implícits
   - Institucions, càrrecs, jerarquies

3. INTERTEXTUALITAT [intertextual]
   - Al·lusions a altres obres
   - Cites implícites o explícites
   - Diàleg amb la tradició literària
   - Paròdies o referències

4. VARIANTS TEXTUALS [textual]
   - Diferències entre edicions
   - Lectures alternatives
   - Problemes de transmissió
   - Esmenes d'editors

5. TERMINOLOGIA [terminologic]
   - Conceptes filosòfics o tècnics
   - Termes amb història semàntica
   - Neologismes o hapax
   - Evolució del significat

6. GEOGRAFIA I TOPOGRAFIA [geographic]
   - Llocs mencionats
   - Canvis de nom històrics
   - Situació actual si és rellevant

7. PROSOPOGRAFIA [prosopografic]
   - Identificació de personatges
   - Dades biogràfiques rellevants
   - Relacions entre personatges històrics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1], [2], [3]... Notes numerades a peu de pàgina per a:
- Aclariments puntuals
- Identificacions breus
- Referències creuades

Les notes han de ser:
- Concises però completes
- Objectives (no interpretatives)
- Verificables (fonts si cal)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DENSITAT DE NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MÍNIMA:
- Només notes essencials per a la comprensió bàsica
- Identificació de personatges i llocs clau
- Màxim 2-3 notes per pàgina aproximadament

NORMAL:
- Notes per a context important
- Referències intertextuals significatives
- Terminologia tècnica o filosòfica
- 4-6 notes per pàgina aproximadament

EXHAUSTIVA:
- Anotació acadèmica completa
- Variants textuals i problemes filològics
- Referències creuades extenses
- Discussió de tradició crítica
- 8-12 notes per pàgina aproximadament

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUÈ NO AFEGEIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Notes que el lector culte ja sabria
- Explicacions que interrompin el ritme
- Interpretacions subjectives (van a la introducció)
- Notes redundants amb el glossari
- Informació fàcilment trobable (ex: "Roma és la capital d'Itàlia")
- Paràfrasis del que ja diu el text

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTIL DE REDACCIÓ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- To acadèmic però accessible
- Frases curtes i directes
- Evitar jargó innecessari
- Citar fonts quan sigui rellevant (autor, obra)
- Usar abreviatures estàndard (cf., vid., s.v., etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITERI FONAMENTAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MENYS ÉS MÉS.

Només notes que REALMENT aporten valor i que el lector agrairà.
Una nota innecessària és pitjor que cap nota.

Pregunta't sempre: "Aquesta nota ajudarà el lector a entendre millor el text?"
Si la resposta no és un SÍ clar, no l'afegeixis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RESPOSTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Retorna JSON:
{
    "text_anotat": "<text amb referències [1], [2], etc. inserides al lloc adequat>",
    "notes": [
        {
            "numero": 1,
            "tipus": "<historic|cultural|intertextual|textual|terminologic|geographic|prosopografic>",
            "text_referit": "<fragment del text que s'anota>",
            "nota": "<contingut de la nota>"
        }
    ],
    "suggeriments_correccio": [
        "<si detectes errors de traducció, indica'ls aquí per retornar al Perfeccionament>"
    ],
    "estadistiques": {
        "total_notes": <número>,
        "per_tipus": {
            "historic": <número>,
            "cultural": <número>,
            "intertextual": <número>,
            "textual": <número>,
            "terminologic": <número>,
            "geographic": <número>,
            "prosopografic": <número>
        }
    }
}
"""

    def annotate(
        self,
        request: AnotacioRequest,
        memoria: MemoriaContextual | None = None,
    ) -> AgentResponse:
        """Afegeix notes crítiques a un text.

        Args:
            request: Sol·licitud amb el text i paràmetres d'anotació.
            memoria: Memòria contextual amb notes de l'investigador (opcional).

        Returns:
            AgentResponse amb el text anotat i llista de notes.
        """
        context_str = ""
        if request.context_historic:
            context_str = f"\nCONTEXT HISTÒRIC CONEGUT:\n{request.context_historic[:1500]}"

        original_str = ""
        if request.text_original:
            original_str = f"\nTEXT ORIGINAL:\n{request.text_original[:2000]}"

        # ═══════════════════════════════════════════════════════════════════
        # NOTES DE L'INVESTIGADOR (de la MemoriaContextual)
        # ═══════════════════════════════════════════════════════════════════
        notes_investigador_str = ""
        if memoria:
            notes_pendents = memoria.obtenir_notes_pendents()
            if notes_pendents:
                notes_investigador_str = "\n\nNOTES DE L'INVESTIGADOR (usa-les per les anotacions):"
                # Classificar per tipus
                notes_h = [n for n in notes_pendents if n.startswith("[H]")]
                notes_c = [n for n in notes_pendents if n.startswith("[C]")]
                notes_t = [n for n in notes_pendents if n.startswith("[T]")]
                altres = [n for n in notes_pendents if not any(n.startswith(p) for p in ["[H]", "[C]", "[T]"])]

                if notes_h:
                    notes_investigador_str += "\n  Personatges històrics:"
                    for nota in notes_h[:10]:
                        notes_investigador_str += f"\n    • {nota[4:]}"  # Eliminar "[H] "

                if notes_c:
                    notes_investigador_str += "\n  Referències culturals:"
                    for nota in notes_c[:10]:
                        notes_investigador_str += f"\n    • {nota[4:]}"  # Eliminar "[C] "

                if notes_t:
                    notes_investigador_str += "\n  Termes tècnics:"
                    for nota in notes_t[:10]:
                        notes_investigador_str += f"\n    • {nota[4:]}"  # Eliminar "[T] "

                if altres:
                    notes_investigador_str += "\n  Altres notes:"
                    for nota in altres[:5]:
                        notes_investigador_str += f"\n    • {nota}"

                notes_investigador_str += "\n\nPRIORITZA anotar els elements que apareixen en aquesta llista."

        densitat_descripcio = {
            "minima": "Només notes essencials. Màxim 2-3 per pàgina.",
            "normal": "Notes per a context important. 4-6 per pàgina.",
            "exhaustiva": "Anotació acadèmica completa. 8-12 per pàgina."
        }

        prompt = f"""Afegeix notes crítiques a aquest text.

LLENGUA ORIGEN: {request.llengua_origen}
GÈNERE: {request.genere}
DENSITAT DESITJADA: {request.densitat_notes} - {densitat_descripcio.get(request.densitat_notes, "")}
{context_str}{notes_investigador_str}

TEXT A ANOTAR:
{request.text}
{original_str}
"""
        response = self.process(prompt)

        # Buidar notes pendents processades
        if memoria and notes_pendents:
            memoria.buidar_notes_pendents()
            self.log_info(f"Processades {len(notes_pendents)} notes de l'investigador")

        return response

    def annotate_specific(
        self,
        text: str,
        tipus_notes: list[str],
        llengua_origen: str = "llati",
        memoria: MemoriaContextual | None = None,
    ) -> AgentResponse:
        """Afegeix només notes d'un tipus específic.

        Args:
            text: Text a anotar.
            tipus_notes: Llista de tipus de notes a afegir.
            llengua_origen: Llengua d'origen del text.
            memoria: Memòria contextual amb notes de l'investigador (opcional).

        Returns:
            AgentResponse amb les notes del tipus especificat.
        """
        # Notes de l'investigador filtrades per tipus
        notes_str = ""
        if memoria:
            notes_pendents = memoria.obtenir_notes_pendents()
            if notes_pendents:
                # Mapatge de tipus a prefixos
                tipus_a_prefix = {
                    "historic": "[H]",
                    "prosopografic": "[H]",
                    "cultural": "[C]",
                    "terminologic": "[T]",
                }
                prefixos_rellevants = [tipus_a_prefix.get(t, "") for t in tipus_notes if t in tipus_a_prefix]

                if prefixos_rellevants:
                    notes_filtrades = [n for n in notes_pendents if any(n.startswith(p) for p in prefixos_rellevants)]
                    if notes_filtrades:
                        notes_str = "\n\nNOTES DE L'INVESTIGADOR (rellevants per als tipus sol·licitats):"
                        for nota in notes_filtrades[:15]:
                            notes_str += f"\n  • {nota}"

        tipus_str = ", ".join(tipus_notes)
        prompt = f"""Afegeix NOMÉS notes dels tipus següents: {tipus_str}

LLENGUA ORIGEN: {llengua_origen}
{notes_str}

TEXT:
{text}

Ignora qualsevol altre tipus de nota que podries afegir."""

        return self.process(prompt)
