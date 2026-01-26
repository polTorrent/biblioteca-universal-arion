"""Pipeline editorial per orquestrar la traducció i revisió de textos clàssics."""

import json
import re
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Literal


def parse_json_response(content: str) -> dict | None:
    """Parseja una resposta JSON que pot estar dins de blocs de codi markdown.

    Args:
        content: Contingut de la resposta de l'agent.

    Returns:
        Diccionari amb les dades parseades o None si falla.
    """
    # Primer intent: parsing directe
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Segon intent: extreure JSON de blocs de codi markdown
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Tercer intent: buscar objecte JSON directament
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None

from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from agents import (
    AgentConfig,
    ChunkerAgent,
    ChunkingRequest,
    ChunkingResult,
    ChunkingStrategy,
    ReviewerAgent,
    ReviewRequest,
    TextChunk,
    TranslationRequest,
    TranslatorAgent,
    SupportedLanguage,
    CorrectorAgent,
    CorrectionRequest,
    GlossaristaAgent,
    GlossaryRequest,
    EstilAgent,
    StyleRequest,
    AgentPortadista,
    PortadistaConfig,
)
from utils.logger import AgentLogger, VerbosityLevel, get_logger
from utils.dashboard import Dashboard, ProgressTracker, print_agent_activity
from utils.translation_logger import TranslationLogger, LogLevel


class PipelineStage(str, Enum):
    """Etapes del pipeline."""

    PENDING = "pendent"
    CHUNKING = "seccionant"
    GLOSSARY = "glossariant"
    TRANSLATING = "traduint"
    REVIEWING = "revisant"
    REFINING = "refinant"
    CORRECTING = "corregint"
    STYLING = "estilitzant"
    MERGING = "fusionant"
    COVER = "portadant"
    COMPLETED = "completat"
    FAILED = "fallat"
    PAUSED = "pausat"


class PipelineConfig(BaseModel):
    """Configuració del pipeline."""

    max_revision_rounds: int = Field(default=2, ge=1, le=5)
    min_quality_score: float = Field(default=7.0, ge=1.0, le=10.0)
    save_intermediate: bool = Field(default=True)
    output_dir: Path = Field(default=Path("output"))
    agent_config: AgentConfig = Field(default_factory=AgentConfig)

    # Configuració de chunking
    enable_chunking: bool = Field(default=True)
    max_tokens_per_chunk: int = Field(default=3500, ge=500, le=8000)
    min_tokens_per_chunk: int = Field(default=500, ge=100, le=2000)
    overlap_tokens: int = Field(default=100, ge=0, le=500)
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.AUTO)

    # Configuració de cache i represa
    enable_cache: bool = Field(default=True)
    cache_dir: Path = Field(default=Path(".cache/pipeline"))

    # Configuració de visualització
    verbosity: VerbosityLevel = Field(default=VerbosityLevel.NORMAL)
    use_dashboard: bool = Field(default=False)
    cost_limit_eur: float | None = Field(default=None)

    # Configuració d'agents opcionals
    enable_glossary: bool = Field(default=True)
    enable_correction: bool = Field(default=True)
    correction_level: str = Field(default="normal")  # relaxat, normal, estricte
    enable_styling: bool = Field(default=True)
    style_register: str = Field(default="literari")  # acadèmic, divulgatiu, literari

    # Configuració de portada
    enable_cover: bool = Field(default=True)
    cover_genere: str = Field(default="NOV")  # FIL, POE, TEA, NOV, SAG, ORI, EPO
    cover_output_dir: Path | None = Field(default=None)

    # Configuració del translation logger
    use_translation_logger: bool = Field(default=True)
    project_name: str = Field(default="Traducció")


class StageResult(BaseModel):
    """Resultat d'una etapa del pipeline."""

    stage: PipelineStage
    content: str
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ChunkResult(BaseModel):
    """Resultat del processament d'un chunk."""

    chunk_id: int
    original_text: str
    translated_text: str
    quality_score: float | None = None
    revision_rounds: int = 0
    metadata: dict = Field(default_factory=dict)


class GlossaryEntry(BaseModel):
    """Entrada del glossari acumulatiu."""

    term_original: str
    term_translated: str
    context: str = ""
    first_occurrence_chunk: int = 1
    frequency: int = 1


class AccumulatedContext(BaseModel):
    """Context acumulat durant el processament."""

    glossary: dict[str, GlossaryEntry] = Field(default_factory=dict)
    previous_summaries: list[str] = Field(default_factory=list)
    speakers_encountered: list[str] = Field(default_factory=list)
    current_section: str = ""
    total_chunks_processed: int = 0


class PipelineResult(BaseModel):
    """Resultat final del pipeline."""

    original_text: str
    source_language: SupportedLanguage
    final_translation: str
    quality_score: float | None = None
    revision_rounds: int = 0
    stages: list[StageResult] = Field(default_factory=list)
    author: str | None = None
    work_title: str | None = None

    # Resultats de chunks
    chunk_results: list[ChunkResult] = Field(default_factory=list)
    chunking_info: dict = Field(default_factory=dict)
    accumulated_context: AccumulatedContext = Field(default_factory=AccumulatedContext)

    # Portada generada
    cover_path: Path | None = None

    # Estadístiques
    total_tokens: int = 0
    total_cost_eur: float = 0.0
    total_duration_seconds: float = 0.0

    model_config = {"arbitrary_types_allowed": True}


class PipelineState(BaseModel):
    """Estat del pipeline per permetre pausa/represa."""

    session_id: str
    current_stage: PipelineStage
    current_chunk_index: int = 0
    chunk_results: list[ChunkResult] = Field(default_factory=list)
    accumulated_context: AccumulatedContext = Field(default_factory=AccumulatedContext)
    config: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TranslationPipeline:
    """Pipeline editorial que orquestra traducció i revisió de textos clàssics.

    Flux de treball:
    1. Chunking (si el text és llarg)
    2. Per cada chunk:
       - Traducció inicial amb TranslatorAgent
       - Revisió amb ReviewerAgent
       - Refinament iteratiu si la qualitat és insuficient
    3. Fusió dels resultats
    4. Generació del resultat final
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.console = Console()

        # Inicialitzar logger
        self.logger = get_logger(
            verbosity=self.config.verbosity,
            log_dir=self.config.output_dir / "logs",
        )

        # Inicialitzar agents amb el logger compartit
        self.chunker = ChunkerAgent(config=self.config.agent_config, logger=self.logger)
        self.glossarist = GlossaristaAgent(config=self.config.agent_config, logger=self.logger) if self.config.enable_glossary else None
        self.translator = TranslatorAgent(config=self.config.agent_config, logger=self.logger)
        self.reviewer = ReviewerAgent(config=self.config.agent_config, logger=self.logger)
        self.corrector = CorrectorAgent(config=self.config.agent_config, logger=self.logger) if self.config.enable_correction else None
        self.estil_agent = EstilAgent(config=self.config.agent_config, registre=self.config.style_register) if self.config.enable_styling else None
        self.portadista = AgentPortadista(config=self.config.agent_config) if self.config.enable_cover else None

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.enable_cache:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        self._progress_callback: Callable[[int, int, str], None] | None = None
        self._should_pause = False
        self._dashboard: Dashboard | None = None

        # Estadístiques de la sessió
        self._total_tokens = 0
        self._total_cost = 0.0
        self._start_time: float | None = None

        # Translation logger (nou sistema de logging)
        self._translation_logger: TranslationLogger | None = None
        if self.config.use_translation_logger:
            log_level = LogLevel.DEBUG if self.config.verbosity == VerbosityLevel.VERBOSE else LogLevel.INFO
            self._translation_logger = TranslationLogger(
                log_dir=self.config.output_dir / "logs",
                project_name=self.config.project_name,
                min_level=log_level,
            )

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Estableix callback per actualitzar progrés extern."""
        self._progress_callback = callback

    def request_pause(self) -> None:
        """Sol·licita pausa del pipeline."""
        self._should_pause = True

    def _check_cost_limit(self) -> bool:
        """Comprova si s'ha superat el límit de cost."""
        if self.config.cost_limit_eur is None:
            return True

        if self._total_cost >= self.config.cost_limit_eur:
            self.logger.log_cost_warning(self._total_cost, self.config.cost_limit_eur)
            self.logger.log_warning(
                "Pipeline",
                f"Límit de cost superat: €{self._total_cost:.4f} >= €{self.config.cost_limit_eur:.4f}"
            )
            return False

        # Avisos progressius
        self.logger.log_cost_warning(self._total_cost, self.config.cost_limit_eur)
        return True

    def _update_stats(self, tokens: int, cost: float) -> None:
        """Actualitza les estadístiques globals."""
        self._total_tokens += tokens
        self._total_cost += cost

        if self._dashboard:
            self._dashboard.add_tokens(tokens)
            self._dashboard.add_cost(cost)

    def run(
        self,
        text: str,
        source_language: SupportedLanguage = "llatí",
        author: str | None = None,
        work_title: str | None = None,
        resume_from: PipelineState | None = None,
    ) -> PipelineResult:
        """Executa el pipeline complet de traducció i revisió.

        Args:
            text: Text original a traduir.
            source_language: Llengua d'origen.
            author: Autor del text original.
            work_title: Títol de l'obra.
            resume_from: Estat previ per reprendre.

        Returns:
            PipelineResult amb la traducció final i metadades.
        """
        self._start_time = time.time()

        # Iniciar sessió de logging
        estimated_cost = len(text) / 3 / 1_000_000 * 18 * 3  # Estimació bàsica
        self.logger.log_session_start(
            work_title=work_title or "Text sense títol",
            author=author,
            estimated_cost=estimated_cost,
        )

        result = PipelineResult(
            original_text=text,
            source_language=source_language,
            final_translation="",
            author=author,
            work_title=work_title,
        )

        # Estimar tokens
        estimated_tokens = len(text) // 3

        # Info inicial
        word_count = len(text.split())
        self.logger.log_info(
            "Pipeline",
            f"Text: {word_count:,} paraules, ~{estimated_tokens:,} tokens"
        )

        # Decidir si cal chunking
        needs_chunking = (
            self.config.enable_chunking and
            estimated_tokens > self.config.max_tokens_per_chunk
        )

        # Iniciar translation logger si està actiu
        if self._translation_logger:
            # Estimar chunks
            estimated_chunks = max(1, estimated_tokens // self.config.max_tokens_per_chunk) if needs_chunking else 1
            self._translation_logger.start_pipeline(
                total_chunks=estimated_chunks,
                source_file=work_title or "text"
            )

        try:
            if needs_chunking:
                result = self._run_chunked(text, source_language, author, work_title, resume_from)
            else:
                result = self._run_single(text, source_language, author, work_title)
        finally:
            # Tancar sessió de logging
            elapsed = time.time() - self._start_time if self._start_time else 0
            result.total_tokens = self._total_tokens
            result.total_cost_eur = self._total_cost
            result.total_duration_seconds = elapsed
            self.logger.log_session_end()

            # Completar translation logger
            if self._translation_logger:
                self._translation_logger.complete_pipeline()

        return result

    def _run_single(
        self,
        text: str,
        source_language: SupportedLanguage,
        author: str | None,
        work_title: str | None,
    ) -> PipelineResult:
        """Executa el pipeline per un text curt (sense chunking)."""
        result = PipelineResult(
            original_text=text,
            source_language=source_language,
            final_translation="",
            author=author,
            work_title=work_title,
        )

        # Utilitzar ProgressTracker segons verbositat
        show_progress = self.config.verbosity != VerbosityLevel.QUIET

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=not show_progress,
        ) as progress:
            # Etapa 1: Traducció inicial
            task = progress.add_task("[cyan]Traduint text original...", total=None)
            translation = self._translate(text, source_language, author, work_title)
            result.stages.append(translation)
            progress.remove_task(task)

            if translation.stage == PipelineStage.FAILED:
                result.final_translation = ""
                return result

            current_translation = translation.content

            # Etapa 2: Revisió iterativa
            for round_num in range(self.config.max_revision_rounds):
                if not self._check_cost_limit():
                    break

                task = progress.add_task(
                    f"[yellow]Revisant traducció (ronda {round_num + 1})...",
                    total=None,
                )
                review = self._review(text, current_translation, source_language, author, work_title)
                result.stages.append(review)
                result.revision_rounds += 1
                progress.remove_task(task)

                if review.stage == PipelineStage.FAILED:
                    break

                score = review.metadata.get("quality_score", 0)
                result.quality_score = score

                if score >= self.config.min_quality_score:
                    revised_text = review.metadata.get("revised_text")
                    if revised_text:
                        current_translation = revised_text
                    break

                # Refinament si la qualitat és insuficient
                revised_text = review.metadata.get("revised_text")
                if revised_text and revised_text != current_translation:
                    task = progress.add_task("[magenta]Refinant traducció...", total=None)
                    current_translation = revised_text
                    result.stages.append(
                        StageResult(
                            stage=PipelineStage.REFINING,
                            content=current_translation,
                            metadata={"round": round_num + 1},
                        )
                    )
                    progress.remove_task(task)

            # Etapa 3: Correcció ortogràfica/gramatical (si està habilitada)
            if self.config.enable_correction and self.corrector and current_translation:
                task = progress.add_task("[green]Corregint ortografia i gramàtica...", total=None)

                try:
                    correction_request = CorrectionRequest(
                        text=current_translation,
                        nivell=self.config.correction_level,
                    )
                    correction_response = self.corrector.correct(correction_request)

                    # Actualitzar estadístiques
                    tokens = correction_response.usage.get("input_tokens", 0) + correction_response.usage.get("output_tokens", 0)
                    self._update_stats(tokens, correction_response.cost_eur)

                    # Parsejar resposta JSON
                    correction_data = parse_json_response(correction_response.content)
                    if correction_data:
                        corrected_text = correction_data.get("text_corregit")
                        corrections_list = correction_data.get("correccions", [])

                        if corrected_text:
                            current_translation = corrected_text

                            result.stages.append(
                                StageResult(
                                    stage=PipelineStage.CORRECTING,
                                    content=corrected_text,
                                    metadata={
                                        "corrections_count": len(corrections_list),
                                        "corrections": corrections_list[:10],
                                    },
                                )
                            )

                            if corrections_list:
                                self.logger.log_info(
                                    "Corrector",
                                    f"Aplicades {len(corrections_list)} correccions"
                                )
                    else:
                        self.logger.log_warning("Corrector", "No s'ha pogut parsejar la resposta de correcció")

                except Exception as e:
                    self.logger.log_error("Corrector", e)

                progress.remove_task(task)

            # Etapa 4: Estilització (si està habilitada)
            if self.config.enable_styling and self.estil_agent and current_translation:
                task = progress.add_task("[blue]Polint estil literari...", total=None)

                try:
                    style_request = StyleRequest(
                        text=current_translation,
                        registre=self.config.style_register,
                        preservar_veu=True,
                        autor_original=author,
                    )
                    style_response = self.estil_agent.polish(style_request)

                    # Actualitzar estadístiques
                    tokens = style_response.usage.get("input_tokens", 0) + style_response.usage.get("output_tokens", 0)
                    self._update_stats(tokens, style_response.cost_eur)

                    # Parsejar resposta JSON
                    style_data = parse_json_response(style_response.content)
                    if style_data:
                        styled_text = style_data.get("text_polit")
                        style_notes = style_data.get("notes_edicio", [])
                        improvements = style_data.get("millores_aplicades", {})

                        if styled_text:
                            current_translation = styled_text

                            result.stages.append(
                                StageResult(
                                    stage=PipelineStage.STYLING,
                                    content=styled_text,
                                    metadata={
                                        "improvements": improvements,
                                        "notes_count": len(style_notes),
                                    },
                                )
                            )

                            total_improvements = sum(improvements.values()) if isinstance(improvements, dict) else 0
                            if total_improvements > 0:
                                self.logger.log_info(
                                    "Estil",
                                    f"Aplicades {total_improvements} millores d'estil"
                                )
                    else:
                        self.logger.log_warning("Estil", "No s'ha pogut parsejar la resposta d'estil")

                except Exception as e:
                    self.logger.log_error("Estil", e)

                progress.remove_task(task)

        result.final_translation = current_translation

        # Generar portada si està habilitada
        if self.config.enable_cover and self.portadista:
            self.logger.log_info("Pipeline", "Generant portada...")
            result.cover_path = self._generate_cover(
                work_title=work_title,
                author=author,
                source_language=source_language,
                result=result,
            )
            if result.cover_path:
                result.stages.append(
                    StageResult(
                        stage=PipelineStage.COVER,
                        content=f"Portada generada: {result.cover_path}",
                        metadata={"cover_path": str(result.cover_path)},
                    )
                )

        result.stages.append(
            StageResult(
                stage=PipelineStage.COMPLETED,
                content=current_translation,
                metadata={
                    "quality_score": result.quality_score,
                    "cover_path": str(result.cover_path) if result.cover_path else None,
                },
            )
        )

        if self.config.save_intermediate:
            self._save_result(result)

        return result

    def _run_chunked(
        self,
        text: str,
        source_language: SupportedLanguage,
        author: str | None,
        work_title: str | None,
        resume_from: PipelineState | None = None,
    ) -> PipelineResult:
        """Executa el pipeline amb chunking per textos llargs."""
        result = PipelineResult(
            original_text=text,
            source_language=source_language,
            final_translation="",
            author=author,
            work_title=work_title,
        )

        # Fase 1: Chunking
        self.logger.log_info("Pipeline", "Fase 1: Seccionant el text...")

        chunking_request = ChunkingRequest(
            text=text,
            strategy=self.config.chunking_strategy,
            max_tokens=self.config.max_tokens_per_chunk,
            min_tokens=self.config.min_tokens_per_chunk,
            overlap_tokens=self.config.overlap_tokens,
            source_language=source_language,
        )

        chunking_result = self.chunker.chunk(chunking_request)

        # Mostrar informació del chunking
        if self.config.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
            self._display_chunking_info(chunking_result)

        result.chunking_info = {
            "total_chunks": chunking_result.total_chunks,
            "strategy": chunking_result.strategy_used.value,
            "estimated_tokens": chunking_result.estimated_total_tokens,
        }

        result.stages.append(
            StageResult(
                stage=PipelineStage.CHUNKING,
                content=f"Text dividit en {chunking_result.total_chunks} chunks",
                metadata=result.chunking_info,
            )
        )

        self.logger.log_info(
            "Chunker",
            f"Text dividit en {chunking_result.total_chunks} chunks ({chunking_result.strategy_used.value})"
        )

        # Fase 1.5: Generar glossari inicial si està habilitat
        initial_glossary = {}
        if self.config.enable_glossary and self.glossarist and not resume_from:
            self.logger.log_info("Pipeline", "Fase 1.5: Generant glossari terminològic...")

            # Agafar una mostra del text per generar glossari
            sample_text = text[:8000] if len(text) > 8000 else text

            try:
                glossary_request = GlossaryRequest(
                    text="",  # Sense traducció encara
                    text_original=sample_text,
                    llengua_original=source_language,
                )
                glossary_response = self.glossarist.create_glossary(glossary_request)

                # Intentar parsejar el glossari
                glossary_data = parse_json_response(glossary_response.content)
                if glossary_data and "glossari" in glossary_data:
                    for entry in glossary_data["glossari"]:
                        term_key = entry.get("terme_original", "")
                        if term_key:
                            initial_glossary[term_key] = GlossaryEntry(
                                term_original=term_key,
                                term_translated=entry.get("traduccio_catalana", ""),
                                context=entry.get("context_us", ""),
                                first_occurrence_chunk=1,
                                frequency=1,
                            )

                    self.logger.log_info(
                        "Glossarista",
                        f"Glossari creat amb {len(initial_glossary)} termes"
                    )

                    # Log al translation logger
                    if self._translation_logger:
                        self._translation_logger.log_glossary(len(initial_glossary))

                    # Actualitzar estadístiques
                    tokens = glossary_response.usage.get("input_tokens", 0) + glossary_response.usage.get("output_tokens", 0)
                    self._update_stats(tokens, glossary_response.cost_eur)

                    result.stages.append(
                        StageResult(
                            stage=PipelineStage.GLOSSARY,
                            content=f"Glossari generat amb {len(initial_glossary)} termes",
                            metadata={"terms_count": len(initial_glossary)},
                        )
                    )
                elif glossary_data is None:
                    self.logger.log_warning("Glossarista", "No s'ha pogut parsejar el glossari")
            except Exception as e:
                self.logger.log_error("Glossarista", e)

        # Determinar punt de partida
        start_index = 0
        accumulated_context = AccumulatedContext()

        # Afegir glossari inicial al context
        if initial_glossary:
            accumulated_context.glossary = initial_glossary

        if resume_from:
            start_index = resume_from.current_chunk_index
            accumulated_context = resume_from.accumulated_context
            result.chunk_results = resume_from.chunk_results
            self.logger.log_info("Pipeline", f"Reprenent des del chunk {start_index + 1}...")

        # Inicialitzar dashboard si s'utilitza
        if self.config.use_dashboard:
            self._dashboard = Dashboard(
                work_title=work_title or "Traducció",
                author=author,
                source_language=source_language,
                total_chunks=chunking_result.total_chunks,
            )
            self._dashboard.start()

        try:
            # Fase 2: Processar cada chunk
            self.logger.log_info("Pipeline", "Fase 2: Processant chunks...")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
                disable=self.config.verbosity == VerbosityLevel.QUIET,
            ) as progress:
                main_task = progress.add_task(
                    "[cyan]Traduint...",
                    total=chunking_result.total_chunks,
                    completed=start_index,
                )

                for i, chunk in enumerate(chunking_result.chunks[start_index:], start=start_index):
                    # Comprovar pausa
                    if self._should_pause:
                        self._save_state(
                            result, chunking_result, i, accumulated_context, author, work_title
                        )
                        self.logger.log_warning("Pipeline", f"Pipeline pausat al chunk {i + 1}.")
                        result.stages.append(
                            StageResult(
                                stage=PipelineStage.PAUSED,
                                content=f"Pausat al chunk {i + 1}",
                                metadata={"chunk_index": i},
                            )
                        )
                        return result

                    # Comprovar límit de cost
                    if not self._check_cost_limit():
                        self._save_state(
                            result, chunking_result, i, accumulated_context, author, work_title
                        )
                        result.stages.append(
                            StageResult(
                                stage=PipelineStage.PAUSED,
                                content=f"Aturat per límit de cost al chunk {i + 1}",
                                metadata={"chunk_index": i, "cost": self._total_cost},
                            )
                        )
                        return result

                    # Actualitzar progrés
                    progress.update(
                        main_task,
                        description=f"[cyan]Traduint chunk {i + 1}/{chunking_result.total_chunks}...",
                    )

                    if self._dashboard:
                        self._dashboard.set_chunk(i + 1, chunking_result.total_chunks)
                        self._dashboard.set_active_agent("Traductor", f"Chunk {i + 1}/{chunking_result.total_chunks}")

                    # Log de progrés
                    self.logger.log_progress(
                        "Pipeline",
                        i + 1,
                        chunking_result.total_chunks,
                        f"Processant chunk"
                    )

                    # Iniciar chunk al translation logger
                    chunk_start_time = time.time()
                    if self._translation_logger:
                        self._translation_logger.start_chunk(i + 1, len(chunk.text))

                    # Generar context per aquest chunk
                    context_summary = self.chunker.generate_summary(chunking_result.chunks, i)

                    # Processar el chunk
                    chunk_result = self._process_chunk(
                        chunk=chunk,
                        source_language=source_language,
                        author=author,
                        work_title=work_title,
                        context=accumulated_context,
                        context_summary=context_summary,
                    )

                    result.chunk_results.append(chunk_result)

                    # Completar chunk al translation logger
                    if self._translation_logger:
                        chunk_duration = time.time() - chunk_start_time
                        chunk_tokens = chunk_result.metadata.get("tokens", 0)
                        chunk_cost = chunk_result.metadata.get("cost", 0.0)
                        chunk_quality = chunk_result.quality_score or 7.0
                        self._translation_logger.complete_chunk(
                            chunk_num=i + 1,
                            tokens=chunk_tokens,
                            cost=chunk_cost,
                            quality=chunk_quality,
                            duration=chunk_duration,
                        )

                    # Actualitzar context acumulat
                    self._update_accumulated_context(accumulated_context, chunk, chunk_result)

                    # Actualitzar paraules traduïdes
                    if self._dashboard and chunk_result.translated_text:
                        words = len(chunk_result.translated_text.split())
                        self._dashboard.add_words(words)

                    # Notificar progrés
                    if self._progress_callback:
                        self._progress_callback(
                            i + 1,
                            chunking_result.total_chunks,
                            f"Chunk {i + 1} completat",
                        )

                    progress.update(main_task, advance=1)

                    # Estimar temps restant
                    if self._start_time and self._dashboard:
                        elapsed = time.time() - self._start_time
                        avg_time_per_chunk = elapsed / (i + 1 - start_index) if i > start_index else elapsed
                        remaining_chunks = chunking_result.total_chunks - (i + 1)
                        self._dashboard.set_estimated_remaining(avg_time_per_chunk * remaining_chunks)

                    # Guardar cache intermedi
                    if self.config.enable_cache and (i + 1) % 5 == 0:
                        self._save_state(
                            result, chunking_result, i + 1, accumulated_context, author, work_title
                        )

        finally:
            if self._dashboard:
                self._dashboard.stop()
                self._dashboard = None

        # Fase 3: Fusionar resultats
        self.logger.log_info("Pipeline", "Fase 3: Fusionant traduccions...")

        result.stages.append(
            StageResult(
                stage=PipelineStage.MERGING,
                content="Fusionant traduccions dels chunks",
                metadata={"chunks_merged": len(result.chunk_results)},
            )
        )

        result.final_translation = self._merge_translations(result.chunk_results)
        result.accumulated_context = accumulated_context

        # Calcular puntuació mitjana
        scores = [cr.quality_score for cr in result.chunk_results if cr.quality_score is not None]
        if scores:
            result.quality_score = sum(scores) / len(scores)

        result.revision_rounds = sum(cr.revision_rounds for cr in result.chunk_results)

        # Fase 4: Generar portada si està habilitada
        if self.config.enable_cover and self.portadista:
            self.logger.log_info("Pipeline", "Fase 4: Generant portada...")
            result.cover_path = self._generate_cover(
                work_title=work_title,
                author=author,
                source_language=source_language,
                result=result,
            )
            if result.cover_path:
                result.stages.append(
                    StageResult(
                        stage=PipelineStage.COVER,
                        content=f"Portada generada: {result.cover_path}",
                        metadata={"cover_path": str(result.cover_path)},
                    )
                )

        result.stages.append(
            StageResult(
                stage=PipelineStage.COMPLETED,
                content="Pipeline completat",
                metadata={
                    "total_chunks": len(result.chunk_results),
                    "average_quality": result.quality_score,
                    "total_revisions": result.revision_rounds,
                    "total_tokens": self._total_tokens,
                    "total_cost_eur": self._total_cost,
                    "cover_path": str(result.cover_path) if result.cover_path else None,
                },
            )
        )

        if self.config.save_intermediate:
            self._save_result(result)

        return result

    def _process_chunk(
        self,
        chunk: TextChunk,
        source_language: SupportedLanguage,
        author: str | None,
        work_title: str | None,
        context: AccumulatedContext,
        context_summary: str,
    ) -> ChunkResult:
        """Processa un chunk individual: traducció + revisió."""
        chunk_result = ChunkResult(
            chunk_id=chunk.chunk_id,
            original_text=chunk.text,
            translated_text="",
        )

        # Tracking de tokens i cost per aquest chunk
        chunk_tokens = 0
        chunk_cost = 0.0

        # Construir notes amb context
        notes_parts = []
        if context_summary:
            notes_parts.append(f"Context anterior: {context_summary}")
        if context.glossary:
            glossary_terms = ", ".join(
                f"{e.term_original}={e.term_translated}"
                for e in list(context.glossary.values())[:10]
            )
            notes_parts.append(f"Glossari establert: {glossary_terms}")
        if chunk.metadata.section:
            notes_parts.append(f"Secció actual: {chunk.metadata.section}")

        notes = "\n".join(notes_parts) if notes_parts else None

        # Traducció
        try:
            self.translator.source_language = source_language
            request = TranslationRequest(
                text=chunk.text,
                source_language=source_language,
                author=author,
                work_title=work_title,
                notes=notes,
            )
            response = self.translator.translate(request)
            current_translation = response.content
            chunk_result.metadata["translation_usage"] = response.usage

            # Actualitzar estadístiques
            tokens = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
            chunk_tokens += tokens
            chunk_cost += response.cost_eur
            self._update_stats(tokens, response.cost_eur)

        except Exception as e:
            chunk_result.metadata["error"] = str(e)
            self.logger.log_error("Traductor", e)
            if self._dashboard:
                self._dashboard.add_error(f"Chunk {chunk.chunk_id}: {str(e)}")
            return chunk_result

        # Revisió iterativa
        for round_num in range(self.config.max_revision_rounds):
            if not self._check_cost_limit():
                break

            try:
                if self._dashboard:
                    self._dashboard.set_active_agent(
                        "Revisor",
                        f"Ronda {round_num + 1}/{self.config.max_revision_rounds}"
                    )

                review_request = ReviewRequest(
                    original_text=chunk.text,
                    translated_text=current_translation,
                    source_language=source_language,
                    author=author,
                    work_title=work_title,
                )
                review_response = self.reviewer.review(review_request)
                chunk_result.revision_rounds += 1

                # Actualitzar estadístiques
                tokens = review_response.usage.get("input_tokens", 0) + review_response.usage.get("output_tokens", 0)
                chunk_tokens += tokens
                chunk_cost += review_response.cost_eur
                self._update_stats(tokens, review_response.cost_eur)

                # Parsejar resposta JSON
                review_data = parse_json_response(review_response.content)
                if review_data:
                    score = review_data.get("puntuació_global", 0)
                    chunk_result.quality_score = score
                    issues = review_data.get("problemes", [])

                    # Log de revisió al translation logger
                    if self._translation_logger:
                        self._translation_logger.log_review(
                            chunk_num=chunk.chunk_id,
                            round_num=round_num + 1,
                            score=score,
                            issues=len(issues) if isinstance(issues, list) else 0
                        )

                    if score >= self.config.min_quality_score:
                        revised_text = review_data.get("text_revisat")
                        if revised_text:
                            current_translation = revised_text
                        break

                    revised_text = review_data.get("text_revisat")
                    if revised_text and revised_text != current_translation:
                        current_translation = revised_text
                else:
                    chunk_result.metadata["review_parse_error"] = True
                    self.logger.log_warning("Revisor", "No s'ha pogut parsejar la resposta JSON")
                    break

            except Exception as e:
                chunk_result.metadata["review_error"] = str(e)
                self.logger.log_error("Revisor", e)
                if self._dashboard:
                    self._dashboard.add_error(f"Revisió chunk {chunk.chunk_id}: {str(e)}")
                break

        # Correcció ortogràfica/gramatical si està habilitada
        if self.config.enable_correction and self.corrector and current_translation:
            try:
                if self._dashboard:
                    self._dashboard.set_active_agent("Corrector", "Corregint text")

                correction_request = CorrectionRequest(
                    text=current_translation,
                    nivell=self.config.correction_level,
                )
                correction_response = self.corrector.correct(correction_request)

                # Actualitzar estadístiques
                tokens = correction_response.usage.get("input_tokens", 0) + correction_response.usage.get("output_tokens", 0)
                chunk_tokens += tokens
                chunk_cost += correction_response.cost_eur
                self._update_stats(tokens, correction_response.cost_eur)

                # Parsejar resposta JSON
                correction_data = parse_json_response(correction_response.content)
                if correction_data:
                    corrected_text = correction_data.get("text_corregit")
                    corrections_list = correction_data.get("correccions", [])

                    if corrected_text:
                        current_translation = corrected_text
                        chunk_result.metadata["corrections_count"] = len(corrections_list)
                        chunk_result.metadata["corrections"] = corrections_list[:10]  # Només primeres 10

                        if corrections_list:
                            self.logger.log_info(
                                "Corrector",
                                f"Aplicades {len(corrections_list)} correccions al chunk {chunk.chunk_id}"
                            )
                            # Log al translation logger
                            if self._translation_logger:
                                self._translation_logger.log_correction(
                                    chunk_num=chunk.chunk_id,
                                    corrections=len(corrections_list)
                                )
                else:
                    chunk_result.metadata["correction_parse_error"] = True
                    self.logger.log_warning("Corrector", "No s'ha pogut parsejar la resposta de correcció")

            except Exception as e:
                chunk_result.metadata["correction_error"] = str(e)
                self.logger.log_error("Corrector", e)
                if self._dashboard:
                    self._dashboard.add_error(f"Correcció chunk {chunk.chunk_id}: {str(e)}")

        # Estilització si està habilitada
        if self.config.enable_styling and self.estil_agent and current_translation:
            try:
                if self._dashboard:
                    self._dashboard.set_active_agent("Estil", "Polint estil literari")

                # Construir context per l'agent d'estil
                estil_context = None
                if context.glossary or context.speakers_encountered or context.current_section:
                    context_parts = []
                    if context.current_section:
                        context_parts.append(f"Secció: {context.current_section}")
                    if context.speakers_encountered:
                        context_parts.append(f"Parlants: {', '.join(context.speakers_encountered[:5])}")
                    if context.previous_summaries:
                        context_parts.append(f"Context anterior: {context.previous_summaries[-1][:100]}...")
                    estil_context = " | ".join(context_parts)

                style_request = StyleRequest(
                    text=current_translation,
                    registre=self.config.style_register,
                    preservar_veu=True,
                    autor_original=author,
                    context=estil_context,
                )
                style_response = self.estil_agent.polish(style_request)

                # Actualitzar estadístiques
                tokens = style_response.usage.get("input_tokens", 0) + style_response.usage.get("output_tokens", 0)
                chunk_tokens += tokens
                chunk_cost += style_response.cost_eur
                self._update_stats(tokens, style_response.cost_eur)

                # Parsejar resposta JSON
                style_data = parse_json_response(style_response.content)
                if style_data:
                    styled_text = style_data.get("text_polit")
                    style_notes = style_data.get("notes_edicio", [])
                    improvements = style_data.get("millores_aplicades", {})

                    if styled_text:
                        current_translation = styled_text
                        chunk_result.metadata["styling_applied"] = True
                        chunk_result.metadata["style_improvements"] = improvements
                        chunk_result.metadata["style_notes_count"] = len(style_notes)

                        total_improvements = sum(improvements.values()) if isinstance(improvements, dict) else 0
                        if total_improvements > 0:
                            self.logger.log_info(
                                "Estil",
                                f"Aplicades {total_improvements} millores d'estil al chunk {chunk.chunk_id}"
                            )
                            # Log al translation logger
                            if self._translation_logger:
                                self._translation_logger.log_event(
                                    "styling",
                                    f"Chunk {chunk.chunk_id}: {total_improvements} millores d'estil"
                                )
                else:
                    chunk_result.metadata["style_parse_error"] = True
                    self.logger.log_warning("Estil", "No s'ha pogut parsejar la resposta d'estil")

            except Exception as e:
                chunk_result.metadata["style_error"] = str(e)
                self.logger.log_error("Estil", e)
                if self._dashboard:
                    self._dashboard.add_error(f"Estil chunk {chunk.chunk_id}: {str(e)}")

        chunk_result.translated_text = current_translation

        # Guardar estadístiques del chunk al metadata
        chunk_result.metadata["tokens"] = chunk_tokens
        chunk_result.metadata["cost"] = chunk_cost

        return chunk_result

    def _update_accumulated_context(
        self,
        context: AccumulatedContext,
        chunk: TextChunk,
        chunk_result: ChunkResult,
    ) -> None:
        """Actualitza el context acumulat després de processar un chunk."""
        context.total_chunks_processed += 1

        # Actualitzar secció actual
        if chunk.metadata.section:
            context.current_section = chunk.metadata.section

        # Afegir parlants nous
        for speaker in chunk.metadata.speakers:
            if speaker not in context.speakers_encountered:
                context.speakers_encountered.append(speaker)

        # Generar resum breu per context
        if chunk_result.translated_text:
            summary = chunk_result.translated_text[:200] + "..." if len(chunk_result.translated_text) > 200 else chunk_result.translated_text
            context.previous_summaries.append(summary)
            # Mantenir només els últims 5 resums
            if len(context.previous_summaries) > 5:
                context.previous_summaries = context.previous_summaries[-5:]

    def _merge_translations(self, chunk_results: list[ChunkResult]) -> str:
        """Fusiona les traduccions de tots els chunks."""
        translations = []
        for cr in chunk_results:
            if cr.translated_text:
                translations.append(cr.translated_text)

        return "\n\n".join(translations)

    def _display_chunking_info(self, result: ChunkingResult) -> None:
        """Mostra informació sobre el chunking."""
        table = Table(title="Informació del Chunking")
        table.add_column("Propietat", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Total chunks", str(result.total_chunks))
        table.add_row("Total caràcters", f"{result.total_characters:,}")
        table.add_row("Tokens estimats", f"{result.estimated_total_tokens:,}")
        table.add_row("Estratègia", result.strategy_used.value)

        self.console.print(table)

        # Mostrar estimació de costos
        cost_estimate = self.chunker.estimate_processing_cost(result)
        cost_table = Table(title="Estimació de Costos")
        cost_table.add_column("Concepte", style="cyan")
        cost_table.add_column("Valor", style="yellow")

        cost_table.add_row("Tokens entrada", f"{cost_estimate['estimated_input_tokens']:,}")
        cost_table.add_row("Tokens sortida (est.)", f"{cost_estimate['estimated_output_tokens']:,}")
        cost_table.add_row("Cost entrada", f"${cost_estimate['input_cost_usd']:.4f}")
        cost_table.add_row("Cost sortida", f"${cost_estimate['output_cost_usd']:.4f}")
        cost_table.add_row("Cost total", f"${cost_estimate['total_cost_usd']:.4f}")

        self.console.print(cost_table)

        if result.warnings:
            for warning in result.warnings:
                self.logger.log_warning("Chunker", warning)

    def _save_state(
        self,
        result: PipelineResult,
        chunking_result: ChunkingResult,
        current_index: int,
        context: AccumulatedContext,
        author: str | None,
        work_title: str | None,
    ) -> Path:
        """Desa l'estat del pipeline per poder reprendre."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        state = PipelineState(
            session_id=session_id,
            current_stage=PipelineStage.TRANSLATING,
            current_chunk_index=current_index,
            chunk_results=result.chunk_results,
            accumulated_context=context,
            config={
                "source_language": result.source_language,
                "author": author,
                "work_title": work_title,
            },
            metadata={
                "total_chunks": chunking_result.total_chunks,
                "total_tokens": self._total_tokens,
                "total_cost_eur": self._total_cost,
            },
        )

        state_path = self.config.cache_dir / f"state_{session_id}.json"
        state_path.write_text(state.model_dump_json(indent=2))

        self.logger.log_debug("Pipeline", f"Estat desat a {state_path}")
        return state_path

    def load_state(self, state_path: Path) -> PipelineState:
        """Carrega un estat previ del pipeline."""
        data = json.loads(state_path.read_text())
        return PipelineState.model_validate(data)

    def _translate(
        self,
        text: str,
        source_language: SupportedLanguage,
        author: str | None,
        work_title: str | None,
    ) -> StageResult:
        """Executa la traducció inicial."""
        try:
            self.translator.source_language = source_language
            request = TranslationRequest(
                text=text,
                source_language=source_language,
                author=author,
                work_title=work_title,
            )
            response = self.translator.translate(request)

            # Actualitzar estadístiques
            tokens = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
            self._update_stats(tokens, response.cost_eur)

            return StageResult(
                stage=PipelineStage.TRANSLATING,
                content=response.content,
                metadata={
                    "usage": response.usage,
                    "model": response.model,
                    "duration": response.duration_seconds,
                    "cost_eur": response.cost_eur,
                },
            )
        except Exception as e:
            return StageResult(
                stage=PipelineStage.FAILED,
                content="",
                metadata={"error": str(e)},
            )

    def _review(
        self,
        original_text: str,
        translated_text: str,
        source_language: SupportedLanguage,
        author: str | None,
        work_title: str | None,
    ) -> StageResult:
        """Executa la revisió de la traducció."""
        try:
            request = ReviewRequest(
                original_text=original_text,
                translated_text=translated_text,
                source_language=source_language,
                author=author,
                work_title=work_title,
            )
            response = self.reviewer.review(request)

            # Actualitzar estadístiques
            tokens = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
            self._update_stats(tokens, response.cost_eur)

            # Parsejar la resposta JSON del revisor
            metadata = {
                "raw_response": response.content,
                "duration": response.duration_seconds,
                "cost_eur": response.cost_eur,
            }
            review_data = parse_json_response(response.content)
            if review_data:
                metadata["quality_score"] = review_data.get("puntuació_global", 0)
                metadata["summary"] = review_data.get("resum", "")
                metadata["issues"] = review_data.get("problemes", [])
                metadata["revised_text"] = review_data.get("text_revisat", "")
            else:
                metadata["quality_score"] = 0
                metadata["parse_error"] = "No s'ha pogut parsejar la resposta JSON"

            return StageResult(
                stage=PipelineStage.REVIEWING,
                content=response.content,
                metadata=metadata,
            )
        except Exception as e:
            return StageResult(
                stage=PipelineStage.FAILED,
                content="",
                metadata={"error": str(e)},
            )

    def _generate_cover(
        self,
        work_title: str | None,
        author: str | None,
        source_language: SupportedLanguage,
        result: PipelineResult,
    ) -> Path | None:
        """Genera la portada del llibre amb l'AgentPortadista.

        Args:
            work_title: Títol de l'obra.
            author: Autor del text original.
            source_language: Llengua d'origen per determinar el gènere.
            result: Resultat del pipeline per extreure temes.

        Returns:
            Path a la imatge generada o None si falla.
        """
        if not self.portadista or not self.portadista.venice:
            self.logger.log_warning("Portadista", "Venice client no disponible, saltant generació de portada")
            return None

        try:
            # Determinar gènere basat en la llengua d'origen
            genere_map = {
                "japonès": "ORI",
                "xinès": "ORI",
                "sànscrit": "SAG",
                "grec": "FIL",
                "llatí": "FIL",
                "hebreu": "SAG",
                "alemany": "FIL",
                "anglès": "NOV",
                "francès": "NOV",
                "italià": "POE",
                "rus": "NOV",
                "àrab": "SAG",
                "persa": "POE",
            }
            genere = genere_map.get(source_language, self.config.cover_genere)

            # Extreure temes del glossari si n'hi ha
            temes = []
            if result.accumulated_context.glossary:
                # Agafar els primers termes com a temes
                temes = list(result.accumulated_context.glossary.keys())[:5]

            # Preparar metadata per la portada (incloent gènere)
            metadata = {
                "titol": work_title or "Sense títol",
                "autor": author or "Anònim",
                "genere": genere,
                "temes": temes,
                "descripcio": result.final_translation[:500] if result.final_translation else "",
            }

            # Directori de sortida
            output_dir = self.config.cover_output_dir or self.config.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generar nom del fitxer
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in (work_title or "portada"))
            safe_title = safe_title.replace(" ", "_").lower()[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cover_filename = f"portada_{safe_title}_{timestamp}.png"
            cover_path = output_dir / cover_filename

            # Generar portada
            self.logger.log_info("Portadista", f"Generant portada per '{work_title}' (gènere: {genere})")

            cover_bytes = self.portadista.generar_portada(metadata=metadata)

            # Guardar la imatge
            cover_path.write_bytes(cover_bytes)

            self.logger.log_info("Portadista", f"Portada generada: {cover_path}")
            return cover_path

        except Exception as e:
            self.logger.log_error("Portadista", e)
            return None

    def _save_result(self, result: PipelineResult) -> Path:
        """Desa el resultat en un fitxer JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"translation_{timestamp}.json"
        filepath = self.config.output_dir / filename

        output_data = {
            "original_text": result.original_text[:1000] + "..." if len(result.original_text) > 1000 else result.original_text,
            "source_language": result.source_language,
            "final_translation": result.final_translation,
            "quality_score": result.quality_score,
            "revision_rounds": result.revision_rounds,
            "author": result.author,
            "work_title": result.work_title,
            "chunking_info": result.chunking_info,
            "chunk_count": len(result.chunk_results),
            "total_tokens": result.total_tokens,
            "total_cost_eur": result.total_cost_eur,
            "total_duration_seconds": result.total_duration_seconds,
            "stages": [
                {
                    "stage": s.stage.value,
                    "content": s.content[:500] + "..." if len(s.content) > 500 else s.content,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in result.stages
            ],
        }

        filepath.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
        self.logger.log_debug("Pipeline", f"Resultat desat a {filepath}")
        return filepath

    def display_result(self, result: PipelineResult) -> None:
        """Mostra el resultat formatat a la consola."""
        self.console.print()

        title = "Resultat de la traducció"
        if result.author or result.work_title:
            parts = [p for p in [result.author, result.work_title] if p]
            title += f" - {', '.join(parts)}"

        # Mostrar estadístiques si hi ha chunks
        if result.chunk_results:
            stats_table = Table(title="Estadístiques del Processament")
            stats_table.add_column("Mètrica", style="cyan")
            stats_table.add_column("Valor", style="green")

            stats_table.add_row("Chunks processats", str(len(result.chunk_results)))
            stats_table.add_row("Puntuació mitjana", f"{result.quality_score:.2f}/10" if result.quality_score else "N/A")
            stats_table.add_row("Revisions totals", str(result.revision_rounds))
            stats_table.add_row("Tokens processats", f"{result.total_tokens:,}")
            stats_table.add_row("Cost total", f"€{result.total_cost_eur:.4f}")
            stats_table.add_row("Temps total", f"{result.total_duration_seconds:.1f}s")

            self.console.print(stats_table)
            self.console.print()

        # Mostrar fragment del text original
        original_preview = result.original_text[:500] + "..." if len(result.original_text) > 500 else result.original_text
        self.console.print(Panel(
            original_preview,
            title=f"[bold]Text original ({result.source_language}) - Fragment[/bold]",
            border_style="yellow",
        ))

        self.console.print()

        # Mostrar fragment de la traducció
        translation_preview = result.final_translation[:1000] + "..." if len(result.final_translation) > 1000 else result.final_translation
        self.console.print(Panel(
            translation_preview,
            title="[bold]Traducció final (català) - Fragment[/bold]",
            border_style="green",
        ))

        self.console.print()

        score_color = "green" if (result.quality_score or 0) >= 7 else "yellow" if (result.quality_score or 0) >= 5 else "red"
        self.console.print(f"[bold]Puntuació de qualitat:[/bold] [{score_color}]{result.quality_score or 'N/A'}/10[/{score_color}]")
        self.console.print(f"[bold]Rondes de revisió:[/bold] {result.revision_rounds}")
        self.console.print(f"[bold]Tokens totals:[/bold] {result.total_tokens:,}")
        self.console.print(f"[bold]Cost total:[/bold] €{result.total_cost_eur:.4f}")
        self.console.print()
