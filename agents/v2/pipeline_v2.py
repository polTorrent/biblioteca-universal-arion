"""Pipeline de Traducció v2.

Orquestra el flux complet de traducció utilitzant:
- Agents V2: Anàlisi, Traducció, Avaluació, Refinament
- Agents V1: Glossari, Chunker, Portades, EPUB (reutilitzats)
- Investigador: Context històric i cultural
- Dashboard: Monitorització en temps real al navegador
- Core: Persistència d'estat, memòria contextual, validació

Flux:
0. Investigació - Recollir context sobre autor i obra
1. Glossari (v1) - Crear terminologia consistent
2. Chunking (v1) - Dividir text en fragments manejables
3. Per cada chunk:
   a. Anàlisi Pre-Traducció (v2)
   b. Traducció Enriquida (v2)
   c. Avaluació Dimensional (v2)
   d. Refinament Iteratiu (v2) si cal
4. Fusió de chunks
5. Validació final (core)
6. Post-processament (portades, EPUB, etc.)
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional as Opt
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, ContentFilterError

# Validadors
from utils.validators import validar_text_entrada, netejar_text, SeverityLevel

# Core (persistència i validació)
from core import EstatPipeline, MemoriaContextual, ValidadorFinal, ContextInvestigacio

# Agents V2 (nous)
from agents.v2.analitzador_pre import AnalitzadorPreTraduccio, SelectorExemplesFewShot
from agents.v2.traductor_enriquit import TraductorEnriquit, ResultatTraduccio
from agents.v2.avaluador_dimensional import AvaluadorDimensional
from agents.v2.refinador_iteratiu import RefinadorIteratiu, ResultatRefinament
from agents.v2.models import (
    AnalisiPreTraduccio,
    ContextTraduccioEnriquit,
    ContextAvaluacio,
    FeedbackFusionat,
    LlindarsAvaluacio,
    LLINDARS_DEFAULT,
)

# Agents V1 (reutilitzats)
from agents.glossarista import GlossaristaAgent, GlossaryRequest
from agents.chunker_agent import ChunkerAgent, ChunkingRequest, ChunkingStrategy
from agents.investigador import InvestigadorAgent
from agents.anotador_critic import AnotadorCriticAgent, AnotacioRequest

# Dashboard (opcional)
try:
    from dashboard.server import TranslationDashboard, dashboard as global_dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    global_dashboard = None

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# =============================================================================
# MODELS
# =============================================================================

class FasePipeline(str, Enum):
    """Fases del pipeline (per al resultat)."""
    PENDENT = "pendent"
    GLOSSARI = "creant_glossari"
    CHUNKING = "dividint"
    ANALITZANT = "analitzant"
    TRADUINT = "traduint"
    AVALUANT = "avaluant"
    REFINANT = "refinant"
    FUSIONANT = "fusionant"
    ANOTANT = "anotant"
    VALIDANT = "validant"
    COMPLETAT = "completat"
    ERROR = "error"


class ConfiguracioPipelineV2(BaseModel):
    """Configuració del pipeline v2."""

    # Investigació
    fer_investigacio: bool = Field(default=True, description="Investigar autor i obra abans de traduir")

    # Anàlisi
    fer_analisi_previa: bool = Field(default=True, description="Analitzar text abans de traduir")
    usar_exemples_fewshot: bool = Field(default=True, description="Usar exemples de traduccions similars")
    max_exemples_fewshot: int = Field(default=5, ge=0, le=10)

    # Glossari
    crear_glossari: bool = Field(default=True, description="Crear glossari terminològic")

    # Chunking
    fer_chunking: bool = Field(default=True, description="Dividir text en fragments")
    max_chars_chunk: int = Field(default=3000, description="Mida màxima de cada chunk")
    chunk_strategy: str = Field(default="paragraph", description="Estratègia de chunking")

    # Límits de truncat per evitar excés de tokens
    max_chars_analisi: int = Field(default=10000, description="Límit de caràcters per anàlisi prèvia")
    max_chars_avaluacio: int = Field(default=8000, description="Límit de caràcters per avaluació")
    max_chars_context_memoria: int = Field(default=1500, description="Límit de caràcters per context de memòria")

    # Avaluació i refinament
    fer_avaluacio: bool = Field(default=True, description="Avaluar traduccions")
    fer_refinament: bool = Field(default=True, description="Refinar si no aprovat")
    llindars: LlindarsAvaluacio = Field(default_factory=lambda: LLINDARS_DEFAULT)

    # Anotació crítica
    generar_anotacions: bool = Field(default=True, description="Generar notes crítiques automàticament")
    densitat_notes: Literal["minima", "normal", "exhaustiva"] = Field(
        default="normal",
        description="Densitat de notes: minima (2-3/pàg), normal (4-6/pàg), exhaustiva (8-12/pàg)"
    )

    # Sortida
    incloure_analisi: bool = Field(default=False, description="Incloure anàlisi a la sortida")
    incloure_historial: bool = Field(default=False, description="Incloure historial de refinament")

    # Dashboard
    mostrar_dashboard: bool = Field(default=True, description="Obrir dashboard al navegador")
    dashboard_port: int = Field(default=5050, description="Port del servidor dashboard")

    # Persistència (core)
    habilitar_persistencia: bool = Field(default=True, description="Guardar estat per poder reprendre")
    directori_obra: Path | None = Field(default=None, description="Directori de l'obra (si None, es dedueix)")

    # Validació final (core)
    habilitar_validacio_final: bool = Field(default=True, description="Validar obra abans de publicar")
    bloquejar_si_invalid: bool = Field(default=True, description="No marcar com completat si no passa validació")


class ResultatChunk(BaseModel):
    """Resultat de la traducció d'un chunk."""

    chunk_id: int
    text_original: str
    traduccio_final: str

    # Detalls opcionals
    analisi: AnalisiPreTraduccio | None = None
    avaluacio_final: FeedbackFusionat | None = None
    iteracions_refinament: int = 0
    aprovat: bool = True

    temps_processament: float = 0.0


class ResultatPipelineV2(BaseModel):
    """Resultat complet del pipeline v2."""

    # Texts
    text_original: str
    traduccio_final: str

    # Metadades
    llengua_origen: str
    autor: str | None = None
    obra: str | None = None
    genere: str | None = None

    # Glossari
    glossari: dict[str, str] = Field(default_factory=dict)

    # Notes crítiques
    notes: list[dict] = Field(default_factory=list, description="Llista de notes crítiques generades")
    text_anotat: str | None = Field(default=None, description="Traducció amb marques [^n] inserides")

    # Chunks
    num_chunks: int = 0
    chunks_aprovats: int = 0
    chunks_refinats: int = 0
    resultats_chunks: list[ResultatChunk] = Field(default_factory=list)

    # Qualitat
    puntuacio_mitjana: float = 0.0
    requereix_revisio_humana: bool = False

    # Temps
    temps_total: float = 0.0
    temps_per_fase: dict[str, float] = Field(default_factory=dict)

    # Estat
    fase: FasePipeline = FasePipeline.COMPLETAT
    errors: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)

    def resum(self) -> str:
        """Retorna un resum llegible del resultat."""
        linies = [
            "═══════════════════════════════════════════════════════════════",
            "                    RESULTAT PIPELINE V2",
            "═══════════════════════════════════════════════════════════════",
            f"Obra: {self.obra or 'N/A'} ({self.autor or 'Anònim'})",
            f"Llengua: {self.llengua_origen} → català",
            f"Fase: {self.fase.value}",
            "",
            f"Chunks: {self.chunks_aprovats}/{self.num_chunks} aprovats",
            f"Refinats: {self.chunks_refinats}",
            f"Puntuació mitjana: {self.puntuacio_mitjana:.1f}/10",
            "",
            f"Temps total: {self.temps_total:.1f}s",
        ]

        if self.notes:
            linies.append(f"\nNotes crítiques: {len(self.notes)} generades")

        if self.temps_per_fase:
            linies.append("\nTemps per fase:")
            for fase, temps in self.temps_per_fase.items():
                linies.append(f"  • {fase}: {temps:.1f}s")

        if self.requereix_revisio_humana:
            linies.append("\n⚠ REQUEREIX REVISIÓ HUMANA")

        if self.avisos:
            linies.append("\nAvisos:")
            for a in self.avisos[:5]:
                linies.append(f"  • {a}")

        if self.errors:
            linies.append("\nErrors:")
            for e in self.errors[:5]:
                linies.append(f"  ✗ {e}")

        linies.append("═══════════════════════════════════════════════════════════════")

        return "\n".join(linies)


# =============================================================================
# PIPELINE V2
# =============================================================================

class PipelineV2:
    """Pipeline de traducció v2 amb avaluació dimensional i refinament iteratiu.

    Combina agents v2 (traducció, avaluació, refinament) amb agents v1
    (glossari, chunking) per oferir traduccions de qualitat professional.
    """

    def __init__(
        self,
        config: ConfiguracioPipelineV2 | None = None,
        agent_config: AgentConfig | None = None,
        corpus_path: str | None = None,
        logger: "AgentLogger | None" = None,
        on_progress: Callable[[str, float], None] | None = None,
    ) -> None:
        """Inicialitza el pipeline.

        Args:
            config: Configuració del pipeline.
            agent_config: Configuració pels agents.
            corpus_path: Ruta al corpus d'exemples few-shot.
            logger: Logger per al seguiment.
            on_progress: Callback per reportar progrés (fase, percentatge).
        """
        self.config = config or ConfiguracioPipelineV2()
        self.agent_config = agent_config
        self.logger = logger
        self.on_progress = on_progress

        # Agents V2
        self.analitzador = AnalitzadorPreTraduccio(agent_config, logger)
        self.traductor = TraductorEnriquit(agent_config, logger)
        self.avaluador = AvaluadorDimensional(agent_config, self.config.llindars, logger)
        self.refinador = RefinadorIteratiu(agent_config, self.config.llindars, logger)

        # Selector d'exemples
        self.selector_exemples = SelectorExemplesFewShot(corpus_path)

        # Agents V1 (reutilitzats)
        self.glossarista = GlossaristaAgent(agent_config, logger)
        self.chunker = ChunkerAgent(agent_config, logger)
        self.anotador = AnotadorCriticAgent(agent_config, logger)

        # Dashboard
        self.dashboard: Opt[TranslationDashboard] = None
        if DASHBOARD_AVAILABLE and self.config.mostrar_dashboard:
            self.dashboard = global_dashboard

        # Core: Persistència i memòria contextual
        self.estat: EstatPipeline | None = None
        self.memoria: MemoriaContextual = MemoriaContextual()

    # =========================================================================
    # MÈTODES AUXILIARS CORE
    # =========================================================================

    @staticmethod
    def _crear_slug(text: str) -> str:
        """Converteix text a slug per noms de carpeta."""
        text = unicodedata.normalize("NFKD", text.lower())
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text).strip("-")
        return text[:50]  # Limitar longitud

    def _inicialitzar_estat(self, autor: str, titol: str, llengua: str) -> bool:
        """Inicialitza o carrega estat existent.

        Args:
            autor: Nom de l'autor.
            titol: Títol de l'obra.
            llengua: Llengua original.

        Returns:
            True si és una represa de sessió anterior, False si és nova.
        """
        if not self.config.habilitar_persistencia:
            return False

        # Determinar directori obra
        if self.config.directori_obra:
            obra_dir = Path(self.config.directori_obra)
        else:
            # Crear slug i deduir path
            slug_autor = self._crear_slug(autor or "desconegut")
            slug_titol = self._crear_slug(titol or "sense-titol")
            obra_dir = Path("obres") / slug_autor / slug_titol

        obra_dir.mkdir(parents=True, exist_ok=True)

        self.estat = EstatPipeline(obra_dir, autor or "Desconegut", titol or "Sense títol", llengua)

        # Intentar carregar estat existent
        if self.estat.existeix():
            if self.estat.carregar():
                print(f"[Pipeline] Reprenent sessió: {self.estat.sessio_id}")
                print(f"[Pipeline] Fases completades: {self.estat.fases_completades}")
                return True

        return False

    def _guardar_estat_amb_memoria(self) -> None:
        """Guarda l'estat incloent la memòria contextual."""
        if self.estat:
            # La memòria es guarda per separat al fitxer .memoria_contextual.json
            memoria_path = self.estat.obra_dir / ".memoria_contextual.json"
            memoria_path.write_text(
                json.dumps(self.memoria.exportar(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self.estat.guardar()

    def _carregar_memoria(self) -> None:
        """Carrega la memòria contextual si existeix."""
        if not self.estat:
            return

        memoria_path = self.estat.obra_dir / ".memoria_contextual.json"
        if memoria_path.exists():
            try:
                dades = json.loads(memoria_path.read_text(encoding="utf-8"))
                self.memoria.importar(dades)
                print(f"[Pipeline] Memòria contextual carregada: {self.memoria.num_traduccions} traduccions")
            except Exception as e:
                print(f"[Pipeline] Error carregant memòria: {e}")

    def _validar_final(self) -> bool:
        """Executa validació final.

        Returns:
            True si pot publicar, False altrament.
        """
        if not self.config.habilitar_validacio_final:
            return True

        if not self.estat or not self.estat.obra_dir:
            print("[Pipeline] No es pot validar sense directori d'obra")
            return True  # No bloquejar si no hi ha persistència

        print("[Pipeline] Executant validació final...")
        validador = ValidadorFinal(self.estat.obra_dir)
        resultat = validador.validar(self.memoria)

        # Mostrar informe breu
        print(f"[Pipeline] Validació: {resultat.puntuacio:.1f}% - ", end="")
        if resultat.pot_publicar:
            print("✓ Pot publicar")
        else:
            print(f"✗ {resultat.errors_critics} errors crítics")
            if self.config.bloquejar_si_invalid:
                print("[Pipeline] ⚠️ Publicació bloquejada - corregeix els errors primer")
                print(validador.generar_informe(resultat))

        return resultat.pot_publicar

    @classmethod
    def reprendre(cls, obra_dir: Path, config: ConfiguracioPipelineV2 | None = None) -> "PipelineV2":
        """Crea un pipeline i prepara per carregar l'estat existent.

        Args:
            obra_dir: Directori de l'obra a reprendre.
            config: Configuració opcional.

        Returns:
            Instància de PipelineV2 preparada per reprendre.
        """
        config = config or ConfiguracioPipelineV2()
        config.directori_obra = obra_dir
        config.habilitar_persistencia = True

        pipeline = cls(config)
        return pipeline

    def _reportar_progres(self, fase: str, percentatge: float) -> None:
        """Reporta el progrés si hi ha callback."""
        if self.on_progress:
            self.on_progress(fase, percentatge)

    def traduir(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        obra: str | None = None,
        genere: str | None = None,
        glossari_existent: dict[str, str] | None = None,
    ) -> ResultatPipelineV2:
        """Executa el pipeline complet de traducció.

        Args:
            text: Text original a traduir.
            llengua_origen: Llengua del text original.
            autor: Autor de l'obra (opcional).
            obra: Títol de l'obra (opcional).
            genere: Gènere literari (opcional, es detectarà).
            glossari_existent: Glossari previ a reutilitzar (opcional).

        Returns:
            ResultatPipelineV2 amb la traducció i metadades.
        """
        temps_inici = time.time()
        temps_fases: dict[str, float] = {}
        errors: list[str] = []
        avisos: list[str] = []

        # ═══════════════════════════════════════════════════════════════
        # VALIDACIÓ PRE-TRADUCCIÓ
        # ═══════════════════════════════════════════════════════════════
        validacio = validar_text_entrada(text, llengua_origen)

        # Processar missatges de validació
        for severity, msg in validacio.messages:
            if severity == SeverityLevel.ERROR:
                errors.append(msg)
            elif severity == SeverityLevel.WARNING:
                avisos.append(msg)

        # Si hi ha errors crítics, retornar immediatament
        if validacio.has_errors():
            return ResultatPipelineV2(
                text_original=text,
                traduccio_final="",
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                temps_total=round(time.time() - temps_inici, 2),
                fase=FasePipeline.ERROR,
                errors=errors,
                avisos=avisos,
            )

        # Netejar text si hi ha warnings de caràcters problemàtics
        if validacio.has_warnings():
            text = netejar_text(text)

        # ═══════════════════════════════════════════════════════════════
        # INICIALITZAR ESTAT PERSISTENT (CORE)
        # ═══════════════════════════════════════════════════════════════
        es_represa = self._inicialitzar_estat(
            autor=autor or "Desconegut",
            titol=obra or "Sense títol",
            llengua=llengua_origen
        )

        if es_represa:
            self._carregar_memoria()
            avisos.append(f"Reprenent sessió anterior: {self.estat.sessio_id}")

        # ═══════════════════════════════════════════════════════════════
        # INICIAR DASHBOARD
        # ═══════════════════════════════════════════════════════════════
        if self.dashboard and self.config.mostrar_dashboard:
            self.dashboard.port = self.config.dashboard_port
            self.dashboard.start(
                obra=obra or "Sense títol",
                autor=autor or "Desconegut",
                llengua=llengua_origen,
                open_browser=True
            )
            self.dashboard.log_info("Pipeline", f"Iniciant traducció de '{obra or 'text'}'...")

        try:
            # ═══════════════════════════════════════════════════════════════
            # FASE 0: INVESTIGACIÓ
            # ═══════════════════════════════════════════════════════════════
            fase_investigacio_completada = (
                self.estat and "investigacio" in self.estat.fases_completades
            )

            if fase_investigacio_completada:
                print("[Pipeline] Fase investigació ja completada, saltant...")
                if self.dashboard:
                    self.dashboard.log_info("Pipeline", "Investigació ja completada (represa)")
            elif self.config.fer_investigacio:
                self._reportar_progres("Investigació", 0.0)
                if self.dashboard:
                    self.dashboard.set_stage("investigant")
                    self.dashboard.log_info("Investigador", "Investigant autor i obra...")

                if self.estat:
                    self.estat.iniciar_fase("investigacio")

                temps_fase = time.time()
                try:
                    investigador = InvestigadorAgent()
                    informe = investigador.investigar(
                        autor=autor or "Desconegut",
                        obra=obra or "Sense títol",
                        llengua_origen=llengua_origen,
                        text_mostra=text[:500],  # Primers 500 chars com a mostra
                        memoria=self.memoria,
                    )
                    temps_fases["investigacio"] = time.time() - temps_fase

                    if self.dashboard:
                        self.dashboard.log_success(
                            "Investigador",
                            f"Investigació completada - Fiabilitat: {informe.fiabilitat}/10"
                        )

                except Exception as e:
                    avisos.append(f"Error en investigació: {e}")
                    temps_fases["investigacio"] = time.time() - temps_fase
                    if self.dashboard:
                        self.dashboard.log_warning("Investigador", f"Error: {e}")
                    if self.estat:
                        self.estat.registrar_warning(f"Error investigació: {e}")

                # Marcar fase completada
                if self.estat:
                    self.estat.completar_fase("investigacio")
                    self._guardar_estat_amb_memoria()

            self._reportar_progres("Investigació", 1.0)

            # ═══════════════════════════════════════════════════════════════
            # FASE 1: GLOSSARI
            # ═══════════════════════════════════════════════════════════════
            glossari = glossari_existent or {}

            # Comprovar si ja està completada (represa)
            fase_glossari_completada = (
                self.estat and "glossari" in self.estat.fases_completades
            )

            if fase_glossari_completada:
                print("[Pipeline] Fase glossari ja completada, saltant...")
                if self.dashboard:
                    self.dashboard.log_info("Pipeline", "Glossari ja completat (represa)")
            else:
                self._reportar_progres("Glossari", 0.0)
                if self.dashboard:
                    self.dashboard.set_stage("glossari")
                    self.dashboard.log_info("Glossarista", "Creant glossari terminològic...")

                if self.estat:
                    self.estat.iniciar_fase("glossari")

                if self.config.crear_glossari and not glossari_existent:
                    temps_fase = time.time()
                    try:
                        glossari = self._crear_glossari(text, llengua_origen, genere)
                        temps_fases["glossari"] = time.time() - temps_fase
                        if self.dashboard:
                            self.dashboard.log_success("Glossarista", f"Glossari creat amb {len(glossari)} termes")

                        # Registrar termes a la memòria contextual
                        for terme, traduccio in glossari.items():
                            self.memoria.registrar_traduccio(
                                original=terme,
                                traduccio=traduccio,
                                justificacio="Glossari inicial",
                                chunk_id="glossari"
                            )

                    except Exception as e:
                        avisos.append(f"Error creant glossari: {e}")
                        temps_fases["glossari"] = time.time() - temps_fase
                        if self.dashboard:
                            self.dashboard.log_warning("Glossarista", f"Error creant glossari: {e}")
                        if self.estat:
                            self.estat.registrar_warning(f"Error glossari: {e}")

                # Marcar fase completada i guardar
                if self.estat:
                    self.estat.completar_fase("glossari")
                    self._guardar_estat_amb_memoria()

            self._reportar_progres("Glossari", 1.0)

            # ═══════════════════════════════════════════════════════════════
            # FASE 2: CHUNKING
            # ═══════════════════════════════════════════════════════════════
            fase_chunking_completada = (
                self.estat and "chunking" in self.estat.fases_completades
            )

            if fase_chunking_completada:
                print("[Pipeline] Fase chunking ja completada, saltant...")
                # Recalcular chunks per tenir-los disponibles
                if self.config.fer_chunking and len(text) > self.config.max_chars_chunk:
                    chunks = self._dividir_en_chunks(text, llengua_origen)
                else:
                    chunks = [text]
                if self.dashboard:
                    self.dashboard.log_info("Pipeline", "Chunking ja completat (represa)")
            else:
                self._reportar_progres("Chunking", 0.0)
                if self.dashboard:
                    self.dashboard.set_stage("chunking")
                    self.dashboard.log_info("Chunker", "Dividint text en fragments...")

                if self.estat:
                    self.estat.iniciar_fase("chunking")

                temps_fase = time.time()

                if self.config.fer_chunking and len(text) > self.config.max_chars_chunk:
                    chunks = self._dividir_en_chunks(text, llengua_origen)
                else:
                    chunks = [text]

                temps_fases["chunking"] = time.time() - temps_fase

                # Registrar chunks a l'estat
                if self.estat:
                    chunk_ids = [f"chunk_{i+1}" for i in range(len(chunks))]
                    self.estat.registrar_chunks(chunk_ids)
                    self.estat.completar_fase("chunking")
                    self._guardar_estat_amb_memoria()

            self._reportar_progres("Chunking", 1.0)

            if self.dashboard:
                self.dashboard.log_success("Chunker", f"Text dividit en {len(chunks)} chunks")
                self.dashboard.set_chunks(len(chunks))

            # ═══════════════════════════════════════════════════════════════
            # FASE 3: TRADUCCIÓ DE CHUNKS
            # ═══════════════════════════════════════════════════════════════
            if self.estat:
                self.estat.iniciar_fase("traduccio")

            resultats_chunks: list[ResultatChunk] = []
            puntuacions: list[float] = []

            # Obtenir chunks pendents (per represes)
            chunks_pendents = set()
            if self.estat:
                chunks_pendents = set(self.estat.obtenir_chunks_pendents())

            for i, chunk in enumerate(chunks):
                chunk_id = f"chunk_{i+1}"

                # Saltar chunks ja completats (represa)
                if self.estat and chunk_id not in chunks_pendents and self.estat.chunks_completats > 0:
                    print(f"[Pipeline] Chunk {i+1} ja completat, saltant...")
                    # Crear resultat placeholder per mantenir ordre
                    resultats_chunks.append(ResultatChunk(
                        chunk_id=i + 1,
                        text_original=chunk,
                        traduccio_final="[CARREGAT DE SESSIÓ ANTERIOR]",
                        aprovat=True,
                    ))
                    continue

                progres_chunk = i / len(chunks)
                self._reportar_progres(f"Traduint chunk {i+1}/{len(chunks)}", progres_chunk)

                # Marcar chunk en curs
                if self.estat:
                    self.estat.iniciar_chunk(chunk_id)

                temps_chunk = time.time()

                try:
                    # Dashboard: chunk en processament
                    if self.dashboard:
                        self.dashboard.update_chunk(i, "analitzant")
                        self.dashboard.log_info("Pipeline", f"Processant chunk {i+1}/{len(chunks)}...")

                    resultat_chunk = self._processar_chunk(
                        chunk_id=i + 1,
                        text_chunk=chunk,
                        llengua_origen=llengua_origen,
                        autor=autor,
                        obra=obra,
                        genere=genere,
                        glossari=glossari,
                        chunk_index=i,  # Per actualitzar dashboard
                    )
                    resultat_chunk.temps_processament = time.time() - temps_chunk
                    resultats_chunks.append(resultat_chunk)

                    if resultat_chunk.avaluacio_final:
                        puntuacio = resultat_chunk.avaluacio_final.puntuacio_global
                        puntuacions.append(puntuacio)
                        # Dashboard: chunk completat amb qualitat
                        if self.dashboard:
                            self.dashboard.update_chunk(
                                i, "completat",
                                quality=puntuacio,
                                iterations=resultat_chunk.iteracions_refinament
                            )
                            self.dashboard.log_success(
                                "Pipeline",
                                f"Chunk {i+1} completat - Qualitat: {puntuacio:.1f}/10"
                            )

                        # Guardar estat després de cada chunk
                        if self.estat:
                            self.estat.completar_chunk(chunk_id, qualitat=puntuacio)
                            self._guardar_estat_amb_memoria()

                    elif self.dashboard:
                        # Chunk sense avaluació
                        self.dashboard.update_chunk(i, "completat", quality=7.5, iterations=0)
                        self.dashboard.log_success("Pipeline", f"Chunk {i+1} completat")

                        # Guardar estat sense puntuació
                        if self.estat:
                            self.estat.completar_chunk(chunk_id, qualitat=7.5)
                            self._guardar_estat_amb_memoria()

                except ContentFilterError as e:
                    # Error de filtratge de contingut: suggerir chunks més petits
                    error_msg = (
                        f"Chunk {i+1} bloquejat per filtratge de contingut. "
                        f"Prova amb max_chars_chunk més petit (actual: {self.config.max_chars_chunk})"
                    )
                    errors.append(error_msg)
                    avisos.append(
                        "El text conté contingut que activa filtres de seguretat. "
                        "Considereu dividir-lo en fragments més petits o revisar el text."
                    )
                    if self.dashboard:
                        self.dashboard.update_chunk(i, "completat", quality=0, iterations=0)
                        self.dashboard.log_error("Pipeline", error_msg)
                    resultats_chunks.append(ResultatChunk(
                        chunk_id=i + 1,
                        text_original=chunk,
                        traduccio_final=f"[FILTRE DE CONTINGUT: Fragment massa sensible]",
                        aprovat=False,
                    ))

                    # Registrar error a l'estat
                    if self.estat:
                        self.estat.registrar_error(error_msg)
                        self.estat.completar_chunk(chunk_id, qualitat=0.0)
                        self._guardar_estat_amb_memoria()

                except Exception as e:
                    errors.append(f"Error en chunk {i+1}: {e}")
                    if self.dashboard:
                        self.dashboard.update_chunk(i, "completat", quality=0, iterations=0)
                        self.dashboard.log_error("Pipeline", f"Error en chunk {i+1}: {e}")
                    # Crear resultat amb traducció buida per mantenir ordre
                    resultats_chunks.append(ResultatChunk(
                        chunk_id=i + 1,
                        text_original=chunk,
                        traduccio_final=f"[ERROR: {e}]",
                        aprovat=False,
                    ))

                    # Registrar error a l'estat
                    if self.estat:
                        self.estat.registrar_error(f"Error chunk {i+1}: {e}")
                        self.estat.completar_chunk(chunk_id, qualitat=0.0)
                        self._guardar_estat_amb_memoria()

            # Marcar fase traducció completada
            if self.estat:
                self.estat.completar_fase("traduccio")
                self._guardar_estat_amb_memoria()

            temps_fases["traduccio"] = sum(r.temps_processament for r in resultats_chunks)

            # ═══════════════════════════════════════════════════════════════
            # FASE 4: FUSIÓ
            # ═══════════════════════════════════════════════════════════════
            self._reportar_progres("Fusionant", 0.5)
            if self.dashboard:
                self.dashboard.set_stage("fusionant")
                self.dashboard.log_info("Pipeline", "Fusionant traduccions...")

            temps_fase = time.time()

            traduccio_final = self._fusionar_chunks(resultats_chunks)

            temps_fases["fusio"] = time.time() - temps_fase
            self._reportar_progres("Fusionant", 1.0)

            # ═══════════════════════════════════════════════════════════════
            # FASE 5: ANOTACIÓ CRÍTICA
            # ═══════════════════════════════════════════════════════════════
            notes_generades: list[dict] = []
            text_anotat: str | None = None

            fase_anotacio_completada = (
                self.estat and "anotacio" in self.estat.fases_completades
            )

            if fase_anotacio_completada:
                print("[Pipeline] Fase anotació ja completada, saltant...")
                if self.dashboard:
                    self.dashboard.log_info("Pipeline", "Anotació ja completada (represa)")
            elif self.config.generar_anotacions:
                self._reportar_progres("Anotant", 0.0)
                if self.dashboard:
                    self.dashboard.set_stage("anotant")
                    self.dashboard.log_info("Anotador", "Generant notes crítiques...")

                if self.estat:
                    self.estat.iniciar_fase("anotacio")

                temps_fase = time.time()
                try:
                    notes_generades, text_anotat = self._generar_anotacions(
                        traduccio=traduccio_final,
                        text_original=text,
                        llengua_origen=llengua_origen,
                        genere=genere,
                    )
                    temps_fases["anotacio"] = time.time() - temps_fase

                    if self.dashboard:
                        self.dashboard.log_success(
                            "Anotador",
                            f"Generades {len(notes_generades)} notes crítiques"
                        )

                    # Guardar notes.md si hi ha persistència
                    if self.estat and notes_generades:
                        self._guardar_notes_md(notes_generades)

                except Exception as e:
                    avisos.append(f"Error generant anotacions: {e}")
                    temps_fases["anotacio"] = time.time() - temps_fase
                    if self.dashboard:
                        self.dashboard.log_warning("Anotador", f"Error: {e}")
                    if self.estat:
                        self.estat.registrar_warning(f"Error anotació: {e}")

                # Marcar fase completada
                if self.estat:
                    self.estat.completar_fase("anotacio")
                    self._guardar_estat_amb_memoria()

                self._reportar_progres("Anotant", 1.0)

            # Actualitzar traducció final amb marques si s'han generat notes
            if text_anotat:
                traduccio_final = text_anotat

            # ═══════════════════════════════════════════════════════════════
            # RESULTAT FINAL
            # ═══════════════════════════════════════════════════════════════
            chunks_aprovats = sum(1 for r in resultats_chunks if r.aprovat)
            chunks_refinats = sum(1 for r in resultats_chunks if r.iteracions_refinament > 0)
            puntuacio_mitjana = sum(puntuacions) / len(puntuacions) if puntuacions else 0.0

            # Detectar si cal revisió humana
            requereix_revisio = (
                len(errors) > 0
                or puntuacio_mitjana < self.config.llindars.llindar_revisio_humana
                or chunks_aprovats < len(chunks)
            )

            if requereix_revisio:
                avisos.append("Es recomana revisió humana")

            # ═══════════════════════════════════════════════════════════════
            # VALIDACIÓ FINAL (CORE)
            # ═══════════════════════════════════════════════════════════════
            pot_publicar = True
            if self.config.habilitar_validacio_final and self.estat:
                if self.dashboard:
                    self.dashboard.set_stage("validant")
                    self.dashboard.log_info("Pipeline", "Executant validació final...")

                pot_publicar = self._validar_final()

                if not pot_publicar:
                    avisos.append("Validació final no superada - revisar errors")

            # ═══════════════════════════════════════════════════════════════
            # ACTUALITZAR ESTAT FINAL
            # ═══════════════════════════════════════════════════════════════
            if self.estat:
                self.estat.completar_fase("fusio")
                self.estat.actualitzar_temps((time.time() - temps_inici) / 60.0)
                self._guardar_estat_amb_memoria()
                print(f"[Pipeline] Estat final guardat: {self.estat.resum()}")

            # ═══════════════════════════════════════════════════════════════
            # DASHBOARD: COMPLETAT
            # ═══════════════════════════════════════════════════════════════
            if self.dashboard:
                temps_total = time.time() - temps_inici
                puntuacio_final = sum(puntuacions) / len(puntuacions) if puntuacions else 0.0
                self.dashboard.set_stage("completat")
                self.dashboard.update_elapsed(temps_total)
                self.dashboard.log_success("Pipeline", "═" * 40)
                self.dashboard.log_success(
                    "Pipeline",
                    f"TRADUCCIÓ COMPLETADA - Qualitat mitjana: {puntuacio_final:.1f}/10"
                )
                self.dashboard.log_success(
                    "Pipeline",
                    f"Chunks: {chunks_aprovats}/{len(chunks)} aprovats | Temps: {temps_total:.1f}s"
                )
                if not pot_publicar:
                    self.dashboard.log_warning("Pipeline", "⚠️ Validació no superada - revisar errors")
                self.dashboard.log_success("Pipeline", "═" * 40)

            return ResultatPipelineV2(
                text_original=text,
                traduccio_final=traduccio_final,
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                glossari=glossari,
                notes=notes_generades,
                text_anotat=text_anotat,
                num_chunks=len(chunks),
                chunks_aprovats=chunks_aprovats,
                chunks_refinats=chunks_refinats,
                resultats_chunks=resultats_chunks if self.config.incloure_historial else [],
                puntuacio_mitjana=round(puntuacio_mitjana, 2),
                requereix_revisio_humana=requereix_revisio,
                temps_total=round(time.time() - temps_inici, 2),
                temps_per_fase=temps_fases,
                fase=FasePipeline.COMPLETAT,
                errors=errors,
                avisos=avisos,
            )

        except Exception as e:
            # Dashboard: error
            if self.dashboard:
                self.dashboard.set_stage("error")
                self.dashboard.log_error("Pipeline", f"Error fatal: {e}")

            # Guardar estat amb error
            if self.estat:
                self.estat.registrar_error(f"Error fatal: {e}")
                self._guardar_estat_amb_memoria()
                print(f"[Pipeline] Estat guardat amb error - es pot reprendre")

            return ResultatPipelineV2(
                text_original=text,
                traduccio_final="",
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                temps_total=round(time.time() - temps_inici, 2),
                fase=FasePipeline.ERROR,
                errors=[str(e)],
            )

    def _crear_glossari(
        self,
        text: str,
        llengua_origen: str,
        genere: str | None,
    ) -> dict[str, str]:
        """Crea glossari utilitzant l'agent v1."""
        request = GlossaryRequest(
            text=text[:5000],  # Limitar per eficiència
            llengua_original=llengua_origen,
            genre=genere,
        )
        response = self.glossarista.create_glossary(request)

        # Parsejar resposta per extreure glossari
        try:
            content = response.content

            # Buscar JSON a la resposta
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                # Extreure termes del glossari
                glossari = {}
                for entry in data.get("glossari", data.get("entries", [])):
                    if isinstance(entry, dict):
                        terme = entry.get("terme_original", entry.get("terme", ""))
                        traduccio = entry.get("traduccio_catalana", entry.get("traduccio", ""))
                        if terme and traduccio:
                            glossari[terme] = traduccio
                return glossari
        except Exception as e:
            print(f"[Pipeline] Error parsejant glossari JSON: {e}")

        return {}

    def _dividir_en_chunks(
        self,
        text: str,
        llengua_origen: str,
    ) -> list[str]:
        """Divideix el text en chunks utilitzant l'agent v1."""
        try:
            request = ChunkingRequest(
                text=text,
                source_language=llengua_origen,
                max_chunk_size=self.config.max_chars_chunk,
                strategy=ChunkingStrategy.PARAGRAPH,
            )
            result = self.chunker.chunk(request)
            return [chunk.content for chunk in result.chunks]
        except Exception as e:
            # Fallback: divisió simple per paràgrafs
            print(f"[Pipeline] Error en chunking agent, usant fallback: {e}")
            paragraphs = text.split("\n\n")
            chunks = []
            current_chunk = ""

            for p in paragraphs:
                if len(current_chunk) + len(p) < self.config.max_chars_chunk:
                    current_chunk += p + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = p + "\n\n"

            if current_chunk:
                chunks.append(current_chunk.strip())

            return chunks if chunks else [text]

    def _processar_chunk(
        self,
        chunk_id: int,
        text_chunk: str,
        llengua_origen: str,
        autor: str | None,
        obra: str | None,
        genere: str | None,
        glossari: dict[str, str],
        chunk_index: int = 0,
    ) -> ResultatChunk:
        """Processa un chunk individual: anàlisi → traducció → avaluació → refinament."""

        analisi: AnalisiPreTraduccio | None = None
        avaluacio: FeedbackFusionat | None = None
        iteracions = 0

        # ─────────────────────────────────────────────────────────────
        # ANÀLISI PRE-TRADUCCIÓ
        # ─────────────────────────────────────────────────────────────
        if self.config.fer_analisi_previa:
            if self.dashboard:
                self.dashboard.update_chunk(chunk_index, "analitzant")
                self.dashboard.log_info("Analitzador", f"Analitzant chunk {chunk_id}...")
            analisi = self.analitzador.analitzar(
                text=text_chunk,
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                max_chars=self.config.max_chars_analisi,
            )
            # Usar gènere detectat si no s'ha especificat
            if genere is None and analisi:
                genere = analisi.genere_detectat

        # ─────────────────────────────────────────────────────────────
        # EXEMPLES FEW-SHOT
        # ─────────────────────────────────────────────────────────────
        exemples_fewshot = []
        if self.config.usar_exemples_fewshot:
            exemples_fewshot = self.selector_exemples.seleccionar(
                llengua_origen=llengua_origen,
                genere=genere or "narrativa",
                autor=autor,
                max_exemples=self.config.max_exemples_fewshot,
            )

        # ─────────────────────────────────────────────────────────────
        # TRADUCCIÓ
        # ─────────────────────────────────────────────────────────────
        if self.dashboard:
            self.dashboard.update_chunk(chunk_index, "traduint")
            self.dashboard.log_info("Traductor", f"Traduint chunk {chunk_id}...")

        context = ContextTraduccioEnriquit(
            text_original=text_chunk,
            llengua_origen=llengua_origen,
            autor=autor,
            obra=obra,
            genere=genere or "narrativa",
            analisi=analisi,
            exemples_fewshot=exemples_fewshot,
            glossari=glossari,
        )

        resultat_traduccio = self.traductor.traduir(
            context,
            self.memoria,
            max_chars_context_memoria=self.config.max_chars_context_memoria,
        )
        traduccio_actual = resultat_traduccio.traduccio

        # ─────────────────────────────────────────────────────────────
        # AVALUACIÓ
        # ─────────────────────────────────────────────────────────────
        aprovat = True

        if self.config.fer_avaluacio:
            if self.dashboard:
                self.dashboard.update_chunk(chunk_index, "avaluant")
                self.dashboard.log_info("Avaluador", f"Avaluant qualitat chunk {chunk_id}...")
            context_avaluacio = ContextAvaluacio(
                text_original=text_chunk,
                text_traduit=traduccio_actual,
                llengua_origen=llengua_origen,
                autor=autor,
                genere=genere or "narrativa",
                descripcio_estil_autor=analisi.to_autor if analisi else None,
                glossari=glossari,
                max_chars=self.config.max_chars_avaluacio,
            )
            avaluacio = self.avaluador.avaluar(context_avaluacio)
            aprovat = avaluacio.aprovat

            # ─────────────────────────────────────────────────────────
            # REFINAMENT (si cal)
            # ─────────────────────────────────────────────────────────
            if not aprovat and self.config.fer_refinament:
                if self.dashboard:
                    self.dashboard.update_chunk(chunk_index, "refinant")
                    self.dashboard.log_warning(
                        "Refinador",
                        f"Qualitat {avaluacio.puntuacio_global:.1f} < llindar, refinant chunk {chunk_id}..."
                    )
                resultat_refinament = self.refinador.refinar(
                    traduccio=traduccio_actual,
                    text_original=text_chunk,
                    llengua_origen=llengua_origen,
                    autor=autor,
                    genere=genere or "narrativa",
                    descripcio_estil=analisi.to_autor if analisi else None,
                    glossari=glossari,
                )
                traduccio_actual = resultat_refinament.traduccio_final
                avaluacio = resultat_refinament.avaluacio_final
                iteracions = resultat_refinament.iteracions_realitzades
                aprovat = resultat_refinament.aprovat

        return ResultatChunk(
            chunk_id=chunk_id,
            text_original=text_chunk,
            traduccio_final=traduccio_actual,
            analisi=analisi if self.config.incloure_analisi else None,
            avaluacio_final=avaluacio,
            iteracions_refinament=iteracions,
            aprovat=aprovat,
        )

    def _fusionar_chunks(self, resultats: list[ResultatChunk]) -> str:
        """Fusiona les traduccions dels chunks."""
        traduccions = [r.traduccio_final for r in resultats]
        return "\n\n".join(traduccions)

    def _generar_anotacions(
        self,
        traduccio: str,
        text_original: str,
        llengua_origen: str,
        genere: str | None,
    ) -> tuple[list[dict], str | None]:
        """Genera notes crítiques per a la traducció.

        Args:
            traduccio: Text traduït.
            text_original: Text original.
            llengua_origen: Llengua d'origen.
            genere: Gènere literari.

        Returns:
            Tupla (llista de notes, text amb marques [^n]).
        """
        # Obtenir context històric com a string
        context_historic_str: str | None = None
        if self.memoria:
            ctx_inv = self.memoria.obtenir_context_investigacio()
            if ctx_inv:
                parts = []
                if ctx_inv.context_historic:
                    parts.append(ctx_inv.context_historic)
                if ctx_inv.context_obra:
                    parts.append(ctx_inv.context_obra)
                if ctx_inv.autor_bio:
                    parts.append(ctx_inv.autor_bio)
                context_historic_str = "\n\n".join(parts) if parts else None

        request = AnotacioRequest(
            text=traduccio,
            text_original=text_original,
            llengua_origen=llengua_origen,
            genere=genere or "narrativa",
            context_historic=context_historic_str,
            densitat_notes=self.config.densitat_notes,
        )

        response = self.anotador.annotate(request, self.memoria)

        # Parsejar resposta JSON
        notes: list[dict] = []
        text_anotat: str | None = None

        try:
            content = response.content

            # Buscar JSON a la resposta
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())

                # Extreure text anotat
                text_anotat = data.get("text_anotat")

                # Extreure notes
                for nota in data.get("notes", []):
                    if isinstance(nota, dict):
                        notes.append({
                            "numero": nota.get("numero", len(notes) + 1),
                            "tipus": nota.get("tipus", "cultural"),
                            "text_referit": nota.get("text_referit", ""),
                            "nota": nota.get("nota", ""),
                        })

                # Log estadístiques
                stats = data.get("estadistiques", {})
                if stats:
                    print(f"[Anotador] Estadístiques: {stats.get('total_notes', len(notes))} notes")
                    per_tipus = stats.get("per_tipus", {})
                    for tipus, count in per_tipus.items():
                        if count > 0:
                            print(f"  • {tipus}: {count}")

        except json.JSONDecodeError as e:
            print(f"[Anotador] Error parsejant JSON: {e}")
            # Intentar extreure notes manualment si falla el JSON
            pass

        return notes, text_anotat

    def _guardar_notes_md(self, notes: list[dict]) -> None:
        """Guarda les notes al fitxer notes.md.

        Args:
            notes: Llista de notes a guardar.
        """
        if not self.estat or not self.estat.obra_dir:
            return

        notes_path = self.estat.obra_dir / "notes.md"

        # Generar contingut markdown
        linies = [
            "# Notes crítiques",
            "",
            "*Notes generades automàticament per l'Agent Anotador Crític.*",
            "",
            "---",
            "",
        ]

        # Agrupar notes per tipus per a millor organització
        tipus_ordre = [
            "historic",
            "prosopografic",
            "cultural",
            "terminologic",
            "intertextual",
            "geographic",
            "textual",
        ]

        tipus_noms = {
            "historic": "Context Històric",
            "prosopografic": "Personatges",
            "cultural": "Context Cultural",
            "terminologic": "Terminologia",
            "intertextual": "Intertextualitat",
            "geographic": "Geografia",
            "textual": "Variants Textuals",
        }

        for nota in sorted(notes, key=lambda n: n.get("numero", 0)):
            numero = nota.get("numero", "?")
            tipus = nota.get("tipus", "cultural")
            text_referit = nota.get("text_referit", "")
            contingut = nota.get("nota", "")

            tipus_tag = tipus_noms.get(tipus, tipus.capitalize())

            linies.append(f"## [{numero}] {text_referit[:50]}{'...' if len(text_referit) > 50 else ''}")
            linies.append("")
            linies.append(f"**Tipus:** {tipus_tag}")
            linies.append("")
            if text_referit:
                linies.append(f"> «{text_referit}»")
                linies.append("")
            linies.append(contingut)
            linies.append("")

        # Guardar fitxer
        notes_path.write_text("\n".join(linies), encoding="utf-8")
        print(f"[Pipeline] Notes guardades a: {notes_path}")

    # =========================================================================
    # MÈTODES DE CONVENIÈNCIA
    # =========================================================================

    def traduir_simple(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        genere: str = "narrativa",
    ) -> str:
        """Traducció simple que retorna només el text.

        Args:
            text: Text a traduir.
            llengua_origen: Llengua del text.
            autor: Autor (opcional).
            genere: Gènere literari.

        Returns:
            Text traduït.
        """
        resultat = self.traduir(
            text=text,
            llengua_origen=llengua_origen,
            autor=autor,
            genere=genere,
        )
        return resultat.traduccio_final

    def traduir_amb_qualitat(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        genere: str = "narrativa",
        llindar_minim: float = 8.0,
    ) -> tuple[str, float, bool]:
        """Traducció amb garantia de qualitat mínima.

        Args:
            text: Text a traduir.
            llengua_origen: Llengua del text.
            autor: Autor (opcional).
            genere: Gènere literari.
            llindar_minim: Puntuació mínima requerida.

        Returns:
            Tupla (traducció, puntuació, assolit_llindar).
        """
        # Configurar llindars més estrictes
        config_estricte = ConfiguracioPipelineV2(
            llindars=LlindarsAvaluacio(
                global_minim=llindar_minim,
                veu_autor_minim=llindar_minim - 0.5,
                max_iteracions=5,  # Més iteracions
            )
        )

        pipeline = PipelineV2(config=config_estricte, agent_config=self.agent_config)
        resultat = pipeline.traduir(
            text=text,
            llengua_origen=llengua_origen,
            autor=autor,
            genere=genere,
        )

        assolit = resultat.puntuacio_mitjana >= llindar_minim

        return resultat.traduccio_final, resultat.puntuacio_mitjana, assolit
