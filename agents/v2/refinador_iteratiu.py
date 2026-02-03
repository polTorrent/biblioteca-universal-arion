"""Refinador Iteratiu v2.

Sistema de refinament que millora iterativament una traducció basant-se
en el feedback dimensional (Fidelitat, Veu de l'Autor, Fluïdesa).

El flux és:
1. Avaluar traducció actual
2. Si no aprovat, refinar segons feedback prioritzat
3. Repetir fins a aprovació o màx iteracions
4. Retornar millor versió + historial
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent, extract_json_from_text
from agents.v2.models import (
    ContextAvaluacio,
    FeedbackFusionat,
    LlindarsAvaluacio,
    LLINDARS_DEFAULT,
)
from agents.v2.avaluador_dimensional import AvaluadorDimensional

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# =============================================================================
# MODELS
# =============================================================================

class IteracioRefinament(BaseModel):
    """Registre d'una iteració de refinament."""

    numero: int = Field(..., description="Número d'iteració (1, 2, 3...)")
    traduccio_entrada: str = Field(..., description="Traducció abans del refinament")
    traduccio_sortida: str = Field(..., description="Traducció després del refinament")
    avaluacio: FeedbackFusionat = Field(..., description="Avaluació de l'entrada")
    canvis_aplicats: list[str] = Field(
        default_factory=list,
        description="Descripció dels canvis aplicats"
    )
    dimensio_prioritzada: str | None = Field(
        default=None,
        description="Dimensió que s'ha prioritzat en aquesta iteració"
    )


class ResultatRefinament(BaseModel):
    """Resultat complet del procés de refinament."""

    traduccio_inicial: str = Field(..., description="Traducció abans de refinar")
    traduccio_final: str = Field(..., description="Millor traducció obtinguda")

    aprovat: bool = Field(default=False, description="Si ha passat els llindars")
    iteracions_realitzades: int = Field(default=0)
    max_iteracions: int = Field(default=3)

    # Avaluacions
    avaluacio_inicial: FeedbackFusionat | None = None
    avaluacio_final: FeedbackFusionat | None = None

    # Historial
    historial: list[IteracioRefinament] = Field(default_factory=list)

    # Metadades
    millora_aconseguida: float = Field(
        default=0.0,
        description="Diferència entre puntuació final i inicial"
    )
    requereix_revisio_humana: bool = Field(
        default=False,
        description="Si cal revisió humana després del refinament"
    )
    avisos: list[str] = Field(default_factory=list)

    def resum(self) -> str:
        """Retorna un resum llegible del refinament."""
        estat = "APROVAT" if self.aprovat else "NO APROVAT"
        linies = [
            f"═══ RESULTAT REFINAMENT ({estat}) ═══",
            f"Iteracions: {self.iteracions_realitzades}/{self.max_iteracions}",
        ]

        if self.avaluacio_inicial and self.avaluacio_final:
            linies.append(f"\nPuntuació inicial: {self.avaluacio_inicial.puntuacio_global:.1f}/10")
            linies.append(f"Puntuació final:   {self.avaluacio_final.puntuacio_global:.1f}/10")
            linies.append(f"Millora: {self.millora_aconseguida:+.1f}")

        if self.historial:
            linies.append("\nHistorial:")
            for it in self.historial:
                dim = it.dimensio_prioritzada or "general"
                puntuacio = it.avaluacio.puntuacio_global
                linies.append(f"  {it.numero}. [{dim}] {puntuacio:.1f}/10 → refinat")

        if self.requereix_revisio_humana:
            linies.append("\n⚠ REQUEREIX REVISIÓ HUMANA")

        if self.avisos:
            linies.append("\nAvisos:")
            for a in self.avisos:
                linies.append(f"  • {a}")

        return "\n".join(linies)


# =============================================================================
# AGENT REFINADOR
# =============================================================================

class AgentRefinador(BaseAgent):
    """Agent que refina una traducció basant-se en feedback dimensional."""

    agent_name: str = "Refinador"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Millora aquesta traducció basant-te en el feedback.

REGLES:
- REFINA, no reescriguis des de zero
- Mantén el que funciona bé
- Canvia NOMÉS el que el feedback indica
- Ha de sonar NATURAL en català, no a traducció

FORMAT JSON:
{
    "traduccio_refinada": "<TEXT COMPLET REFINAT>",
    "canvis_aplicats": ["canvi 1", "canvi 2"],
    "justificacio": "<per què millora>",
    "confianca": <0.0-1.0>
}"""

    def refinar(
        self,
        traduccio_actual: str,
        text_original: str,
        feedback: FeedbackFusionat,
        llengua_origen: str = "llatí",
        genere: str = "narrativa",
    ) -> tuple[str, list[str]]:
        """Refina una traducció basant-se en el feedback.

        Args:
            traduccio_actual: Traducció a refinar.
            text_original: Text original per referència.
            feedback: Feedback dimensional amb instruccions.
            llengua_origen: Llengua del text original.
            genere: Gènere literari.

        Returns:
            Tupla (traducció_refinada, llista_de_canvis).
        """
        prompt = self._construir_prompt(
            traduccio_actual=traduccio_actual,
            text_original=text_original,
            feedback=feedback,
            llengua_origen=llengua_origen,
            genere=genere,
        )

        response = self.process(prompt)

        # Parsejar resposta (robust)
        data = extract_json_from_text(response.content)
        if data and data.get("traduccio_refinada"):
            traduccio_refinada = data.get("traduccio_refinada", traduccio_actual)
            canvis = data.get("canvis_aplicats", [])
            return traduccio_refinada, canvis

        # Intentar extreure traducció del text
        self.log_warning("No s'ha pogut parsejar JSON, extraient text")
        return self._extreure_traduccio(response.content, traduccio_actual), []

    def _construir_prompt(
        self,
        traduccio_actual: str,
        text_original: str,
        feedback: FeedbackFusionat,
        llengua_origen: str,
        genere: str,
    ) -> str:
        """Construeix el prompt per al refinament."""
        seccions = []

        seccions.append(f"REFINA la següent traducció del {llengua_origen} al català.")
        seccions.append(f"Gènere: {genere}")

        # Puntuacions actuals
        seccions.append("\n" + "="*60)
        seccions.append("PUNTUACIONS ACTUALS")
        seccions.append("="*60)
        seccions.append(f"Puntuació global: {feedback.puntuacio_global:.1f}/10")
        seccions.append(f"  • Fidelitat:  {feedback.puntuacio_fidelitat:.1f}/10 (pes 25%)")
        seccions.append(f"  • Veu autor:  {feedback.puntuacio_veu_autor:.1f}/10 (pes 40%)")
        seccions.append(f"  • Fluïdesa:   {feedback.puntuacio_fluidesa:.1f}/10 (pes 35%)")

        # Prioritats
        if feedback.prioritat_1:
            seccions.append(f"\nPRIORITAT DE MILLORA: {feedback.prioritat_1.upper()}")

        # Instruccions de refinament
        seccions.append("\n" + "="*60)
        seccions.append("INSTRUCCIONS DE REFINAMENT (SEGUEIX-LES)")
        seccions.append("="*60)
        seccions.append(feedback.instruccions_refinament)

        # Text original
        seccions.append("\n" + "="*60)
        seccions.append(f"TEXT ORIGINAL ({llengua_origen.upper()})")
        seccions.append("="*60)
        seccions.append(text_original[:5000])

        # Traducció a refinar
        seccions.append("\n" + "="*60)
        seccions.append("TRADUCCIÓ A REFINAR")
        seccions.append("="*60)
        seccions.append(traduccio_actual)

        # Instrucció final
        seccions.append("\n" + "="*60)
        seccions.append("Refina la traducció aplicant les correccions indicades.")
        seccions.append("Mantén el que funciona bé. Canvia NOMÉS el que cal.")
        seccions.append("="*60)

        return "\n".join(seccions)

    def _extreure_traduccio(self, text: str, fallback: str) -> str:
        """Intenta extreure la traducció d'una resposta no estructurada."""
        import re

        patterns = [
            r'"traduccio_refinada":\s*"([^"]+)"',
            r'TRADUCCIÓ REFINADA:?\s*\n(.+?)(?:\n\n|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Si la resposta sembla ser la traducció directa
        if len(text) > 50 and not text.startswith("{"):
            return text.strip()

        return fallback


# =============================================================================
# REFINADOR ITERATIU
# =============================================================================

class RefinadorIteratiu:
    """Orquestra el procés de refinament iteratiu.

    Avalua → Refina → Avalua → Refina... fins a aprovació o màx iteracions.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        llindars: LlindarsAvaluacio | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        """Inicialitza el refinador iteratiu.

        Args:
            config: Configuració pels agents.
            llindars: Llindars d'aprovació personalitzats.
            logger: Logger per al seguiment.
        """
        self.config = config
        self.llindars = llindars or LLINDARS_DEFAULT
        self.logger = logger

        # Crear components
        self.avaluador = AvaluadorDimensional(config, llindars, logger)
        self.refinador = AgentRefinador(config, logger)

    def refinar(
        self,
        traduccio: str,
        text_original: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        genere: str = "narrativa",
        descripcio_estil: str | None = None,
        glossari: dict[str, str] | None = None,
        max_iteracions: int | None = None,
    ) -> ResultatRefinament:
        """Refina iterativament una traducció fins a aprovació.

        Args:
            traduccio: Traducció inicial a refinar.
            text_original: Text original.
            llengua_origen: Llengua del text original.
            autor: Autor (opcional).
            genere: Gènere literari.
            descripcio_estil: Descripció de l'estil de l'autor (opcional).
            glossari: Glossari de termes (opcional).
            max_iteracions: Màxim d'iteracions (per defecte, el dels llindars).

        Returns:
            ResultatRefinament amb la millor traducció i historial.
        """
        max_iter = max_iteracions or self.llindars.max_iteracions
        traduccio_actual = traduccio
        historial: list[IteracioRefinament] = []
        avisos: list[str] = []

        # Avaluació inicial
        context_avaluacio = ContextAvaluacio(
            text_original=text_original,
            text_traduit=traduccio_actual,
            llengua_origen=llengua_origen,
            autor=autor,
            genere=genere,
            descripcio_estil_autor=descripcio_estil,
            glossari=glossari,
        )
        avaluacio_inicial = self.avaluador.avaluar(context_avaluacio, iteracio=1)

        # Si ja està aprovat, retornar directament
        if avaluacio_inicial.aprovat:
            return ResultatRefinament(
                traduccio_inicial=traduccio,
                traduccio_final=traduccio,
                aprovat=True,
                iteracions_realitzades=0,
                max_iteracions=max_iter,
                avaluacio_inicial=avaluacio_inicial,
                avaluacio_final=avaluacio_inicial,
                millora_aconseguida=0.0,
            )

        # Bucle de refinament
        millor_traduccio = traduccio_actual
        millor_puntuacio = avaluacio_inicial.puntuacio_global
        avaluacio_actual = avaluacio_inicial

        for i in range(1, max_iter + 1):
            # Refinar
            traduccio_refinada, canvis = self.refinador.refinar(
                traduccio_actual=traduccio_actual,
                text_original=text_original,
                feedback=avaluacio_actual,
                llengua_origen=llengua_origen,
                genere=genere,
            )

            # Registrar iteració
            iteracio = IteracioRefinament(
                numero=i,
                traduccio_entrada=traduccio_actual,
                traduccio_sortida=traduccio_refinada,
                avaluacio=avaluacio_actual,
                canvis_aplicats=canvis,
                dimensio_prioritzada=avaluacio_actual.prioritat_1,
            )
            historial.append(iteracio)

            # Si no hi ha canvis, aturar
            if traduccio_refinada == traduccio_actual:
                avisos.append(f"Iteració {i}: No s'han pogut aplicar més canvis")
                break

            traduccio_actual = traduccio_refinada

            # Avaluar la nova versió
            context_avaluacio.text_traduit = traduccio_actual
            avaluacio_actual = self.avaluador.avaluar(context_avaluacio, iteracio=i+1)

            # Actualitzar millor versió
            if avaluacio_actual.puntuacio_global > millor_puntuacio:
                millor_traduccio = traduccio_actual
                millor_puntuacio = avaluacio_actual.puntuacio_global

            # Si aprovat, aturar
            if avaluacio_actual.aprovat:
                break

        # Determinar si cal revisió humana
        requereix_revisio = (
            not avaluacio_actual.aprovat
            and avaluacio_actual.puntuacio_global < self.llindars.llindar_revisio_humana
        )

        if requereix_revisio:
            avisos.append("La traducció no ha assolit el llindar mínim després de totes les iteracions")

        return ResultatRefinament(
            traduccio_inicial=traduccio,
            traduccio_final=millor_traduccio,
            aprovat=avaluacio_actual.aprovat,
            iteracions_realitzades=len(historial),
            max_iteracions=max_iter,
            avaluacio_inicial=avaluacio_inicial,
            avaluacio_final=avaluacio_actual,
            historial=historial,
            millora_aconseguida=millor_puntuacio - avaluacio_inicial.puntuacio_global,
            requereix_revisio_humana=requereix_revisio,
            avisos=avisos,
        )

    def refinar_fins_aprovacio(
        self,
        traduccio: str,
        text_original: str,
        llengua_origen: str = "llatí",
        genere: str = "narrativa",
    ) -> str:
        """Mètode de conveniència que retorna només la traducció final.

        Args:
            traduccio: Traducció inicial.
            text_original: Text original.
            llengua_origen: Llengua del text.
            genere: Gènere literari.

        Returns:
            Millor traducció obtinguda.
        """
        resultat = self.refinar(
            traduccio=traduccio,
            text_original=text_original,
            llengua_origen=llengua_origen,
            genere=genere,
        )
        return resultat.traduccio_final


class RefinadorPerDimensio(BaseAgent):
    """Agent especialitzat que refina NOMÉS una dimensió específica.

    Útil quan es vol un control més fi sobre el procés de refinament,
    aplicant correccions dimensió per dimensió.
    """

    agent_name: str = "RefinadorDimensio"

    PROMPTS_DIMENSIO = {
        "fidelitat": """Ets un refinador especialitzat en FIDELITAT de traduccions.

La teva ÚNICA tasca és corregir problemes de fidelitat:
- Omissions: restaurar contingut omès
- Addicions: eliminar contingut inventat
- Significat: corregir errors de sentit
- Terminologia: usar termes precisos

NO TOQUIS res més. Si la fluïdesa o el to empitjoren lleugerament per guanyar fidelitat, és acceptable.

Retorna JSON:
{
    "traduccio_refinada": "<text>",
    "correccions_fidelitat": ["<correcció 1>", "<correcció 2>"]
}""",

        "veu_autor": """Ets un refinador especialitzat en VEU DE L'AUTOR.

La teva ÚNICA tasca és recuperar o millorar la veu de l'autor:
- Registre: ajustar formalitat
- To: recuperar ironia, solemnitat, humor...
- Ritme: ajustar cadència de les frases
- Recursos: preservar o adaptar figures retòriques

Aquesta és la dimensió MÉS IMPORTANT. Si cal sacrificar lleugerament la fluïdesa per preservar la veu, fes-ho.

Retorna JSON:
{
    "traduccio_refinada": "<text>",
    "ajustos_veu": ["<ajust 1>", "<ajust 2>"]
}""",

        "fluidesa": """Ets un refinador especialitzat en FLUÏDESA en català.

La teva ÚNICA tasca és millorar la naturalitat del text:
- Sintaxi: reordenar per fluir millor
- Lèxic: usar paraules més naturals
- Normativa: corregir errors IEC
- Calcs: eliminar estructures copiades

IMPORTANT: MAI sacrifiquis la veu de l'autor per guanyar fluïdesa. Si un gir és una mica forçat però preserva el to de l'autor, deixa'l.

Retorna JSON:
{
    "traduccio_refinada": "<text>",
    "millores_fluidesa": ["<millora 1>", "<millora 2>"]
}""",
    }

    def __init__(
        self,
        dimensio: str,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        """Inicialitza el refinador per a una dimensió específica.

        Args:
            dimensio: "fidelitat", "veu_autor" o "fluidesa".
            config: Configuració de l'agent.
            logger: Logger.
        """
        super().__init__(config, logger)
        if dimensio not in self.PROMPTS_DIMENSIO:
            raise ValueError(f"Dimensió no vàlida: {dimensio}")
        self.dimensio = dimensio
        self.agent_name = f"Refinador_{dimensio}"

    @property
    def system_prompt(self) -> str:
        return self.PROMPTS_DIMENSIO[self.dimensio]

    def refinar(
        self,
        traduccio: str,
        text_original: str,
        feedback_dimensio: str,
    ) -> tuple[str, list[str]]:
        """Refina la traducció per a la dimensió específica.

        Args:
            traduccio: Traducció a refinar.
            text_original: Text original.
            feedback_dimensio: Feedback específic de la dimensió.

        Returns:
            Tupla (traducció_refinada, llista_de_canvis).
        """
        prompt = f"""FEEDBACK A APLICAR:
{feedback_dimensio}

TEXT ORIGINAL:
{text_original[:3000]}

TRADUCCIÓ A REFINAR:
{traduccio}

Aplica NOMÉS les correccions de {self.dimensio}."""

        response = self.process(prompt)

        # Parsejar resposta (robust)
        data = extract_json_from_text(response.content)
        if data:
            traduccio_refinada = data.get("traduccio_refinada", traduccio)
            # Extreure canvis segons la clau de la dimensió
            claus_canvis = ["correccions_fidelitat", "ajustos_veu", "millores_fluidesa"]
            canvis = []
            for clau in claus_canvis:
                if clau in data:
                    canvis = data[clau]
                    break
            return traduccio_refinada, canvis

        return traduccio, []
