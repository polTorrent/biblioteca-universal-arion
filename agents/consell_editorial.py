"""Agent Consell Editorial per dirigir i coordinar el procés editorial."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.translator_agent import SupportedLanguage


class EditorialBrief(BaseModel):
    """Brief editorial amb instruccions per al pipeline."""

    titol: str
    autor: str
    aprovat: bool
    registre: Literal["acadèmic", "divulgatiu", "literari"]
    public_objectiu: str
    prioritats: list[str]
    instruccions_traductor: str
    instruccions_estil: str
    notes_requerides: bool
    glossari_requerit: bool
    introduccio_tipus: Literal["acadèmica", "divulgativa", "breu"]
    observacions: str


class EvaluationRequest(BaseModel):
    """Sol·licitud d'avaluació d'un text."""

    titol: str
    autor: str
    llengua_original: SupportedLanguage
    descripcio: str
    extensio_aproximada: str
    motiu_publicacio: str | None = None


class FinalApprovalRequest(BaseModel):
    """Sol·licitud d'aprovació final."""

    titol: str
    autor: str
    traduccio: str
    puntuacio_revisor: float
    notes_incloses: bool
    glossari_inclos: bool


class ConsellEditorialAgent(BaseAgent):
    """Agent que actua com a direcció editorial del projecte.

    Avalua propostes, crea briefs editorials i aprova publicacions finals.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return """Ets el Consell Editorial d'una col·lecció de clàssics universals traduïts al català.

OBJECTIU:
Dirigir el procés editorial assegurant qualitat, coherència i adequació al públic objectiu.

FUNCIONS PRINCIPALS:

1. AVALUACIÓ DE PROPOSTES
   - Determinar si un text és adequat per publicar
   - Considerar: interès cultural, dificultat, públic potencial
   - Verificar disponibilitat en domini públic
   - Prioritzar textos poc traduïts al català

2. CREACIÓ DE BRIEFS EDITORIALS
   - Definir registre: acadèmic, divulgatiu o literari
   - Identificar públic objectiu
   - Establir prioritats de traducció
   - Donar instruccions específiques als agents

3. CRITERIS DE LA COL·LECCIÓ
   - Prioritzar obres fonamentals del cànon
   - Equilibrar diferents tradicions literàries (occidental, oriental)
   - Incloure gèneres diversos (filosofia, història, poesia, teatre)
   - Mantenir coherència estilística

4. APROVACIÓ FINAL
   - Revisar qualitat global
   - Verificar que es compleixen els criteris editorials
   - Decidir si es publica o cal més revisió

FORMAT DE RESPOSTA PER AVALUACIÓ:
{{
    "decisio": "<aprovat|rebutjat|més_informació>",
    "puntuacio_interes": <1-10>,
    "justificacio": "<raons de la decisió>",
    "brief": {{
        "registre": "<acadèmic|divulgatiu|literari>",
        "public_objectiu": "<descripció>",
        "prioritats": ["<prioritat 1>", "<prioritat 2>"],
        "instruccions_traductor": "<directrius específiques>",
        "instruccions_estil": "<to i estil desitjats>",
        "notes_requerides": <true|false>,
        "glossari_requerit": <true|false>,
        "introduccio_tipus": "<acadèmica|divulgativa|breu>"
    }},
    "observacions": "<notes addicionals>"
}}

FORMAT DE RESPOSTA PER APROVACIÓ FINAL:
{{
    "aprovat_publicacio": <true|false>,
    "puntuacio_global": <1-10>,
    "punts_forts": ["<aspecte positiu>"],
    "punts_a_millorar": ["<aspecte millorable>"],
    "dictamen": "<explicació de la decisió>",
    "accions_requerides": ["<acció si cal>"] o []
}}"""

    def evaluate_proposal(self, request: EvaluationRequest) -> AgentResponse:
        """Avalua una proposta de traducció.

        Args:
            request: Dades de la proposta.

        Returns:
            AgentResponse amb la decisió i brief editorial.
        """
        prompt = f"""Avalua aquesta proposta de traducció:

TÍTOL: {request.titol}
AUTOR: {request.autor}
LLENGUA ORIGINAL: {request.llengua_original}
DESCRIPCIÓ: {request.descripcio}
EXTENSIÓ: {request.extensio_aproximada}
{f"MOTIU: {request.motiu_publicacio}" if request.motiu_publicacio else ""}

Decideix si s'aprova i crea el brief editorial corresponent."""

        return self.process(prompt)

    def approve_final(self, request: FinalApprovalRequest) -> AgentResponse:
        """Decideix l'aprovació final per publicació.

        Args:
            request: Dades de la traducció finalitzada.

        Returns:
            AgentResponse amb el dictamen final.
        """
        preview = request.traduccio[:2000] + "..." if len(request.traduccio) > 2000 else request.traduccio

        prompt = f"""Revisa aquesta traducció per aprovació final:

TÍTOL: {request.titol}
AUTOR: {request.autor}
PUNTUACIÓ REVISOR: {request.puntuacio_revisor}/10
NOTES INCLOSES: {"Sí" if request.notes_incloses else "No"}
GLOSSARI INCLÒS: {"Sí" if request.glossari_inclos else "No"}

MOSTRA DE LA TRADUCCIÓ:
{preview}

Emet el dictamen final per a publicació."""

        return self.process(prompt)

    def create_brief(self, titol: str, autor: str, registre: str) -> AgentResponse:
        """Crea un brief editorial ràpid.

        Args:
            titol: Títol de l'obra.
            autor: Autor de l'obra.
            registre: Registre desitjat.

        Returns:
            AgentResponse amb el brief editorial.
        """
        prompt = f"""Crea un brief editorial complet per a:

TÍTOL: {titol}
AUTOR: {autor}
REGISTRE: {registre}

Inclou instruccions detallades per a tots els agents del pipeline."""

        return self.process(prompt)
