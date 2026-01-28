"""Agent Corrector IEC per a correcció ortogràfica i gramatical.

DEPRECATED: Aquest agent està deprecat. Utilitzeu PerfeccionamentAgent en el seu lloc.
El PerfeccionamentAgent ofereix una fusió holística de naturalització, correcció i estil.
"""

import warnings
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class CorrectionItem(BaseModel):
    """Una correcció individual."""

    original: str
    corregit: str
    tipus: Literal["ortografia", "gramàtica", "puntuació", "barbarisme", "estil"]
    explicacio: str


class CorrectionRequest(BaseModel):
    """Sol·licitud de correcció."""

    text: str
    nivell: Literal["relaxat", "normal", "estricte"] = "normal"


class CorrectorAgent(BaseAgent):
    """Agent corrector segons normativa IEC.

    Especialitzat en correcció ortogràfica, gramatical i de puntuació
    seguint les normes de l'Institut d'Estudis Catalans.

    .. deprecated::
        Utilitzeu :class:`PerfeccionamentAgent` en el seu lloc.
        Aquest agent es manté per compatibilitat amb pipelines antics.
    """

    agent_name: str = "Corrector"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        warnings.warn(
            "CorrectorAgent està deprecat. Utilitzeu PerfeccionamentAgent en el seu lloc.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un corrector expert en llengua catalana segons la normativa de l'Institut d'Estudis Catalans (IEC).

OBJECTIU:
Corregir textos catalans garantint la màxima correcció lingüística sense alterar-ne el sentit ni l'estil.

ÀREES DE CORRECCIÓ:

1. ORTOGRAFIA
   - Accentuació (accent obert/tancat, diacrítics)
   - Apòstrofs i contraccions (l', d', al, del, pel, cal)
   - Guionets en compostos i prefixos
   - Majúscules i minúscules
   - Dièresi (raïm, veïna, conduïa)

2. GRAMÀTICA
   - Concordança de gènere i nombre
   - Règim verbal (preposicions correctes)
   - Ús de pronoms febles (em, et, es, ens, us)
   - Combinacions pronominals (me'l, te la, se'n)
   - Verbs pronominals vs. no pronominals

3. PUNTUACIÓ
   - Comes: vocatius, incisos, subordinades
   - Punt i coma en enumeracions complexes
   - Dos punts abans de citacions
   - Guions llargs (—) per a incisos
   - Cometes llatines («») per a citacions

4. BARBARISMES I CALCS
   - Castellanismes lèxics (doncs no *pues, mentre no *mientras)
   - Calcs sintàctics (evitar "el que" castellà)
   - Falsos amics (assistir ≠ asistir)
   - Locucions incorrectes (a pesar de → malgrat)

5. ESTIL NORMATIU
   - Preferència per formes genuïnes
   - Evitar pleonasmes
   - Ordre natural de la frase catalana

FORMAT DE RESPOSTA:
Respon en JSON amb aquesta estructura:
{
    "text_corregit": "<text complet amb totes les correccions aplicades>",
    "correccions": [
        {
            "original": "<fragment original>",
            "corregit": "<fragment corregit>",
            "tipus": "<ortografia|gramàtica|puntuació|barbarisme|estil>",
            "explicacio": "<breu explicació de la norma aplicada>"
        }
    ],
    "estadistiques": {
        "total_correccions": <número>,
        "per_tipus": {
            "ortografia": <número>,
            "gramàtica": <número>,
            "puntuació": <número>,
            "barbarisme": <número>,
            "estil": <número>
        }
    },
    "qualitat_inicial": <1-10>,
    "resum": "<resum breu de les correccions principals>"
}

Si el text és correcte, retorna el text sense canvis i una llista buida de correccions."""

    def correct(self, request: CorrectionRequest) -> AgentResponse:
        """Corregeix un text segons la normativa IEC.

        Args:
            request: Sol·licitud amb el text i nivell d'exigència.

        Returns:
            AgentResponse amb el text corregit i llista de correccions.
        """
        prompt = f"""Corregeix el següent text en català.
Nivell d'exigència: {request.nivell}

TEXT:
{request.text}"""

        return self.process(prompt)

    def check_specific(self, text: str, aspecte: str) -> AgentResponse:
        """Revisa un aspecte específic del text.

        Args:
            text: Text a revisar.
            aspecte: Aspecte concret (puntuació, concordances, etc.)

        Returns:
            AgentResponse amb l'anàlisi específica.
        """
        prompt = f"""Revisa NOMÉS l'aspecte següent del text: {aspecte}

TEXT:
{text}

Retorna només les correccions relacionades amb {aspecte}."""

        return self.process(prompt)
