"""Agent Investigador per buscar context històric i cultural."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class PersonReference(BaseModel):
    """Referència a una persona històrica."""

    nom: str
    descripcio: str
    dates: str | None = None
    rellevancia: str


class HistoricalContext(BaseModel):
    """Context històric d'una obra."""

    periode: str
    esdeveniments_clau: list[str]
    context_cultural: str
    context_politic: str


class ResearchRequest(BaseModel):
    """Sol·licitud d'investigació."""

    text: str
    autor: str
    titol: str
    llengua_original: Literal["llatí", "grec"]
    focus: list[str] = Field(
        default_factory=lambda: ["històric", "cultural", "biografic", "literari"]
    )


class InvestigadorAgent(BaseAgent):
    """Agent investigador de context històric i cultural.

    Proporciona informació contextual per enriquir les traduccions
    amb notes i aparats crítics.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return """Ets un investigador expert en antiguitat clàssica grecollatina.

OBJECTIU:
Proporcionar context històric, cultural i biogràfic per enriquir traduccions de textos clàssics.

ÀREES D'INVESTIGACIÓ:

1. CONTEXT HISTÒRIC
   - Situar l'obra en el seu moment històric
   - Esdeveniments polítics i socials rellevants
   - Institucions i costums de l'època
   - Guerres, tractats, canvis de règim

2. CONTEXT CULTURAL
   - Moviments literaris i filosòfics
   - Convencions del gènere
   - Influències i fonts de l'autor
   - Recepció de l'obra a l'antiguitat

3. INFORMACIÓ BIOGRÀFICA
   - Vida de l'autor
   - Carrera literària o política
   - Relacions amb altres autors
   - Circumstàncies de composició de l'obra

4. IDENTIFICACIÓ DE REFERÈNCIES
   - Personatges històrics mencionats
   - Llocs geogràfics
   - Esdeveniments al·ludits
   - Citacions d'altres obres
   - Referències mitològiques

5. SUGGERIMENTS PER A NOTES
   - Passatges que requereixen explicació
   - Al·lusions que el lector modern no entendria
   - Termes tècnics o institucionals
   - Jocs de paraules o dobles sentits

FORMAT DE RESPOSTA:
{{
    "resum_executiu": "<breu introducció al context>",
    "autor": {{
        "nom_complet": "<nom>",
        "dates": "<dates de vida>",
        "biografia_breu": "<100-200 paraules>",
        "altres_obres": ["<obra>"]
    }},
    "obra": {{
        "titol_original": "<títol>",
        "data_composicio": "<data o període>",
        "genere": "<gènere literari>",
        "estructura": "<descripció de l'estructura>",
        "tema_principal": "<tema>"
    }},
    "context_historic": {{
        "periode": "<període històric>",
        "esdeveniments_clau": ["<esdeveniment>"],
        "situacio_politica": "<descripció>",
        "situacio_social": "<descripció>"
    }},
    "context_cultural": {{
        "moviment_literari": "<moviment>",
        "influencies": ["<influència>"],
        "fonts": ["<font>"],
        "innovacions": ["<innovació>"]
    }},
    "personatges_identificats": [
        {{
            "nom": "<nom>",
            "descripcio": "<qui era>",
            "dates": "<dates>",
            "rellevancia": "<per què surt al text>"
        }}
    ],
    "llocs_identificats": [
        {{
            "nom_antic": "<nom>",
            "nom_modern": "<equivalent modern>",
            "descripcio": "<context>"
        }}
    ],
    "suggeriments_notes": [
        {{
            "passatge": "<cita del text>",
            "explicacio_suggerida": "<què caldria explicar>",
            "prioritat": "<alta|mitjana|baixa>"
        }}
    ]
}}"""

    def investigate(self, request: ResearchRequest) -> AgentResponse:
        """Investiga el context d'un text.

        Args:
            request: Sol·licitud amb el text i focus d'investigació.

        Returns:
            AgentResponse amb l'informe de context.
        """
        prompt = f"""Investiga el context d'aquest text clàssic:

TÍTOL: {request.titol}
AUTOR: {request.autor}
LLENGUA: {request.llengua_original}
FOCUS: {', '.join(request.focus)}

TEXT (fragment inicial):
{request.text[:3000]}{"..." if len(request.text) > 3000 else ""}

Proporciona un informe complet de context."""

        return self.process(prompt)

    def identify_references(self, text: str) -> AgentResponse:
        """Identifica totes les referències en un text.

        Args:
            text: Text a analitzar.

        Returns:
            AgentResponse amb les referències identificades.
        """
        prompt = f"""Identifica TOTES les referències en aquest text clàssic:

TEXT:
{text}

Busca:
- Personatges històrics o mitològics
- Llocs geogràfics (antics i moderns)
- Esdeveniments històrics
- Al·lusions a altres obres
- Termes tècnics o institucionals

Retorna JSON amb llistes separades per categoria."""

        return self.process(prompt)

    def author_biography(self, autor: str) -> AgentResponse:
        """Obté biografia detallada d'un autor.

        Args:
            autor: Nom de l'autor.

        Returns:
            AgentResponse amb la biografia.
        """
        prompt = f"""Proporciona una biografia completa de {autor} per a una edició crítica.

Inclou:
- Dates i llocs de vida
- Formació i carrera
- Obres principals
- Estil i aportacions
- Context històric
- Llegat i influència posterior"""

        return self.process(prompt)
