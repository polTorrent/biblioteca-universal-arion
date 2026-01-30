"""Pipeline de Traducció v2.

Orquestra el flux complet de traducció utilitzant:
- Agents V2: Anàlisi, Traducció, Avaluació, Refinament
- Agents V1: Glossari, Chunker, Portades, EPUB (reutilitzats)
- Dashboard: Monitorització en temps real al navegador

Flux:
1. Glossari (v1) - Crear terminologia consistent
2. Chunking (v1) - Dividir text en fragments manejables
3. Per cada chunk:
   a. Anàlisi Pre-Traducció (v2)
   b. Traducció Enriquida (v2)
   c. Avaluació Dimensional (v2)
   d. Refinament Iteratiu (v2) si cal
4. Fusió de chunks
5. Post-processament (portades, EPUB, etc.)
"""

import time
from typing import Optional as Opt
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, ContentFilterError

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

class EstatPipeline(str, Enum):
    """Estats del pipeline."""
    PENDENT = "pendent"
    GLOSSARI = "creant_glossari"
    CHUNKING = "dividint"
    ANALITZANT = "analitzant"
    TRADUINT = "traduint"
    AVALUANT = "avaluant"
    REFINANT = "refinant"
    FUSIONANT = "fusionant"
    COMPLETAT = "completat"
    ERROR = "error"


class ConfiguracioPipelineV2(BaseModel):
    """Configuració del pipeline v2."""

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

    # Avaluació i refinament
    fer_avaluacio: bool = Field(default=True, description="Avaluar traduccions")
    fer_refinament: bool = Field(default=True, description="Refinar si no aprovat")
    llindars: LlindarsAvaluacio = Field(default_factory=lambda: LLINDARS_DEFAULT)

    # Sortida
    incloure_analisi: bool = Field(default=False, description="Incloure anàlisi a la sortida")
    incloure_historial: bool = Field(default=False, description="Incloure historial de refinament")

    # Dashboard
    mostrar_dashboard: bool = Field(default=True, description="Obrir dashboard al navegador")
    dashboard_port: int = Field(default=5050, description="Port del servidor dashboard")


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
    estat: EstatPipeline = EstatPipeline.COMPLETAT
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
            f"Estat: {self.estat.value}",
            "",
            f"Chunks: {self.chunks_aprovats}/{self.num_chunks} aprovats",
            f"Refinats: {self.chunks_refinats}",
            f"Puntuació mitjana: {self.puntuacio_mitjana:.1f}/10",
            "",
            f"Temps total: {self.temps_total:.1f}s",
        ]

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

        # Dashboard
        self.dashboard: Opt[TranslationDashboard] = None
        if DASHBOARD_AVAILABLE and self.config.mostrar_dashboard:
            self.dashboard = global_dashboard

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
            # FASE 1: GLOSSARI
            # ═══════════════════════════════════════════════════════════════
            self._reportar_progres("Glossari", 0.0)
            if self.dashboard:
                self.dashboard.set_stage("glossari")
                self.dashboard.log_info("Glossarista", "Creant glossari terminològic...")

            glossari = glossari_existent or {}

            if self.config.crear_glossari and not glossari_existent:
                temps_fase = time.time()
                try:
                    glossari = self._crear_glossari(text, llengua_origen, genere)
                    temps_fases["glossari"] = time.time() - temps_fase
                    if self.dashboard:
                        self.dashboard.log_success("Glossarista", f"Glossari creat amb {len(glossari)} termes")
                except Exception as e:
                    avisos.append(f"Error creant glossari: {e}")
                    temps_fases["glossari"] = time.time() - temps_fase
                    if self.dashboard:
                        self.dashboard.log_warning("Glossarista", f"Error creant glossari: {e}")

            self._reportar_progres("Glossari", 1.0)

            # ═══════════════════════════════════════════════════════════════
            # FASE 2: CHUNKING
            # ═══════════════════════════════════════════════════════════════
            self._reportar_progres("Chunking", 0.0)
            if self.dashboard:
                self.dashboard.set_stage("chunking")
                self.dashboard.log_info("Chunker", "Dividint text en fragments...")

            temps_fase = time.time()

            if self.config.fer_chunking and len(text) > self.config.max_chars_chunk:
                chunks = self._dividir_en_chunks(text, llengua_origen)
            else:
                chunks = [text]

            temps_fases["chunking"] = time.time() - temps_fase
            self._reportar_progres("Chunking", 1.0)

            if self.dashboard:
                self.dashboard.log_success("Chunker", f"Text dividit en {len(chunks)} chunks")
                self.dashboard.set_chunks(len(chunks))

            # ═══════════════════════════════════════════════════════════════
            # FASE 3: TRADUCCIÓ DE CHUNKS
            # ═══════════════════════════════════════════════════════════════
            resultats_chunks: list[ResultatChunk] = []
            puntuacions: list[float] = []

            for i, chunk in enumerate(chunks):
                progres_chunk = i / len(chunks)
                self._reportar_progres(f"Traduint chunk {i+1}/{len(chunks)}", progres_chunk)

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
                    elif self.dashboard:
                        # Chunk sense avaluació
                        self.dashboard.update_chunk(i, "completat", quality=7.5, iterations=0)
                        self.dashboard.log_success("Pipeline", f"Chunk {i+1} completat")

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
                self.dashboard.log_success("Pipeline", "═" * 40)

            return ResultatPipelineV2(
                text_original=text,
                traduccio_final=traduccio_final,
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                glossari=glossari,
                num_chunks=len(chunks),
                chunks_aprovats=chunks_aprovats,
                chunks_refinats=chunks_refinats,
                resultats_chunks=resultats_chunks if self.config.incloure_historial else [],
                puntuacio_mitjana=round(puntuacio_mitjana, 2),
                requereix_revisio_humana=requereix_revisio,
                temps_total=round(time.time() - temps_inici, 2),
                temps_per_fase=temps_fases,
                estat=EstatPipeline.COMPLETAT,
                errors=errors,
                avisos=avisos,
            )

        except Exception as e:
            # Dashboard: error
            if self.dashboard:
                self.dashboard.set_stage("error")
                self.dashboard.log_error("Pipeline", f"Error fatal: {e}")

            return ResultatPipelineV2(
                text_original=text,
                traduccio_final="",
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
                temps_total=round(time.time() - temps_inici, 2),
                estat=EstatPipeline.ERROR,
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
            import json
            import re
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
        except Exception:
            pass

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
        except Exception:
            # Fallback: divisió simple per paràgrafs
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

        resultat_traduccio = self.traductor.traduir(context)
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
