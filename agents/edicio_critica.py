"""Agent d'Edició Crítica per redactar notes a peu de pàgina."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.translator_agent import SupportedLanguage


class FootNote(BaseModel):
    """Nota a peu de pàgina."""

    numero: int
    tipus: Literal["explicativa", "filològica", "històrica", "comparativa", "textual"]
    text_referit: str
    contingut: str
    fonts: list[str] = Field(default_factory=list)


class AnnotationRequest(BaseModel):
    """Sol·licitud d'anotació."""

    text_original: str
    text_traduit: str
    llengua_original: SupportedLanguage = "llatí"
    autor: str
    titol: str
    context_investigador: str | None = None
    nivell_detall: Literal["mínim", "moderat", "acadèmic"] = "moderat"


class EdicioCriticaAgent(BaseAgent):
    """Agent per crear aparats crítics i notes a peu de pàgina.

    Especialitzat en edicions crítiques de textos clàssics amb
    notes explicatives, filològiques i comparatives.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        nivell: Literal["mínim", "moderat", "acadèmic"] = "moderat",
    ) -> None:
        super().__init__(config)
        self.nivell = nivell

    @property
    def system_prompt(self) -> str:
        return f"""Ets un filòleg expert en edicions crítiques de textos clàssics universals.

OBJECTIU:
Crear un aparat crític professional amb notes a peu de pàgina que enriqueixin la lectura.

NIVELL D'ANOTACIÓ: {self.nivell.upper()}

TIPUS DE NOTES:

1. NOTES EXPLICATIVES
   - Aclariments de passatges difícils
   - Context necessari per entendre el text
   - Explicació de costums o institucions
   - NO repetir informació òbvia

2. NOTES FILOLÒGIQUES
   - Problemes de traducció
   - Variants textuals significatives
   - Etimologies rellevants
   - Jocs de paraules intradüibles

3. NOTES HISTÒRIQUES
   - Identificació de personatges
   - Esdeveniments al·ludits
   - Dates i cronologia
   - Dades geogràfiques

4. NOTES COMPARATIVES
   - Paral·lels amb altres obres
   - Fonts de l'autor
   - Influència en obres posteriors
   - Altres traduccions catalanes

5. NOTES TEXTUALS (només nivell acadèmic)
   - Variants manuscrites importants
   - Conjectures d'editors
   - Problemes d'autenticitat

CRITERIS D'ANOTACIÓ:
- MÍNIM: Només notes essencials per a la comprensió bàsica (5-10 per capítol)
- MODERAT: Notes explicatives i històriques principals (15-25 per capítol)
- ACADÈMIC: Aparat crític complet amb variants textuals (30+ per capítol)

FORMAT DE RESPOSTA:
{{
    "text_anotat": "<text amb marcadors [1], [2], etc.>",
    "notes": [
        {{
            "numero": <número>,
            "tipus": "<explicativa|filològica|històrica|comparativa|textual>",
            "text_referit": "<fragment del text que s'anota>",
            "contingut": "<text de la nota>",
            "fonts": ["<referència bibliogràfica si escau>"]
        }}
    ],
    "estadistiques": {{
        "total_notes": <número>,
        "per_tipus": {{
            "explicativa": <número>,
            "filològica": <número>,
            "històrica": <número>,
            "comparativa": <número>,
            "textual": <número>
        }}
    }},
    "passatges_sense_anotar": [
        "<passatge que podria necessitar nota però s'ha omès per no sobrecarregar>"
    ]
}}"""

    def annotate(self, request: AnnotationRequest) -> AgentResponse:
        """Crea notes per a un text.

        Args:
            request: Sol·licitud amb els textos i paràmetres.

        Returns:
            AgentResponse amb el text anotat i notes.
        """
        self.nivell = request.nivell_detall

        prompt_parts = [
            f"Crea notes a peu de pàgina per a aquesta traducció.",
            f"Nivell de detall: {request.nivell_detall}",
            f"Autor: {request.autor}",
            f"Obra: {request.titol}",
            "",
            f"TEXT ORIGINAL ({request.llengua_original.upper()}):",
            request.text_original[:2500] + "..." if len(request.text_original) > 2500 else request.text_original,
            "",
            "TRADUCCIÓ CATALANA:",
            request.text_traduit[:2500] + "..." if len(request.text_traduit) > 2500 else request.text_traduit,
        ]

        if request.context_investigador:
            prompt_parts.extend([
                "",
                "CONTEXT DE L'INVESTIGADOR:",
                request.context_investigador[:1500],
            ])

        return self.process("\n".join(prompt_parts))

    def explain_passage(self, passatge: str, context: str) -> AgentResponse:
        """Explica un passatge difícil en detall.

        Args:
            passatge: Passatge a explicar.
            context: Context de l'obra.

        Returns:
            AgentResponse amb l'explicació detallada.
        """
        prompt = f"""Explica detalladament aquest passatge clàssic:

PASSATGE:
{passatge}

CONTEXT:
{context}

Inclou:
- Interpretació literal
- Interpretacions alternatives
- Dificultats de traducció
- Rellevància en l'obra
- Paral·lels amb altres textos"""

        return self.process(prompt)

    def compare_translations(self, original: str, traduccions: dict[str, str]) -> AgentResponse:
        """Compara diverses traduccions d'un passatge.

        Args:
            original: Text original.
            traduccions: Dict amb traductor -> traducció.

        Returns:
            AgentResponse amb l'anàlisi comparativa.
        """
        import json

        prompt = f"""Compara aquestes traduccions d'un text clàssic:

TEXT ORIGINAL:
{original}

TRADUCCIONS:
{json.dumps(traduccions, ensure_ascii=False, indent=2)}

Analitza:
- Diferències significatives
- Encerts de cada traducció
- Problemes detectats
- Quina s'acosta més a l'original"""

        return self.process(prompt)
