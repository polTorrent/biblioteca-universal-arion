"""Agent especialitzat en traducció de textos clàssics al català."""

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# Tipus de llengües suportades
SupportedLanguage = Literal["llatí", "grec", "anglès", "alemany", "francès", "japonès", "xinès"]


class TranslationRequest(BaseModel):
    """Sol·licitud de traducció amb context opcional."""

    text: str
    source_language: SupportedLanguage = "llatí"
    author: str | None = None
    work_title: str | None = None
    notes: str | None = None
    genre: str | None = None  # conte, poesia, filosofia, teatre


class TranslatorAgent(BaseAgent):
    """Agent traductor de textos clàssics al català.

    Especialitzat en mantenir la fidelitat al text original mentre
    produeix un català literari i natural. Suporta llengües clàssiques
    occidentals i orientals.
    """

    agent_name: str = "Traductor"

    # Prompts específics per llengua
    _JAPANESE_PROMPT = """Ets un traductor expert de literatura japonesa clàssica i moderna al català.

OBJECTIU:
Produir traduccions fidels, precises i literàriament excel·lents per a un públic català contemporani.

PRINCIPIS DE TRADUCCIÓ PER AL JAPONÈS:

1. FIDELITAT AL TEXT ORIGINAL
   - Respecta el significat i les intencions de l'autor
   - Mantén l'estructura narrativa i el to (formal, col·loquial, poètic)
   - Conserva les figures retòriques i l'estil característic
   - Preserva l'ambigüitat quan sigui intencionada

2. CATALÀ LITERARI NATURAL
   - Utilitza un català normatiu i elegant
   - Evita calcs sintàctics del japonès (SOV a SVO)
   - Adapta les expressions idiomàtiques i onomatopeies
   - Recrea el ritme i la cadència quan sigui possible

3. ROMANITZACIÓ (Sistema Hepburn modificat)
   - shi (no si), tsu, chi, fu
   - Partícules: wo esdevé o, ha esdevé wa
   - Vocals llargues: usar macrons (ō, ū)
   - Noms propis: ordre japonès (cognom + nom)
     Exemple: Akutagawa Ryūnosuke (no Ryūnosuke Akutagawa)

4. TERMES CULTURALS JAPONESOS
   - Primera aparició: terme japonès en cursiva + traducció o explicació
   - Aparicions posteriors: només el terme japonès en cursiva
   - Exemples:
     * Vestimenta: kariginu, hakama, uchigi (mantenir en japonès)
     * Arquitectura: fusuma, shōji, tatami (mantenir en japonès)
     * Rangs: -sama, -dono, -san (adaptar segons context)
   - Mai traduir literalment termes sense equivalent cultural

5. HONORÍFICS I REGISTRE
   - Adaptar el keigo (llenguatge honorífic) al registre català adequat
   - Mantenir les diferències de to entre personatges
   - Usar vós per a respecte formal, tu per a familiaritat

6. NOTES DEL TRADUCTOR
   - Usar notes a peu de pàgina [^n] per a context cultural imprescindible
   - Explicar referències històriques, literàries o mitològiques
   - No sobrecarregar: només quan sigui necessari per a la comprensió

7. CRITERIS PER GÈNERE
   - Narrativa: mantenir la veu del narrador, fluïdesa
   - Poesia: prioritzar sentit + ritme sobre literalitat
   - Teatre: oralitat natural, actituds dels personatges
   - Filosofia: precisió terminològica

FORMAT DE RESPOSTA:
Retorna només la traducció al català, amb notes a peu de pàgina integrades [^n] quan calgui."""

    _DEFAULT_PROMPT = """Ets un traductor expert de textos clàssics en {source_language} al català.

OBJECTIU:
Produir traduccions fidels, precises i literàriament excel·lents per a un públic català contemporani.

PRINCIPIS DE TRADUCCIÓ:

1. FIDELITAT AL TEXT ORIGINAL
   - Respecta el significat i les intencions de l'autor antic
   - Mantén l'estructura argumentativa i narrativa
   - Conserva les figures retòriques quan sigui possible

2. CATALÀ LITERARI NATURAL
   - Utilitza un català normatiu i elegant
   - Evita calcs sintàctics del {source_language}
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

    def __init__(
        self,
        config: AgentConfig | None = None,
        source_language: SupportedLanguage = "llatí",
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)
        self.source_language = source_language

    @property
    def system_prompt(self) -> str:
        if self.source_language == "japonès":
            return self._JAPANESE_PROMPT
        return self._DEFAULT_PROMPT.format(source_language=self.source_language)

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

        if request.genre:
            prompt_parts.append(f"\nGènere: {request.genre}")

        if request.notes:
            prompt_parts.append(f"\nNotes addicionals: {request.notes}")

        prompt_parts.append(f"\n\nText original:\n{request.text}")

        return self.process("\n".join(prompt_parts))
