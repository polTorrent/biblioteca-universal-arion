"""Agent Calculador de Costos per estimar el cost del pipeline."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class CostEstimate(BaseModel):
    """Estimació de cost per una etapa."""

    etapa: str
    tokens_entrada: int
    tokens_sortida: int
    cost_usd: float
    model: str


class PipelineCostEstimate(BaseModel):
    """Estimació total del pipeline."""

    etapes: list[CostEstimate]
    total_tokens_entrada: int
    total_tokens_sortida: int
    total_cost_usd: float
    temps_estimat_minuts: int


class CostRequest(BaseModel):
    """Sol·licitud d'estimació de cost."""

    text: str
    etapes: list[str] = Field(
        default_factory=lambda: [
            "consell_editorial",
            "investigador",
            "traductor",
            "corrector",
            "revisor",
            "estil",
            "glossarista",
            "edicio_critica",
            "introduccio",
        ]
    )
    model: str = "claude-sonnet-4-20250514"
    include_epub: bool = True


# Preus per 1M tokens (gener 2025)
MODEL_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-haiku-3-5-20241022": {"input": 0.25, "output": 1.25},
}

# Multiplicadors de tokens per etapa (aproximats)
STAGE_MULTIPLIERS = {
    "pescador": {"input": 0.5, "output": 0.3},
    "consell_editorial": {"input": 1.2, "output": 0.8},
    "investigador": {"input": 1.5, "output": 2.0},
    "traductor": {"input": 1.5, "output": 1.8},
    "corrector": {"input": 1.8, "output": 1.5},
    "revisor": {"input": 2.5, "output": 1.5},
    "estil": {"input": 1.8, "output": 1.5},
    "glossarista": {"input": 1.5, "output": 1.0},
    "edicio_critica": {"input": 2.0, "output": 2.5},
    "introduccio": {"input": 1.5, "output": 3.0},
    "disseny": {"input": 0.5, "output": 0.8},
    "epub": {"input": 1.0, "output": 0.5},
}


class CalculadorCostosAgent(BaseAgent):
    """Agent per estimar costos del pipeline abans d'executar.

    Calcula tokens aproximats i cost en USD per cada etapa.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return """Ets un expert en estimació de costos per a pipelines de processament de text amb LLMs.

OBJECTIU:
Proporcionar estimacions precises del cost d'executar un pipeline de traducció editorial.

FACTORS A CONSIDERAR:

1. LONGITUD DEL TEXT
   - Comptar caràcters/paraules del text original
   - Estimar tokens (≈4 caràcters per token en llatí/grec)
   - El català genera ~10-15% més tokens que l'original

2. ETAPES DEL PIPELINE
   - Cada etapa té un "multiplicador" de tokens
   - Algunes etapes processen el text múltiples vegades
   - Les etapes de revisió són més costoses (entrada: original + traducció)

3. MODEL UTILITZAT
   - Sonnet: $3/1M input, $15/1M output
   - Opus: $15/1M input, $75/1M output
   - Haiku: $0.25/1M input, $1.25/1M output

4. ITERACIONS
   - El revisor pot fer 2-3 passades
   - Cada passada multiplica el cost

FORMAT DE RESPOSTA:
Respon en JSON amb aquesta estructura:
{
    "resum": {
        "paraules_original": <número>,
        "tokens_estimats_original": <número>,
        "total_tokens_entrada": <número>,
        "total_tokens_sortida": <número>,
        "cost_total_usd": <número amb 2 decimals>,
        "temps_estimat_minuts": <número>
    },
    "desglossament": [
        {
            "etapa": "<nom>",
            "tokens_entrada": <número>,
            "tokens_sortida": <número>,
            "cost_usd": <número>
        }
    ],
    "recomanacions": [
        "<suggeriments per reduir costos si cal>"
    ],
    "advertencies": [
        "<avisos sobre textos molt llargs, etc.>"
    ]
}"""

    def estimate(self, request: CostRequest) -> AgentResponse:
        """Estima el cost d'executar el pipeline.

        Args:
            request: Paràmetres de la sol·licitud.

        Returns:
            AgentResponse amb l'estimació detallada.
        """
        word_count = len(request.text.split())
        char_count = len(request.text)

        prompt = f"""Estima el cost d'executar un pipeline de traducció editorial.

TEXT ORIGINAL:
- Paraules: {word_count}
- Caràcters: {char_count}
- Primeres línies: {request.text[:500]}...

ETAPES A EXECUTAR: {', '.join(request.etapes)}
MODEL: {request.model}
INCLOURE EPUB: {request.include_epub}

Calcula el cost total i per etapa."""

        return self.process(prompt)

    def quick_estimate(self, text: str, model: str = "claude-sonnet-4-20250514") -> PipelineCostEstimate:
        """Fa una estimació ràpida sense cridar l'API.

        Args:
            text: Text a processar.
            model: Model a utilitzar.

        Returns:
            PipelineCostEstimate amb els càlculs locals.
        """
        # Estimació de tokens (4 chars per token aproximadament)
        base_tokens = len(text) // 4
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-20250514"])

        etapes = []
        total_input = 0
        total_output = 0

        for stage, multipliers in STAGE_MULTIPLIERS.items():
            input_tokens = int(base_tokens * multipliers["input"])
            output_tokens = int(base_tokens * multipliers["output"])

            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

            etapes.append(CostEstimate(
                etapa=stage,
                tokens_entrada=input_tokens,
                tokens_sortida=output_tokens,
                cost_usd=round(cost, 4),
                model=model,
            ))

            total_input += input_tokens
            total_output += output_tokens

        total_cost = (total_input * pricing["input"] + total_output * pricing["output"]) / 1_000_000

        # Temps estimat: ~2 segons per crida API, ~12 etapes
        temps = max(1, len(STAGE_MULTIPLIERS) * 2 // 60 + 1)

        return PipelineCostEstimate(
            etapes=etapes,
            total_tokens_entrada=total_input,
            total_tokens_sortida=total_output,
            total_cost_usd=round(total_cost, 4),
            temps_estimat_minuts=temps,
        )
