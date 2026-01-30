# Utilitats generals del projecte

from utils.logger import (
    AgentLogger,
    SessionStats,
    VerbosityLevel,
    get_logger,
    reset_logger,
    AGENT_ICONS,
)
from utils.dashboard import (
    Dashboard,
    DashboardState,
    ProgressTracker,
    AgentStatus,
    create_summary_table,
    print_agent_activity,
)
from utils.translation_logger import (
    TranslationLogger,
    LogLevel,
    LogColors,
    LiveDashboard,
)
from utils.checkpointer import (
    Checkpointer,
    ChunkCheckpoint,
    PipelineCheckpoint,
)
from utils.detector_calcs import (
    DetectorCalcs,
    detectar_calcs,
    ResultatDeteccio,
    CalcDetectat,
    TipusCalc,
)

# Corrector lingüístic (LanguageTool)
try:
    from utils.corrector_linguistic import (
        CorrectorLinguistic,
        corregir_text,
        obtenir_puntuacio_normativa,
        es_languagetool_disponible,
        ResultatCorreccio,
        ErrorLinguistic,
        CategoriaError,
        LANGUAGETOOL_DISPONIBLE,
    )
except ImportError:
    LANGUAGETOOL_DISPONIBLE = False

__all__ = [
    # Logger
    "AgentLogger",
    "SessionStats",
    "VerbosityLevel",
    "get_logger",
    "reset_logger",
    "AGENT_ICONS",
    # Dashboard
    "Dashboard",
    "DashboardState",
    "ProgressTracker",
    "AgentStatus",
    "create_summary_table",
    "print_agent_activity",
    # Translation Logger
    "TranslationLogger",
    "LogLevel",
    "LogColors",
    "LiveDashboard",
    # Checkpointer
    "Checkpointer",
    "ChunkCheckpoint",
    "PipelineCheckpoint",
    # Detector de calcs
    "DetectorCalcs",
    "detectar_calcs",
    "ResultatDeteccio",
    "CalcDetectat",
    "TipusCalc",
    # Corrector lingüístic
    "CorrectorLinguistic",
    "corregir_text",
    "obtenir_puntuacio_normativa",
    "es_languagetool_disponible",
    "ResultatCorreccio",
    "ErrorLinguistic",
    "CategoriaError",
    "LANGUAGETOOL_DISPONIBLE",
]
