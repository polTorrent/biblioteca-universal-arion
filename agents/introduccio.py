"""Agent d'Introducció per escriure pròlegs i notes del traductor."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.translator_agent import SupportedLanguage


class IntroductionSection(BaseModel):
    """Secció d'una introducció."""

    titol: str
    contingut: str
    ordre: int


class IntroductionRequest(BaseModel):
    """Sol·licitud de redacció d'introducció."""

    titol: str
    autor: str
    llengua_original: SupportedLanguage
    resum_obra: str
    context_historic: str
    public_objectiu: str
    tipus: Literal["acadèmica", "divulgativa", "breu"] = "divulgativa"
    incloure_nota_traductor: bool = True
    criteris_traduccio: str | None = None


class IntroduccioAgent(BaseAgent):
    """Agent per escriure introduccions, pròlegs i notes del traductor.

    Crea textos introductoris adequats al públic objectiu i
    al tipus d'edició.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        tipus: Literal["acadèmica", "divulgativa", "breu"] = "divulgativa",
    ) -> None:
        super().__init__(config)
        self.tipus = tipus

    @property
    def system_prompt(self) -> str:
        return f"""Ets un especialista en literatura clàssica universal expert en redactar introduccions per a edicions de textos de diverses tradicions.

OBJECTIU:
Escriure introduccions que contextualitzin l'obra per al lector modern i facilitin la seva comprensió i gaudi.

TIPUS D'INTRODUCCIÓ: {self.tipus.upper()}

ESTRUCTURA SEGONS TIPUS:

1. INTRODUCCIÓ ACADÈMICA (15-25 pàgines)
   a) L'autor: vida, obra, context
   b) L'obra: gènere, estructura, temes
   c) Context històric i literari
   d) Transmissió textual i edicions
   e) Recepció i influència
   f) Criteris d'aquesta edició
   g) Bibliografia selecta

2. INTRODUCCIÓ DIVULGATIVA (5-10 pàgines)
   a) Per què llegir aquesta obra avui
   b) L'autor en el seu temps
   c) De què tracta l'obra
   d) Claus de lectura
   e) Nota sobre la traducció

3. INTRODUCCIÓ BREU (1-2 pàgines)
   a) L'autor i l'obra
   b) Context essencial
   c) Invitació a la lectura

NOTA DEL TRADUCTOR:
   - Criteris de traducció seguits
   - Dificultats específiques
   - Decisions terminològiques
   - Agraïments

ESTIL:
- {self.tipus.upper()}: {"Rigor acadèmic, citacions, notes" if self.tipus == "acadèmica" else "Amè, accessible, sense jargó" if self.tipus == "divulgativa" else "Concís, directe, essencial"}
- Evitar pedanteria innecessària
- Connectar amb preocupacions actuals sense anacronismes
- Transmetre passió pel text

FORMAT DE RESPOSTA:
{{
    "introduccio": {{
        "titol": "<títol de la introducció>",
        "seccions": [
            {{
                "titol": "<títol de secció>",
                "contingut": "<text en markdown>"
            }}
        ]
    }},
    "nota_traductor": {{
        "titol": "Nota del traductor",
        "contingut": "<text en markdown>"
    }},
    "resum_contraportada": "<text de 100-150 paraules per a contraportada>",
    "paraules_clau": ["<paraula>"],
    "estadistiques": {{
        "paraules_introduccio": <número>,
        "paraules_nota": <número>
    }}
}}"""

    def write_introduction(self, request: IntroductionRequest) -> AgentResponse:
        """Escriu una introducció completa.

        Args:
            request: Paràmetres de la introducció.

        Returns:
            AgentResponse amb la introducció i nota del traductor.
        """
        self.tipus = request.tipus

        prompt = f"""Escriu una introducció {request.tipus} per a aquesta obra:

TÍTOL: {request.titol}
AUTOR: {request.autor}
LLENGUA ORIGINAL: {request.llengua_original}
PÚBLIC OBJECTIU: {request.public_objectiu}

RESUM DE L'OBRA:
{request.resum_obra}

CONTEXT HISTÒRIC:
{request.context_historic}

{"CRITERIS DE TRADUCCIÓ:" + chr(10) + request.criteris_traduccio if request.criteris_traduccio else ""}

{"Inclou nota del traductor." if request.incloure_nota_traductor else "No cal nota del traductor."}"""

        return self.process(prompt)

    def write_back_cover(self, titol: str, autor: str, resum: str) -> AgentResponse:
        """Escriu el text de contraportada.

        Args:
            titol: Títol de l'obra.
            autor: Autor.
            resum: Resum de l'obra.

        Returns:
            AgentResponse amb el text de contraportada.
        """
        prompt = f"""Escriu un text de contraportada atractiu (100-150 paraules) per:

TÍTOL: {titol}
AUTOR: {autor}

RESUM:
{resum}

El text ha de:
- Captar l'atenció del lector
- Explicar per què és rellevant avui
- Evitar spoilers
- Ser evocador però no exagerat"""

        return self.process(prompt)

    def write_translator_note(self, criteris: str, dificultats: str) -> AgentResponse:
        """Escriu només la nota del traductor.

        Args:
            criteris: Criteris de traducció.
            dificultats: Dificultats trobades.

        Returns:
            AgentResponse amb la nota del traductor.
        """
        prompt = f"""Escriu una nota del traductor professional:

CRITERIS SEGUITS:
{criteris}

DIFICULTATS TROBADES:
{dificultats}

La nota ha de:
- Explicar les decisions de traducció
- Justificar opcions controvertides
- Ser honesta sobre les dificultats
- Agrair si escau (editor, revisors)"""

        return self.process(prompt)
