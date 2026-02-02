"""Agent de Correcció Normativa amb LanguageTool.

Aplica correccions ortogràfiques, gramaticals i de puntuació
automàticament al text traduït.
"""

from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from utils.logger import get_logger

try:
    from utils.corrector_linguistic import (
        CorrectorLinguistic,
        ResultatCorreccio,
        CategoriaError,
        LANGUAGETOOL_DISPONIBLE,
    )
except ImportError:
    LANGUAGETOOL_DISPONIBLE = False
    ResultatCorreccio = None
    CategoriaError = None


class ConfiguracioCorrector(BaseModel):
    """Configuració del corrector normatiu."""

    # Categories a corregir automàticament (les altres només s'informen)
    categories_auto: list[str] = Field(
        default=["ortografia", "tipografia", "puntuacio"],
        description="Categories d'errors a corregir automàticament"
    )

    # Categories a mostrar però NO corregir (requereixen revisió humana)
    categories_informe: list[str] = Field(
        default=["gramatica", "estil", "barbarisme"],
        description="Categories a informar però no corregir"
    )

    # Llindar de confiança per aplicar correcció
    min_confianca: float = Field(
        default=0.8,
        description="Confiança mínima per aplicar correcció automàtica"
    )

    # Màxim de correccions per chunk (seguretat)
    max_correccions_chunk: int = Field(
        default=50,
        description="Màxim de correccions per chunk"
    )


class ResultatCorreccioNormativa(BaseModel):
    """Resultat de la correcció normativa."""

    text_original: str
    text_corregit: str

    # Estadístiques
    correccions_aplicades: int = 0
    errors_informats: int = 0
    puntuacio_inicial: float = 10.0
    puntuacio_final: float = 10.0

    # Detall de correccions
    correccions: list[dict] = Field(default_factory=list)
    avisos: list[dict] = Field(default_factory=list)

    # Metadades
    languagetool_disponible: bool = True


class CorrectorNormatiuAgent(BaseAgent):
    """Agent de correcció normativa amb LanguageTool.

    Aplica correccions automàtiques per a certes categories (ortografia,
    puntuació) i informa sobre altres (gramàtica, estil) sense modificar-les.
    """

    agent_name = "CorrectorNormatiu"

    def __init__(
        self,
        config: AgentConfig | None = None,
        configuracio: ConfiguracioCorrector | None = None,
        logger=None,
    ):
        super().__init__(config, logger)
        self.configuracio = configuracio or ConfiguracioCorrector()
        self._corrector: CorrectorLinguistic | None = None

    @property
    def corrector(self) -> CorrectorLinguistic | None:
        """Lazy initialization del corrector."""
        if self._corrector is None and LANGUAGETOOL_DISPONIBLE:
            self._corrector = CorrectorLinguistic()
        return self._corrector

    @property
    def system_prompt(self) -> str:
        """No usat - aquest agent no crida a Claude."""
        return ""

    def corregir(self, text: str) -> ResultatCorreccioNormativa:
        """Aplica correccions normatives al text.

        Args:
            text: Text a corregir.

        Returns:
            ResultatCorreccioNormativa amb text corregit i estadístiques.
        """
        if not LANGUAGETOOL_DISPONIBLE or not self.corrector:
            self.logger.log_warning(
                self.agent_name,
                "LanguageTool no disponible, retornant text sense canvis"
            )
            return ResultatCorreccioNormativa(
                text_original=text,
                text_corregit=text,
                languagetool_disponible=False,
            )

        # Obtenir tots els errors (sense auto-corregir encara)
        resultat_lt = self.corrector.corregir(text, auto_corregir=False)
        puntuacio_inicial = resultat_lt.puntuacio_normativa

        # Separar errors per categoria
        errors_auto = []  # Es corregiran
        errors_informe = []  # Només s'informaran

        for error in resultat_lt.errors:
            categoria_str = error.categoria.value

            if categoria_str in self.configuracio.categories_auto:
                errors_auto.append(error)
            elif categoria_str in self.configuracio.categories_informe:
                errors_informe.append(error)

        # Aplicar correccions automàtiques (de darrere a davant per no desplaçar índexs)
        text_corregit = text
        correccions_aplicades = []

        # Ordenar per posició descendent
        errors_auto_sorted = sorted(
            errors_auto,
            key=lambda e: e.posicio_inici,
            reverse=True
        )

        for error in errors_auto_sorted[:self.configuracio.max_correccions_chunk]:
            if not error.suggeriments:
                continue

            # Aplicar el primer suggeriment
            suggeriment = error.suggeriments[0]

            text_corregit = (
                text_corregit[:error.posicio_inici] +
                suggeriment +
                text_corregit[error.posicio_final:]
            )

            correccions_aplicades.append({
                "categoria": error.categoria.value,
                "original": error.text_original,
                "corregit": suggeriment,
                "posicio": error.posicio_inici,
            })

        # Recalcular puntuació amb text corregit
        if correccions_aplicades:
            resultat_final = self.corrector.corregir(text_corregit, auto_corregir=False)
            puntuacio_final = resultat_final.puntuacio_normativa
        else:
            puntuacio_final = puntuacio_inicial

        # Preparar avisos (errors no corregits)
        avisos = [
            {
                "categoria": e.categoria.value,
                "text": e.text_original,
                "missatge": e.missatge,
                "suggeriments": e.suggeriments[:3],
            }
            for e in errors_informe
        ]

        # Logging
        if correccions_aplicades:
            self.logger.log_info(
                self.agent_name,
                f"Aplicades {len(correccions_aplicades)} correccions "
                f"(puntuació: {puntuacio_inicial:.1f} → {puntuacio_final:.1f})"
            )

        if avisos:
            self.logger.log_warning(
                self.agent_name,
                f"{len(avisos)} avisos de gramàtica/estil (revisió humana recomanada)"
            )

        return ResultatCorreccioNormativa(
            text_original=text,
            text_corregit=text_corregit,
            correccions_aplicades=len(correccions_aplicades),
            errors_informats=len(avisos),
            puntuacio_inicial=puntuacio_inicial,
            puntuacio_final=puntuacio_final,
            correccions=correccions_aplicades,
            avisos=avisos,
            languagetool_disponible=True,
        )

    def process(self, text: str, **kwargs: Any) -> AgentResponse:
        """Interfície estàndard d'agent (wrapper de corregir).

        Nota: Les metadades detallades (correccions, avisos) es poden obtenir
        directament amb el mètode corregir().
        """
        resultat = self.corregir(text)

        return AgentResponse(
            content=resultat.text_corregit,
            model="LanguageTool",
            usage={"input_tokens": 0, "output_tokens": 0},
            duration_seconds=0.0,
            cost_eur=0.0,
        )
