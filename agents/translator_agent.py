"""Agent especialitzat en traducció de textos clàssics grecollatins al català."""

from typing import Literal

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class TranslationRequest(BaseModel):
    """Sol·licitud de traducció amb context opcional."""

    text: str
    source_language: Literal["llatí", "grec", "anglès", "alemany", "francès"] = "llatí"
    author: str | None = None
    work_title: str | None = None
    notes: str | None = None


class TranslatorAgent(BaseAgent):
    """Agent traductor de textos clàssics grecollatins al català.

    Especialitzat en mantenir la fidelitat al text original mentre
    produeix un català literari i natural.
    """

    agent_name: str = "Traductor"

    def __init__(
        self,
        config: AgentConfig | None = None,
        source_language: Literal["llatí", "grec", "anglès", "alemany", "francès"] = "llatí",
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)
        self.source_language = source_language

    @property
    def system_prompt(self) -> str:
        return f"""Ets un traductor expert de textos clàssics en {self.source_language} al català.

OBJECTIU:
Produir traduccions fidels, precises i literàriament excel·lents per a un públic català contemporani.

PRINCIPIS DE TRADUCCIÓ:

1. FIDELITAT AL TEXT ORIGINAL
   - Respecta el significat i les intencions de l'autor antic
   - Mantén l'estructura argumentativa i narrativa
   - Conserva les figures retòriques quan sigui possible

2. CATALÀ LITERARI NATURAL
   - Utilitza un català normatiu i elegant
   - Evita calcs sintàctics del {self.source_language}
   - Adapta les expressions idiomàtiques al català

3. COHERÈNCIA TERMINOLÒGICA
   - Utilitza terminologia consistent per a conceptes clau
   - Respecta les convencions de traducció catalanes establertes
   - Mantén els noms propis en la forma catalana tradicional quan existeixi

4. NOTES DEL TRADUCTOR
   - Indica entre claudàtors [N.T.: ...] quan calgui aclarir context cultural
   - Explica referències mitològiques o històriques si són obscures

FORMAT DE RESPOSTA:
Retorna només la traducció al català, sense comentaris addicionals llevat de les notes del traductor integrades."""

    def translate(self, request: TranslationRequest) -> AgentResponse:
        """Tradueix un text amb context addicional.

        Args:
            request: Sol·licitud de traducció amb metadades.

        Returns:
            AgentResponse amb la traducció.
        """
        self.source_language = request.source_language

        prompt_parts = [f"Tradueix el següent text en {request.source_language} al català:"]

        if request.author or request.work_title:
            context = []
            if request.author:
                context.append(f"Autor: {request.author}")
            if request.work_title:
                context.append(f"Obra: {request.work_title}")
            prompt_parts.append(f"\nContext: {', '.join(context)}")

        if request.notes:
            prompt_parts.append(f"\nNotes addicionals: {request.notes}")

        prompt_parts.append(f"\n\nText original:\n{request.text}")

        return self.process("\n".join(prompt_parts))
