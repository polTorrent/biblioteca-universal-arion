"""Agent Glossarista per crear glossaris i índexs."""

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class GlossaryEntry(BaseModel):
    """Entrada de glossari."""

    terme_original: str
    transliteracio: str | None = None
    traduccio_catalana: str
    categoria: str
    definicio: str
    context_us: str | None = None
    termes_relacionats: list[str] = Field(default_factory=list)


class OnomasticEntry(BaseModel):
    """Entrada d'índex onomàstic."""

    nom: str
    variants: list[str] = Field(default_factory=list)
    tipus: Literal["persona", "lloc", "divinitat", "poble", "institució"]
    descripcio: str
    referencies: list[str] = Field(default_factory=list)


class GlossaryRequest(BaseModel):
    """Sol·licitud de creació de glossari."""

    text: str
    text_original: str | None = None
    llengua_original: Literal["llatí", "grec"] = "llatí"
    categories: list[str] = Field(
        default_factory=lambda: ["filosofia", "política", "militar", "religió", "vida quotidiana"]
    )


class GlossaristaAgent(BaseAgent):
    """Agent per crear glossaris terminològics i índexs onomàstics.

    Assegura consistència terminològica i facilita la comprensió
    de termes especialitzats.
    """

    agent_name: str = "Glossarista"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un lexicògraf expert en terminologia clàssica grecollatina.

OBJECTIU:
Crear glossaris complets i índexs onomàstics per a edicions de textos clàssics en català.

TIPUS D'ENTRADES:

1. TERMES TÈCNICS
   - Filosofia: logos, physis, eudaimonia, virtus, ratio...
   - Política: polis, res publica, senatus, demos, civitas...
   - Militar: legió, falange, cohors, strategós...
   - Religió: numen, pietas, sacerdos, theos, hiereus...
   - Retòrica: ethos, pathos, logos, enthymema...

2. CONCEPTES CULTURALS
   - Institucions: magistratures, assemblees, tribunals
   - Costums: banquets, jocs, rituals
   - Mesures: estadi, talent, as, sesterci
   - Calendari: calendes, nones, idus

3. NOMS PROPIS
   - Persones: forma catalana tradicional si existeix
   - Llocs: nom antic i equivalent modern
   - Pobles: gentilicis i localizació
   - Divinitats: nom grec/llatí i atributs

CRITERIS DE TRADUCCIÓ TERMINOLÒGICA:
- Preferir traduccions catalanes tradicionals si existeixen
- Mantenir el terme original entre parèntesis si és molt específic
- Ser consistent: un terme = una traducció
- Indicar si hi ha debat terminològic

FORMAT DE RESPOSTA:
{{
    "glossari": [
        {{
            "terme_original": "<terme en grec/llatí>",
            "transliteracio": "<si és grec>",
            "traduccio_catalana": "<traducció recomanada>",
            "categoria": "<filosofia|política|militar|religió|retòrica|altre>",
            "definicio": "<definició clara i concisa>",
            "context_us": "<com s'usa en aquest text>",
            "termes_relacionats": ["<terme>"],
            "nota": "<observacions si cal>"
        }}
    ],
    "index_onomastic": [
        {{
            "nom": "<nom principal>",
            "variants": ["<altres formes>"],
            "tipus": "<persona|lloc|divinitat|poble|institució>",
            "descripcio": "<qui o què és>",
            "referencies": ["<on apareix al text>"]
        }}
    ],
    "estadistiques": {{
        "total_termes": <número>,
        "total_noms": <número>,
        "categories": {{"<categoria>": <número>}}
    }},
    "recomanacions_traductor": [
        "<consell per mantenir consistència>"
    ]
}}"""

    def create_glossary(self, request: GlossaryRequest) -> AgentResponse:
        """Crea un glossari per a un text.

        Args:
            request: Sol·licitud amb el text i categories.

        Returns:
            AgentResponse amb el glossari complet.
        """
        prompt_parts = [
            "Crea un glossari complet per a aquest text clàssic.",
            f"Llengua original: {request.llengua_original}",
            f"Categories a incloure: {', '.join(request.categories)}",
            "",
            "TEXT TRADUÏT:",
            request.text[:4000] + "..." if len(request.text) > 4000 else request.text,
        ]

        if request.text_original:
            prompt_parts.extend([
                "",
                "TEXT ORIGINAL:",
                request.text_original[:2000] + "..." if len(request.text_original) > 2000 else request.text_original,
            ])

        return self.process("\n".join(prompt_parts))

    def propose_translation(self, terme: str, context: str) -> AgentResponse:
        """Proposa una traducció per a un terme difícil.

        Args:
            terme: Terme a traduir.
            context: Context d'ús.

        Returns:
            AgentResponse amb les opcions de traducció.
        """
        prompt = f"""Proposa traduccions al català per al terme: {terme}

CONTEXT D'ÚS:
{context}

Retorna JSON amb:
- opcions: [{{traduccio, justificacio, adequacio}}]
- recomanacio: <millor opció>
- termes_a_evitar: [<falsos amics>]"""

        return self.process(prompt)

    def check_consistency(self, glossari: dict, text: str) -> AgentResponse:
        """Verifica la consistència terminològica d'un text.

        Args:
            glossari: Glossari de referència.
            text: Text a verificar.

        Returns:
            AgentResponse amb les inconsistències detectades.
        """
        import json

        prompt = f"""Verifica que aquest text segueix el glossari de manera consistent.

GLOSSARI:
{json.dumps(glossari, ensure_ascii=False, indent=2)[:2000]}

TEXT:
{text[:3000]}

Identifica:
- Termes traduïts de manera inconsistent
- Termes que falten al glossari
- Usos incorrectes segons el glossari"""

        return self.process(prompt)
