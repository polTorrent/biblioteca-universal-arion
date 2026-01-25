"""Agent especialitzat en revisió de traduccions de textos clàssics."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class IssueSeverity(str, Enum):
    """Gravetat dels problemes detectats."""

    CRITICAL = "crític"
    MAJOR = "major"
    MINOR = "menor"
    SUGGESTION = "suggeriment"


class ReviewIssue(BaseModel):
    """Un problema detectat durant la revisió."""

    severity: IssueSeverity
    category: str
    description: str
    original_segment: str | None = None
    suggested_fix: str | None = None


class ReviewRequest(BaseModel):
    """Sol·licitud de revisió amb text original i traducció."""

    original_text: str
    translated_text: str
    source_language: Literal["llatí", "grec", "anglès", "alemany", "francès"] = "llatí"
    author: str | None = None
    work_title: str | None = None


class ReviewerAgent(BaseAgent):
    """Agent revisor de traduccions de textos clàssics.

    Analitza la qualitat de les traduccions verificant fidelitat,
    correcció lingüística i qualitat literària.
    """

    agent_name: str = "Revisor"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un revisor expert de traduccions de textos clàssics grecollatins al català.

OBJECTIU:
Avaluar i millorar traduccions garantint fidelitat, correcció i qualitat literària.

CRITERIS DE REVISIÓ:

1. FIDELITAT AL TEXT ORIGINAL
   - Verifica que el significat es preserva correctament
   - Detecta omissions o addicions injustificades
   - Comprova la precisió terminològica

2. CORRECCIÓ LINGÜÍSTICA
   - Ortografia i gramàtica catalanes normatives
   - Sintaxi natural i fluïda
   - Puntuació adequada

3. QUALITAT LITERÀRIA
   - Estil apropiat al registre de l'original
   - Ritme i fluïdesa del text català
   - Coherència en el to narratiu

4. COHERÈNCIA TERMINOLÒGICA
   - Consistència en la traducció de termes clau
   - Ús apropiat de noms propis
   - Tractament uniforme de conceptes culturals

FORMAT DE RESPOSTA:
Respon en format JSON amb l'estructura següent:
{
    "puntuació_global": <1-10>,
    "resum": "<avaluació general en 2-3 frases>",
    "problemes": [
        {
            "gravetat": "<crític|major|menor|suggeriment>",
            "categoria": "<fidelitat|gramàtica|estil|terminologia>",
            "descripció": "<descripció del problema>",
            "segment_original": "<fragment afectat o null>",
            "correcció_suggerida": "<proposta de millora o null>"
        }
    ],
    "text_revisat": "<traducció completa amb les correccions aplicades>"
}"""

    def review(self, request: ReviewRequest) -> AgentResponse:
        """Revisa una traducció comparant-la amb l'original.

        Args:
            request: Sol·licitud amb text original i traducció.

        Returns:
            AgentResponse amb l'anàlisi en format JSON.
        """
        prompt_parts = [
            f"Revisa la següent traducció del {request.source_language} al català."
        ]

        if request.author or request.work_title:
            context = []
            if request.author:
                context.append(f"Autor: {request.author}")
            if request.work_title:
                context.append(f"Obra: {request.work_title}")
            prompt_parts.append(f"\nContext: {', '.join(context)}")

        prompt_parts.extend([
            f"\n\nTEXT ORIGINAL ({request.source_language.upper()}):",
            request.original_text,
            "\nTRADUCCIÓ A REVISAR:",
            request.translated_text,
        ])

        return self.process("\n".join(prompt_parts))

    def quick_check(self, translated_text: str) -> AgentResponse:
        """Fa una revisió ràpida només del text català sense l'original.

        Args:
            translated_text: Text traduït a revisar.

        Returns:
            AgentResponse amb correccions bàsiques.
        """
        prompt = f"""Revisa aquest text català traduït d'un clàssic grecollatí.
Centra't només en correcció lingüística i qualitat literària.

TEXT:
{translated_text}"""

        return self.process(prompt)
