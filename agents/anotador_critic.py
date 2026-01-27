"""Agent Anotador Crític - afegeix notes erudites i context."""

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

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

    def annotate(self, request: AnotacioRequest) -> AgentResponse:
        """Afegeix notes crítiques a un text.

        Args:
            request: Sol·licitud amb el text i paràmetres d'anotació.

        Returns:
            AgentResponse amb el text anotat i llista de notes.
        """
        context_str = ""
        if request.context_historic:
            context_str = f"\nCONTEXT HISTÒRIC CONEGUT:\n{request.context_historic[:1500]}"

        original_str = ""
        if request.text_original:
            original_str = f"\nTEXT ORIGINAL:\n{request.text_original[:2000]}"

        densitat_descripcio = {
            "minima": "Només notes essencials. Màxim 2-3 per pàgina.",
            "normal": "Notes per a context important. 4-6 per pàgina.",
            "exhaustiva": "Anotació acadèmica completa. 8-12 per pàgina."
        }

        prompt = f"""Afegeix notes crítiques a aquest text.

LLENGUA ORIGEN: {request.llengua_origen}
GÈNERE: {request.genere}
DENSITAT DESITJADA: {request.densitat_notes} - {densitat_descripcio.get(request.densitat_notes, "")}
{context_str}

TEXT A ANOTAR:
{request.text}
{original_str}
"""
        return self.process(prompt)

    def annotate_specific(
        self,
        text: str,
        tipus_notes: list[str],
        llengua_origen: str = "llati",
    ) -> AgentResponse:
        """Afegeix només notes d'un tipus específic.

        Args:
            text: Text a anotar.
            tipus_notes: Llista de tipus de notes a afegir.
            llengua_origen: Llengua d'origen del text.

        Returns:
            AgentResponse amb les notes del tipus especificat.
        """
        tipus_str = ", ".join(tipus_notes)
        prompt = f"""Afegeix NOMÉS notes dels tipus següents: {tipus_str}

LLENGUA ORIGEN: {llengua_origen}

TEXT:
{text}

Ignora qualsevol altre tipus de nota que podries afegir."""

        return self.process(prompt)
