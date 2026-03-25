"""Agent Evaluador Final - Post-Publicació.

Avalua la qualitat de traduccions ja publicades, detecta errors i aplica correccions.
S'executa periòdicament o sota demanda per mantenir la qualitat del catàleg.

Responsabilitats:
1. Avaluació completa de la traducció publicada
2. Detecció d'errors ortogràfics, terminològics, de coherència
3. Verificació de fidelitat vs original
4. Generació d'informe detallat amb correccions
5. Aplicació de correccions (automàtiques o pendents d'aprovació)
6. Actualització del fitxer metadata.yml amb puntuacions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml
from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent, extract_json_from_text

# Imports opcionals per LanguageTool
try:
    from utils.corrector_linguistic import CorrectorLinguistic
    LANGUAGETOOL_DISPONIBLE = True
except ImportError:
    CorrectorLinguistic = None  # type: ignore[assignment,misc]
    LANGUAGETOOL_DISPONIBLE = False

# Detector de calcs
try:
    from utils.detector_calcs import detectar_calcs, ResultatDeteccio
    DETECTOR_CALCS_DISPONIBLE = True
except ImportError:
    DETECTOR_CALCS_DISPONIBLE = False

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# =============================================================================
# FUNCIONS AUXILIARS
# =============================================================================

DEFAULT_PUNTUACIO = 5.0


def safe_float(value: Any, default: float = DEFAULT_PUNTUACIO) -> float:
    """Converteix un valor a float de manera segura."""
    if value is None:
        return default
    try:
        result = float(value)
        return max(0.0, min(10.0, result))  # Clamp entre 0 i 10
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Converteix un valor a string de manera segura."""
    if value is None:
        return default
    return str(value)


def safe_list(value: Any, default: list | None = None) -> list:
    """Converteix un valor a llista de manera segura."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return value
    return default


# =============================================================================
# MODELS
# =============================================================================

class SeveritatError(str, Enum):
    """Severitat dels errors detectats."""
    CRITICA = "critica"       # Error greu que canvia el sentit
    ALTA = "alta"             # Error notable que cal corregir
    MITJANA = "mitjana"       # Error que caldria revisar
    BAIXA = "baixa"           # Millora suggerida
    INFO = "info"             # Observació informativa


class TipusError(str, Enum):
    """Tipus d'errors que pot detectar l'evaluador."""
    ORTOGRAFIC = "ortografic"
    GRAMATICAL = "gramatical"
    TIPOGRAFIC = "tipografic"
    PUNTUACIO = "puntuacio"
    TERMINOLOGIC = "terminologic"
    COHERENCIA = "coherencia"
    OMISSIO = "omissio"
    ADDICIO = "addicio"
    FIDELITAT = "fidelitat"
    ESTIL = "estil"
    CALC_LINGUISTIC = "calc_linguistic"
    FORMAT = "format"


class ErrorDetectat(BaseModel):
    """Error individual detectat en la traducció."""

    tipus: TipusError = Field(description="Tipus d'error")
    severitat: SeveritatError = Field(description="Gravetat de l'error")
    ubicacio: str = Field(description="On es troba l'error (capítol, línia, etc.)")
    text_original: str | None = Field(default=None, description="Fragment original relacionat")
    text_erroni: str = Field(description="Fragment amb l'error")
    text_corregit: str = Field(description="Correcció proposada")
    explicacio: str = Field(description="Explicació de per què és un error")
    correccio_automatica: bool = Field(
        default=False,
        description="Si es pot aplicar automàticament"
    )
    aplicada: bool = Field(default=False, description="Si ja s'ha aplicat la correcció")


class PuntuacioAvaluacio(BaseModel):
    """Puntuacions de l'avaluació final."""

    fidelitat: float = Field(ge=0, le=10, description="Preservació del significat")
    veu_autor: float = Field(ge=0, le=10, description="Preservació de l'estil")
    fluidesa: float = Field(ge=0, le=10, description="Naturalitat del català")
    correccio_linguistica: float = Field(ge=0, le=10, description="Ortografia, gramàtica, tipografia")
    coherencia: float = Field(ge=0, le=10, description="Coherència terminològica i estilística")
    global_: float = Field(ge=0, le=10, alias="global", description="Puntuació global ponderada")

    class Config:
        populate_by_name = True


class InformeEvaluacio(BaseModel):
    """Informe complet de l'avaluació final."""

    # Identificació
    obra: str = Field(description="Títol de l'obra")
    autor: str = Field(description="Autor original")
    llengua_origen: str = Field(description="Llengua de l'original")
    ruta_obra: str = Field(description="Ruta al directori de l'obra")

    # Timestamps
    data_avaluacio: str = Field(default_factory=lambda: datetime.now().isoformat())
    data_publicacio: str | None = Field(default=None, description="Data de publicació original")

    # Puntuacions
    puntuacions: PuntuacioAvaluacio = Field(description="Puntuacions per dimensió")

    # Errors
    errors: list[ErrorDetectat] = Field(default_factory=list, description="Errors detectats")
    total_errors: int = Field(default=0, description="Total d'errors")
    errors_critics: int = Field(default=0, description="Errors de severitat crítica")
    errors_alts: int = Field(default=0, description="Errors de severitat alta")

    # Correccions
    correccions_aplicades: int = Field(default=0, description="Correccions automàtiques aplicades")
    correccions_pendents: int = Field(default=0, description="Correccions pendents d'aprovació")

    # Veredicte
    aprovat: bool = Field(default=False, description="Si la traducció supera els estàndards")
    requereix_revisio_humana: bool = Field(default=False, description="Si cal revisió manual")
    recomanacions: list[str] = Field(default_factory=list, description="Recomanacions generals")

    # Estadístiques
    paraules_original: int = Field(default=0)
    paraules_traduccio: int = Field(default=0)
    ratio_expansio: float = Field(default=1.0, description="Ratio traduccio/original")

    class Config:
        populate_by_name = True


class ConfiguracioEvaluador(BaseModel):
    """Configuració de l'evaluador final."""

    # Llindars d'aprovació
    llindar_global: float = Field(default=7.5, description="Puntuació global mínima")
    llindar_fidelitat: float = Field(default=7.0, description="Fidelitat mínima")
    llindar_veu: float = Field(default=7.0, description="Veu de l'autor mínima")
    llindar_fluidesa: float = Field(default=7.0, description="Fluïdesa mínima")

    # Correccions automàtiques
    aplicar_correccions_automatiques: bool = Field(
        default=False,
        description="Aplicar correccions de baixa severitat automàticament"
    )
    max_correccions_automatiques: int = Field(
        default=50,
        description="Màxim de correccions automàtiques per execució"
    )

    # Severitats a corregir automàticament
    severitats_automatiques: list[SeveritatError] = Field(
        default_factory=lambda: [SeveritatError.BAIXA, SeveritatError.INFO],
        description="Severitats que es poden corregir automàticament"
    )

    # Tipus d'errors a corregir automàticament
    tipus_automatics: list[TipusError] = Field(
        default_factory=lambda: [
            TipusError.ORTOGRAFIC,
            TipusError.TIPOGRAFIC,
            TipusError.PUNTUACIO,
        ],
        description="Tipus d'errors que es poden corregir automàticament"
    )

    # Opcions d'anàlisi
    usar_languagetool: bool = Field(default=True, description="Usar LanguageTool per correccions")
    detectar_calcs: bool = Field(default=True, description="Usar detector de calcs lingüístics")
    verificar_glossari: bool = Field(default=True, description="Verificar coherència amb glossari")

    # Backup
    crear_backup: bool = Field(default=True, description="Crear backup abans de corregir")


class SolicitutEvaluacio(BaseModel):
    """Sol·licitud per avaluar una obra."""

    ruta_obra: str = Field(description="Ruta al directori de l'obra (obres/categoria/autor/obra)")
    config: ConfiguracioEvaluador = Field(default_factory=ConfiguracioEvaluador)


# =============================================================================
# AGENT EVALUADOR FINAL
# =============================================================================

class EvaluadorFinalAgent(BaseAgent):
    """Agent que avalua traduccions publicades i aplica correccions.

    Flux de treball:
    1. Llegir l'obra publicada (original + traducció + glossari + metadata)
    2. Executar avaluació dimensional completa
    3. Detectar errors amb LanguageTool i detector de calcs
    4. Verificar coherència amb glossari
    5. Comparar amb original per detectar omissions/addicions
    6. Generar informe detallat
    7. Aplicar correccions automàtiques (si configurat)
    8. Actualizar metadata amb puntuacions
    """

    agent_name: ClassVar[str] = "EvaluadorFinal"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        """Inicialitza l'agent evaluador final."""
        super().__init__(config, logger)
        self._corrector: Any = None

    @property
    def system_prompt(self) -> str:
        return """Ets l'Evaluador Final de la Biblioteca Universal Arion.

La teva missió és revisar traduccions JA PUBLICADES per assegurar-ne la qualitat
i detectar errors que s'hagin pogut escapar durant el procés de traducció.

══════════════════════════════════════════════════════════════════════════════
RESPONSABILITATS:
══════════════════════════════════════════════════════════════════════════════

1. AVALUACIÓ DIMENSIONAL COMPLETA
   - Fidelitat: El significat es preserva correctament?
   - Veu de l'autor: L'estil i el to es mantenen?
   - Fluïdesa: El català sona natural?
   - Correcció lingüística: Ortografia, gramàtica, tipografia correctes?
   - Coherència: Terminologia i estil consistents?

2. DETECCIÓ D'ERRORS
   - Ortogràfics: errors d'ortografia
   - Gramaticals: concordança, règim verbal, etc.
   - Tipogràfics: guions, cometes, espais, etc.
   - Puntuació: comes, punts, punt i coma
   - Terminològics: termes mal traduïts o inconsistents
   - Coherència: inconsistències internes
   - Omissions: contingut de l'original no traduït
   - Addicions: contingut inventat no present a l'original
   - Fidelitat: distorsions del significat
   - Estil: problemes de registre o to
   - Calcs lingüístics: estructures no naturals en català
   - Format: problemes de format markdown

3. PROPOSTA DE CORRECCIONS
   - Cada error ha de tenir una correcció proposada
   - Indicar si es pot aplicar automàticament
   - Explicar per què és un error

4. CLASSIFICACIÓ DE SEVERITAT
   - CRÍTICA: Error greu que canvia el sentit
   - ALTA: Error notable que cal corregir
   - MITJANA: Error que caldria revisar
   - BAIXA: Millora suggerida
   - INFO: Observació informativa

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE):
══════════════════════════════════════════════════════════════════════════════

{
    "puntuacions": {
        "fidelitat": <1-10>,
        "veu_autor": <1-10>,
        "fluidesa": <1-10>,
        "correccio_linguistica": <1-10>,
        "coherencia": <1-10>
    },
    "errors": [
        {
            "tipus": "<ortografic|gramatical|tipografic|puntuacio|terminologic|coherencia|omissio|addicio|fidelitat|estil|calc_linguistic|format>",
            "severitat": "<critica|alta|mitjana|baixa|info>",
            "ubicacio": "<capítol X, línia Y / secció Z>",
            "text_original": "<fragment original o null>",
            "text_erroni": "<fragment amb error>",
            "text_corregit": "<correcció proposada>",
            "explicacio": "<per què és un error>",
            "correccio_automatica": <true|false>
        }
    ],
    "resum": "<breu resum de l'avaluació>",
    "recomanacions": ["recomanació 1", "recomanació 2"],
    "requereix_revisio_humana": <true|false>
}

══════════════════════════════════════════════════════════════════════════════
CRITERIS D'AVALUACIÓ:
══════════════════════════════════════════════════════════════════════════════

PUNTUACIÓ 9-10: Excel·lent, publicable sense canvis
PUNTUACIÓ 7-8:  Bona, amb millores menors opcionals
PUNTUACIÓ 5-6:  Acceptable, però amb errors a corregir
PUNTUACIÓ 3-4:  Deficient, requereix revisió significativa
PUNTUACIÓ 1-2:  Inacceptable, cal re-traduir

APROVAT si:
- Global ≥ 7.5 I
- Cap error de severitat CRÍTICA I
- Menys de 5 errors de severitat ALTA"""

    def _get_corrector(self) -> Any:
        """Obté o crea el corrector lingüístic."""
        if self._corrector is None and LANGUAGETOOL_DISPONIBLE:
            try:
                self._corrector = CorrectorLinguistic(llengua="ca")
            except Exception as e:
                self.log_warning(f"No s'ha pogut inicialitzar LanguageTool: {e}")
        return self._corrector

    def avaluar(self, sol_licitud: SolicitutEvaluacio) -> InformeEvaluacio:
        """Avalua una obra publicada completa.

        Args:
            sol_licitud: Sol·licitud amb la ruta i configuració.

        Returns:
            InformeEvaluacio amb tots els detalls.
        """
        ruta = Path(sol_licitud.ruta_obra)
        config = sol_licitud.config

        self.log_info(f"Avaluant obra: {ruta}")

        # 1. Llegir fitxers de l'obra
        original, traduccio, glossari, metadata = self._llegir_obra(ruta)

        # Extreure metadata niuada si cal
        if "obra" in metadata:
            metadata_obra = metadata.get("obra", {})
            titol = metadata_obra.get("titol", ruta.name)
            autor = metadata_obra.get("autor", "Desconegut")
            llengua = metadata_obra.get("llengua_original", "desconeguda")
        else:
            titol = metadata.get("titol", metadata.get("title", ruta.name))
            autor = metadata.get("autor", metadata.get("author", "Desconegut"))
            llengua = metadata.get("llengua_origen", metadata.get("source_language", "desconeguda"))

        # 2. Crear informe base
        informe = InformeEvaluacio(
            obra=titol,
            autor=autor,
            llengua_origen=llengua,
            ruta_obra=str(ruta),
            data_publicacio=metadata.get("data_publicacio"),
            puntuacions=PuntuacioAvaluacio(
                fidelitat=0, veu_autor=0, fluidesa=0,
                correccio_linguistica=0, coherencia=0, global_=0
            ),
            paraules_original=len(original.split()) if original else 0,
            paraules_traduccio=len(traduccio.split()) if traduccio else 0,
        )

        if informe.paraules_original > 0:
            informe.ratio_expansio = informe.paraules_traduccio / informe.paraules_original

        errors: list[ErrorDetectat] = []

        # 3. Avaluació amb LLM
        self.log_info("Executant avaluació dimensional amb LLM...")
        avaluacio_llm = self._avaluar_amb_llm(original, traduccio, metadata)
        if avaluacio_llm:
            informe.puntuacions = avaluacio_llm["puntuacions"]
            errors.extend(avaluacio_llm["errors"])
            informe.recomanacions = avaluacio_llm.get("recomanacions", [])

        # 4. Correcció amb LanguageTool
        if config.usar_languagetool and LANGUAGETOOL_DISPONIBLE:
            self.log_info("Detectant errors amb LanguageTool...")
            errors_lt = self._detectar_errors_languagetool(traduccio)
            errors.extend(errors_lt)
            self.log_info(f"LanguageTool: {len(errors_lt)} errors detectats")

        # 5. Detector de calcs
        if config.detectar_calcs and DETECTOR_CALCS_DISPONIBLE:
            self.log_info("Detectant calcs lingüístics...")
            errors_calcs = self._detectar_calcs_linguistics(traduccio)
            errors.extend(errors_calcs)
            self.log_info(f"Calcs: {len(errors_calcs)} detectats")

        # 6. Verificar coherència amb glossari
        if config.verificar_glossari and glossari:
            self.log_info("Verificant coherència amb glossari...")
            errors_glossari = self._verificar_glossari(traduccio, glossari)
            errors.extend(errors_glossari)

        # 7. Consolidar errors i calcular estadístiques
        informe.errors = errors
        informe.total_errors = len(errors)
        informe.errors_critics = sum(1 for e in errors if e.severitat == SeveritatError.CRITICA)
        informe.errors_alts = sum(1 for e in errors if e.severitat == SeveritatError.ALTA)

        # 8. Calcular puntuació global ponderada
        p = informe.puntuacions
        p.global_ = round(
            p.fidelitat * 0.25 +
            p.veu_autor * 0.25 +
            p.fluidesa * 0.20 +
            p.correccio_linguistica * 0.15 +
            p.coherencia * 0.15,
            1
        )

        # 9. Determinar si aprova
        informe.aprovat = (
            p.global_ >= config.llindar_global and
            informe.errors_critics == 0 and
            informe.errors_alts < 5
        )

        informe.requereix_revisio_humana = (
            informe.errors_critics > 0 or
            informe.errors_alts >= 3 or
            p.global_ < config.llindar_global
        )

        # 10. Aplicar correccions automàtiques si configurat
        if config.aplicar_correccions_automatiques:
            self.log_info("Aplicant correccions automàtiques...")
            aplicades = self._aplicar_correccions(
                ruta, traduccio, errors, config
            )
            informe.correccions_aplicades = aplicades
            self.log_info(f"Correccions aplicades: {aplicades}")

        informe.correccions_pendents = sum(
            1 for e in errors
            if not e.aplicada and e.correccio_automatica
        )

        # 11. Actualitzar metadata
        self._actualitzar_metadata(ruta, informe)

        status = "✅ APROVAT" if informe.aprovat else "❌ NO APROVAT"
        self.log_info(f"Avaluació completada: {status} ({p.global_}/10)")

        return informe

    def _llegir_obra(self, ruta: Path) -> tuple[str, str, dict, dict]:
        """Llegeix tots els fitxers d'una obra.

        Returns:
            Tupla (original, traducció, glossari, metadata)
        """
        original = ""
        traduccio = ""
        glossari = {}
        metadata = {}

        # Original
        original_path = ruta / "original.md"
        if original_path.exists():
            original = original_path.read_text(encoding="utf-8")

        # Traducció
        traduccio_path = ruta / "traduccio.md"
        if traduccio_path.exists():
            traduccio = traduccio_path.read_text(encoding="utf-8")

        # Glossari
        glossari_path = ruta / "glossari.yml"
        if glossari_path.exists():
            try:
                glossari = yaml.safe_load(glossari_path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        # Metadata
        metadata_path = ruta / "metadata.yml"
        if metadata_path.exists():
            try:
                metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        return original, traduccio, glossari, metadata

    def _avaluar_amb_llm(
        self,
        original: str,
        traduccio: str,
        metadata: dict
    ) -> dict | None:
        """Avalua amb el model LLM.

        Returns:
            Dict amb puntuacions i errors, o None si falla.
        """
        if not original or not traduccio:
            return None

        # Extreure metadata niuada si cal
        if "obra" in metadata:
            metadata_obra = metadata.get("obra", {})
            titol = metadata_obra.get("titol", "Desconegut")
            autor = metadata_obra.get("autor", "Desconegut")
            llengua = metadata_obra.get("llengua_original", "desconeguda")
            genere = metadata_obra.get("genere", "general")
        else:
            titol = metadata.get("titol", metadata.get("title", "Desconegut"))
            autor = metadata.get("autor", metadata.get("author", "Desconegut"))
            llengua = metadata.get("llengua_origen", metadata.get("source_language", "desconeguda"))
            genere = metadata.get("genere", "general")

        # Limitar longitud per evitar context massa llarg
        max_chars = 12000
        original_truncat = original[:max_chars] + "..." if len(original) > max_chars else original
        traduccio_truncat = traduccio[:max_chars] + "..." if len(traduccio) > max_chars else traduccio

        prompt = f"""Avalua aquesta traducció publicada.

══════════════════════════════════════════════════════════════════════════════
METADATA:
══════════════════════════════════════════════════════════════════════════════
Obra: {titol}
Autor: {autor}
Llengua origen: {llengua}
Gènere: {genere}

══════════════════════════════════════════════════════════════════════════════
TEXT ORIGINAL:
══════════════════════════════════════════════════════════════════════════════
{original_truncat}

══════════════════════════════════════════════════════════════════════════════
TRADUCCIÓ AL CATALÀ:
══════════════════════════════════════════════════════════════════════════════
{traduccio_truncat}

══════════════════════════════════════════════════════════════════════════════
INSTRUCCIONS:
══════════════════════════════════════════════════════════════════════════════
1. Avalua les 5 dimensions (1-10 cada una)
2. Detecta TOTS els errors que trobis (màxim 20)
3. Per cada error, proposa una correcció
4. Marca quins errors es poden corregir automàticament (només ortogràfics simples)
5. Respon NOMÉS amb JSON vàlid"""

        try:
            response = self.process(prompt)
        except Exception as e:
            self.log_error(f"Error cridant LLM: {e}")
            return None

        if not response or not response.content:
            self.log_error("Resposta buida del LLM")
            return None

        # Parsejar JSON
        try:
            data = extract_json_from_text(response.content)

            if not data:
                self.log_warning("No s'ha pogut extreure JSON de la resposta")
                return None

            # Construir puntuacions
            punts = data.get("puntuacions", {})
            puntuacions = PuntuacioAvaluacio(
                fidelitat=safe_float(punts.get("fidelitat"), DEFAULT_PUNTUACIO),
                veu_autor=safe_float(punts.get("veu_autor"), DEFAULT_PUNTUACIO),
                fluidesa=safe_float(punts.get("fluidesa"), DEFAULT_PUNTUACIO),
                correccio_linguistica=safe_float(punts.get("correccio_linguistica"), DEFAULT_PUNTUACIO),
                coherencia=safe_float(punts.get("coherencia"), DEFAULT_PUNTUACIO),
                global_=0  # Es calcularà després
            )

            # Construir errors
            errors = []
            for err_data in data.get("errors", []):
                try:
                    # Validar tipus i severitat
                    tipus_str = err_data.get("tipus", "estil")
                    severitat_str = err_data.get("severitat", "mitjana")

                    try:
                        tipus = TipusError(tipus_str)
                    except ValueError:
                        tipus = TipusError.ESTIL

                    try:
                        severitat = SeveritatError(severitat_str)
                    except ValueError:
                        severitat = SeveritatError.MITJANA

                    error = ErrorDetectat(
                        tipus=tipus,
                        severitat=severitat,
                        ubicacio=safe_str(err_data.get("ubicacio"), "desconeguda"),
                        text_original=err_data.get("text_original"),
                        text_erroni=safe_str(err_data.get("text_erroni"), ""),
                        text_corregit=safe_str(err_data.get("text_corregit"), ""),
                        explicacio=safe_str(err_data.get("explicacio"), ""),
                        correccio_automatica=err_data.get("correccio_automatica", False),
                    )
                    errors.append(error)
                except Exception as e:
                    self.log_warning(f"Error parsejant error: {e}")
                    continue

            return {
                "puntuacions": puntuacions,
                "errors": errors,
                "recomanacions": safe_list(data.get("recomanacions"), []),
            }

        except Exception as e:
            self.log_error(f"Error parsejant JSON: {e}")
            return None

    def _detectar_errors_languagetool(self, text: str) -> list[ErrorDetectat]:
        """Detecta errors amb LanguageTool."""
        errors = []

        corrector = self._get_corrector()
        if not corrector:
            return errors

        try:
            resultat = corrector.corregir(text, auto_corregir=False)

            for err in resultat.errors:
                # Determinar severitat basada en la categoria
                severitat = SeveritatError.BAIXA
                if err.categoria.value in ("ortografia", "barbarisme"):
                    severitat = SeveritatError.MITJANA
                elif err.categoria.value == "gramatica":
                    severitat = SeveritatError.MITJANA

                # Mapatge de categories
                tipus_map = {
                    "ortografia": TipusError.ORTOGRAFIC,
                    "gramatica": TipusError.GRAMATICAL,
                    "puntuacio": TipusError.PUNTUACIO,
                    "tipografia": TipusError.TIPOGRAFIC,
                    "estil": TipusError.ESTIL,
                    "barbarisme": TipusError.CALC_LINGUISTIC,
                    "altres": TipusError.ESTIL,
                }
                tipus = tipus_map.get(err.categoria.value, TipusError.ESTIL)

                # Obtenir primer suggeriment
                text_corregit = err.suggeriments[0] if err.suggeriments else ""

                error = ErrorDetectat(
                    tipus=tipus,
                    severitat=severitat,
                    ubicacio=f"Posició {err.posicio_inici}",
                    text_erroni=err.text_original,
                    text_corregit=text_corregit,
                    explicacio=err.missatge,
                    correccio_automatica=True,
                )
                errors.append(error)

        except Exception as e:
            self.log_warning(f"Error LanguageTool: {e}")

        return errors

    def _detectar_calcs_linguistics(self, text: str) -> list[ErrorDetectat]:
        """Detecta calcs lingüístics."""
        errors = []

        if not DETECTOR_CALCS_DISPONIBLE:
            return errors

        try:
            resultat: ResultatDeteccio = detectar_calcs(text)

            for calc in resultat.calcs:
                error = ErrorDetectat(
                    tipus=TipusError.CALC_LINGUISTIC,
                    severitat=SeveritatError.MITJANA if calc.severitat > 5 else SeveritatError.BAIXA,
                    ubicacio=f"Posició {calc.posicio[0]}-{calc.posicio[1]}",
                    text_erroni=calc.text_original,
                    text_corregit=calc.suggeriment or "",
                    explicacio=f"Calc ({calc.tipus.value}): {calc.explicacio}",
                    correccio_automatica=False,  # Calcs requereixen revisió humana
                )
                errors.append(error)

        except Exception as e:
            self.log_warning(f"Error detector calcs: {e}")

        return errors

    def _verificar_glossari(self, text: str, glossari: dict) -> list[ErrorDetectat]:
        """Verifica coherència amb el glossari."""
        errors = []

        termes = glossari.get("termes", glossari)
        if not isinstance(termes, (dict, list)):
            return errors

        # Si és una llista, convertir a dict
        if isinstance(termes, list):
            termes_dict = {}
            for item in termes:
                if isinstance(item, dict):
                    original = item.get("original", item.get("grec", ""))
                    traduccio = item.get("traduccio", "")
                    if original and traduccio:
                        termes_dict[original] = traduccio
            termes = termes_dict

        text_lower = text.lower()

        for terme_original, traduccio_correcta in termes.items():
            if isinstance(traduccio_correcta, dict):
                traduccio_correcta = traduccio_correcta.get("traduccio", "")

            if not traduccio_correcta or not terme_original:
                continue

            # Buscar el terme original al text (podria indicar que no s'ha traduït)
            if terme_original.lower() in text_lower:
                # Verificar si la traducció correcta també hi és
                if traduccio_correcta.lower() not in text_lower:
                    error = ErrorDetectat(
                        tipus=TipusError.TERMINOLOGIC,
                        severitat=SeveritatError.MITJANA,
                        ubicacio="Text complet",
                        text_original=terme_original,
                        text_erroni=terme_original,
                        text_corregit=traduccio_correcta,
                        explicacio=f"El terme '{terme_original}' apareix però no la seva traducció '{traduccio_correcta}' del glossari",
                        correccio_automatica=False,
                    )
                    errors.append(error)

        return errors

    def _aplicar_correccions(
        self,
        ruta: Path,
        text_original: str,
        errors: list[ErrorDetectat],
        config: ConfiguracioEvaluador,
    ) -> int:
        """Aplica correccions automàtiques al fitxer de traducció.

        Returns:
            Nombre de correccions aplicades.
        """
        # Filtrar errors que es poden corregir automàticament
        errors_aplicables = [
            e for e in errors
            if e.correccio_automatica
            and e.severitat in config.severitats_automatiques
            and e.tipus in config.tipus_automatics
            and e.text_erroni and e.text_corregit
            and e.text_erroni != e.text_corregit
        ]

        if not errors_aplicables:
            return 0

        # Limitar nombre de correccions
        errors_aplicables = errors_aplicables[:config.max_correccions_automatiques]

        traduccio_path = ruta / "traduccio.md"
        if not traduccio_path.exists():
            return 0

        # Crear backup si configurat
        if config.crear_backup:
            backup_path = ruta / f"traduccio.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            backup_path.write_text(text_original, encoding="utf-8")
            self.log_info(f"Backup creat: {backup_path.name}")

        # Aplicar correccions
        text_corregit = text_original
        aplicades = 0

        for error in errors_aplicables:
            if error.text_erroni in text_corregit:
                text_corregit = text_corregit.replace(
                    error.text_erroni,
                    error.text_corregit,
                    1  # Només una ocurrència per seguretat
                )
                error.aplicada = True
                aplicades += 1

        # Guardar text corregit
        if aplicades > 0:
            traduccio_path.write_text(text_corregit, encoding="utf-8")
            self.log_info(f"Aplicades {aplicades} correccions a {traduccio_path.name}")

        return aplicades

    def _actualitzar_metadata(self, ruta: Path, informe: InformeEvaluacio) -> None:
        """Actualitza el fitxer metadata.yml amb els resultats de l'avaluació."""
        import yaml

        metadata_path = ruta / "metadata.yml"

        # Llegir metadata existent
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        # Afegir/actualitzar secció d'avaluació
        metadata["avaluacio_final"] = {
            "data": informe.data_avaluacio,
            "puntuacions": {
                "fidelitat": informe.puntuacions.fidelitat,
                "veu_autor": informe.puntuacions.veu_autor,
                "fluidesa": informe.puntuacions.fluidesa,
                "correccio_linguistica": informe.puntuacions.correccio_linguistica,
                "coherencia": informe.puntuacions.coherencia,
                "global": informe.puntuacions.global_,
            },
            "total_errors": informe.total_errors,
            "errors_critics": informe.errors_critics,
            "errors_alts": informe.errors_alts,
            "aprovat": informe.aprovat,
            "requereix_revisio_humana": informe.requereix_revisio_humana,
            "correccions_aplicades": informe.correccions_aplicades,
            "correccions_pendents": informe.correccions_pendents,
        }

        # Guardar
        try:
            metadata_path.write_text(
                yaml.dump(metadata, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8"
            )
        except Exception as e:
            self.log_error(f"Error guardant metadata: {e}")

    def generar_informe_text(self, informe: InformeEvaluacio) -> str:
        """Genera un informe en format text llegible."""
        lines = [
            "═" * 70,
            "        INFORME D'AVALUACIÓ FINAL - BIBLIOTECA UNIVERSAL ARION",
            "═" * 70,
            "",
            f"Obra: {informe.obra}",
            f"Autor: {informe.autor}",
            f"Llengua origen: {informe.llengua_origen}",
            f"Data avaluació: {informe.data_avaluacio[:10]}",
            "",
            "─" * 70,
            "PUNTUACIONS",
            "─" * 70,
            f"  Fidelitat:             {informe.puntuacions.fidelitat:.1f}/10",
            f"  Veu de l'autor:        {informe.puntuacions.veu_autor:.1f}/10",
            f"  Fluïdesa:              {informe.puntuacions.fluidesa:.1f}/10",
            f"  Correcció lingüística: {informe.puntuacions.correccio_linguistica:.1f}/10",
            f"  Coherència:            {informe.puntuacions.coherencia:.1f}/10",
            f"  ────────────────────────────────",
            f"  GLOBAL:                {informe.puntuacions.global_:.1f}/10",
            "",
            "─" * 70,
            "ESTADÍSTIQUES",
            "─" * 70,
            f"  Paraules original:     {informe.paraules_original:,}",
            f"  Paraules traducció:    {informe.paraules_traduccio:,}",
            f"  Ràtio expansió:        {informe.ratio_expansio:.2f}x",
            "",
            f"  Total errors:          {informe.total_errors}",
            f"  Errors crítics:        {informe.errors_critics}",
            f"  Errors alts:           {informe.errors_alts}",
            f"  Correccions aplicades: {informe.correccions_aplicades}",
            f"  Correccions pendents:  {informe.correccions_pendents}",
            "",
        ]

        # Veredicte
        lines.append("─" * 70)
        lines.append("VEREDICTE")
        lines.append("─" * 70)

        if informe.aprovat:
            lines.append("  ✅ APROVAT - La traducció compleix els estàndards de qualitat")
        else:
            lines.append("  ❌ NO APROVAT - Requereix correccions")

        if informe.requereix_revisio_humana:
            lines.append("  ⚠️  REQUEREIX REVISIÓ HUMANA")

        # Errors (màx 15)
        if informe.errors:
            lines.append("")
            lines.append("─" * 70)
            lines.append(f"ERRORS DETECTATS ({min(15, len(informe.errors))} de {len(informe.errors)})")
            lines.append("─" * 70)

            for i, error in enumerate(informe.errors[:15], 1):
                emoji = {
                    SeveritatError.CRITICA: "🔴",
                    SeveritatError.ALTA: "🟠",
                    SeveritatError.MITJANA: "🟡",
                    SeveritatError.BAIXA: "🟢",
                    SeveritatError.INFO: "ℹ️",
                }.get(error.severitat, "•")

                lines.append(f"\n{i}. {emoji} [{error.tipus.value.upper()}] - {error.severitat.value}")
                lines.append(f"   Ubicació: {error.ubicacio}")
                if error.text_erroni:
                    lines.append(f"   Error: «{error.text_erroni[:60]}{'...' if len(error.text_erroni) > 60 else ''}»")
                if error.text_corregit:
                    lines.append(f"   Correcció: «{error.text_corregit[:60]}{'...' if len(error.text_corregit) > 60 else ''}»")
                if error.explicacio:
                    lines.append(f"   Explicació: {error.explicacio[:80]}{'...' if len(error.explicacio) > 80 else ''}")
                if error.aplicada:
                    lines.append("   ✓ Correcció aplicada automàticament")

        # Recomanacions
        if informe.recomanacions:
            lines.append("")
            lines.append("─" * 70)
            lines.append("RECOMANACIONS")
            lines.append("─" * 70)
            for rec in informe.recomanacions:
                lines.append(f"  • {rec}")

        lines.append("")
        lines.append("═" * 70)

        return "\n".join(lines)


# =============================================================================
# FUNCIONS D'ÚS RÀPID
# =============================================================================

def avaluar_obra(
    ruta_obra: str,
    aplicar_correccions: bool = False,
    verbose: bool = True,
) -> InformeEvaluacio:
    """Funció d'ús ràpid per avaluar una obra.

    Args:
        ruta_obra: Ruta al directori de l'obra.
        aplicar_correccions: Si s'han d'aplicar correccions automàtiques.
        verbose: Si s'ha d'imprimir l'informe.

    Returns:
        InformeEvaluacio amb els resultats.

    Example:
        >>> informe = avaluar_obra("obres/filosofia/plato/el-banquet")
        >>> print(f"Puntuació: {informe.puntuacions.global_}/10")
    """
    config = ConfiguracioEvaluador(
        aplicar_correccions_automatiques=aplicar_correccions,
    )

    sol = SolicitutEvaluacio(ruta_obra=ruta_obra, config=config)

    agent = EvaluadorFinalAgent()
    informe = agent.avaluar(sol)

    if verbose:
        print(agent.generar_informe_text(informe))

    return informe


def avaluar_cataleg(
    ruta_base: str = "obres",
    aplicar_correccions: bool = False,
) -> list[InformeEvaluacio]:
    """Avalua totes les obres del catàleg.

    Args:
        ruta_base: Ruta base del catàleg.
        aplicar_correccions: Si s'han d'aplicar correccions.

    Returns:
        Llista d'informes per cada obra.
    """
    informes = []
    ruta = Path(ruta_base)

    # Buscar totes les obres (directoris amb traduccio.md)
    for traduccio_path in ruta.rglob("traduccio.md"):
        obra_dir = traduccio_path.parent

        try:
            informe = avaluar_obra(
                str(obra_dir),
                aplicar_correccions=aplicar_correccions,
                verbose=False,
            )
            informes.append(informe)

            # Resum breu
            status = "✅" if informe.aprovat else "❌"
            print(f"{status} {informe.obra} ({informe.autor}): {informe.puntuacions.global_:.1f}/10")

        except Exception as e:
            print(f"❌ Error avaluant {obra_dir}: {e}")

    return informes


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Ús: python evaluador_final.py <ruta_obra> [--aplicar]")
        print("Exemple: python evaluador_final.py obres/narrativa/edgar-allan-poe/el-retrat-oval")
        sys.exit(1)

    ruta = sys.argv[1]
    aplicar = "--aplicar" in sys.argv

    informe = avaluar_obra(ruta, aplicar_correccions=aplicar)

    # Sortir amb codi d'error si no aprova
    sys.exit(0 if informe.aprovat else 1)
