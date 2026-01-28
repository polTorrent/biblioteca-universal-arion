"""Agent d'Estil Literari per millorar la fluïdesa i naturalitat del català.

DEPRECATED: Aquest agent està deprecat. Utilitzeu PerfeccionamentAgent en el seu lloc.
El PerfeccionamentAgent ofereix una fusió holística de naturalització, correcció i estil.
"""

import warnings
from typing import Literal

from pydantic import BaseModel

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class StyleNote(BaseModel):
    """Nota d'edició d'estil."""

    fragment_original: str
    fragment_nou: str
    justificacio: str


class StyleRequest(BaseModel):
    """Sol·licitud d'edició d'estil."""

    text: str
    registre: Literal["acadèmic", "divulgatiu", "literari"] = "literari"
    preservar_veu: bool = True
    autor_original: str | None = None
    context: str | None = None


class EstilAgent(BaseAgent):
    """Agent d'estil literari per polir traduccions.

    Millora la fluïdesa i naturalitat del català mentre
    preserva la veu i el to de l'autor original.

    .. deprecated::
        Utilitzeu :class:`PerfeccionamentAgent` en el seu lloc.
        Aquest agent es manté per compatibilitat amb pipelines antics.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        registre: Literal["acadèmic", "divulgatiu", "literari"] = "literari",
    ) -> None:
        warnings.warn(
            "EstilAgent està deprecat. Utilitzeu PerfeccionamentAgent en el seu lloc.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.registre = registre

    @property
    def system_prompt(self) -> str:
        return f"""Ets un editor literari expert en català amb un domini exquisit de l'estil i el ritme de la llengua.

OBJECTIU:
Polir textos traduïts per aconseguir un català literari excel·lent, natural i fluid, tot preservant la veu de l'autor original.

REGISTRE ACTUAL: {self.registre.upper()}

PRINCIPIS D'EDICIÓ D'ESTIL:

1. FLUÏDESA I RITME
   - Alterna frases llargues i curtes per crear ritme
   - Evita acumulacions de subordinades
   - Cuida les transicions entre paràgrafs
   - Respecta el ritme de la prosa clàssica

2. NATURALITAT
   - Prioritza l'ordre natural del català (SVO)
   - Evita hipèrbatons forçats
   - Utilitza connectors variats (però, tanmateix, nogensmenys, amb tot)
   - Tria la paraula més precisa i sonora

3. EVITAR REPETICIONS
   - Substitueix repeticions per sinònims o pronoms
   - Varia els verbs introductors (dir, afirmar, sostenir, declarar)
   - Alterna estructures sintàctiques equivalents

4. REGISTRE SEGONS TIPUS:
   - ACADÈMIC: Precisió terminològica, to objectiu, citacions formals
   - DIVULGATIU: Claredat, exemples, to accessible però rigorós
   - LITERARI: Elegància, ritme, riquesa lèxica, sensibilitat estètica

5. PRESERVAR LA VEU ORIGINAL
   - Mantén el to de l'autor (irònic, solemne, didàctic, líric)
   - Respecta les figures retòriques de l'original
   - No modernitzis excessivament el lèxic si l'obra és antiga

LÈXIC LITERARI CATALÀ:
Prioritza paraules com: tanmateix, nogensmenys, car, puix, altrament, endemés,
àdhuc, baldament, gairebé, escaient, adient, rauxa, seny, enyorança, vetust...

FORMAT DE RESPOSTA:
Respon en JSON amb aquesta estructura:
{{
    "text_polit": "<text complet amb les millores d'estil>",
    "notes_edicio": [
        {{
            "fragment_original": "<fragment abans>",
            "fragment_nou": "<fragment després>",
            "justificacio": "<per què s'ha canviat>"
        }}
    ],
    "millores_aplicades": {{
        "fluïdesa": <número de canvis>,
        "lèxic": <número de canvis>,
        "ritme": <número de canvis>,
        "repeticions": <número de canvis>
    }},
    "to_detectat": "<irònic|solemne|didàctic|líric|neutre|altre>",
    "observacions": "<comentari sobre l'estil general del text>"
}}"""

    def polish(self, request: StyleRequest) -> AgentResponse:
        """Poleix l'estil d'un text.

        Args:
            request: Sol·licitud amb el text i preferències d'estil.

        Returns:
            AgentResponse amb el text polit i notes d'edició.
        """
        self.registre = request.registre

        prompt_parts = [
            f"Poleix l'estil del següent text traduït d'un clàssic universal.",
            f"Registre desitjat: {request.registre}",
        ]

        if request.preservar_veu:
            prompt_parts.append("IMPORTANT: Preserva la veu i el to de l'autor original.")

        if request.autor_original:
            prompt_parts.append(f"Autor original: {request.autor_original}")

        if request.context:
            prompt_parts.append(f"Context: {request.context}")

        prompt_parts.extend(["", "TEXT:", request.text])

        return self.process("\n".join(prompt_parts))

    def analyze_style(self, text: str) -> AgentResponse:
        """Analitza l'estil d'un text sense modificar-lo.

        Args:
            text: Text a analitzar.

        Returns:
            AgentResponse amb l'anàlisi estilística.
        """
        prompt = f"""Analitza l'estil d'aquest text SENSE modificar-lo.

TEXT:
{text}

Retorna JSON amb:
- to_general: <descripció del to>
- punts_forts: [<aspectes positius>]
- punts_febles: [<aspectes millorables>]
- suggeriments: [<recomanacions concretes>]"""

        return self.process(prompt)
