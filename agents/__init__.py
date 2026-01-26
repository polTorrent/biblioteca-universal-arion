# Agents per al pipeline de traducció
from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.chunker_agent import (
    ChunkerAgent,
    ChunkingRequest,
    ChunkingResult,
    ChunkingStrategy,
    ChunkMetadata,
    TextChunk,
)
from agents.reviewer_agent import (
    IssueSeverity,
    ReviewerAgent,
    ReviewIssue,
    ReviewRequest,
)
from agents.translator_agent import TranslationRequest, TranslatorAgent, SupportedLanguage
from agents.corrector import CorrectorAgent, CorrectionRequest
from agents.glossarista import (
    GlossaristaAgent,
    GlossaryRequest,
    GlossaryEntry as GlossaryEntryModel,
    OnomasticEntry,
    DEFAULT_CATEGORIES,
)
from agents.formatter import (
    FormatterAgent,
    FormattingRequest,
    WorkMetadata,
    Section,
    GlossaryEntry as FormatterGlossaryEntry,
)
from agents.venice_client import (
    VeniceClient,
    VeniceError,
    VeniceAPIKeyError,
    VeniceRequestError,
    ImageGenerationRequest,
    generar_portada_llibre,
)
from agents.portadista import (
    AgentPortadista,
    PortadistaConfig,
    PALETES,
    generar_portada_obra,
)
from agents.web_publisher import (
    WebPublisher,
    WebPublisherConfig,
    ObraMetadata,
    publicar_biblioteca,
)
from agents.agent_estil import (
    EstilAgent,
    StyleRequest,
    StyleNote,
)

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "AgentResponse",
    "ChunkerAgent",
    "ChunkingRequest",
    "ChunkingResult",
    "ChunkingStrategy",
    "ChunkMetadata",
    "TextChunk",
    "TranslatorAgent",
    "TranslationRequest",
    "SupportedLanguage",
    "ReviewerAgent",
    "ReviewRequest",
    "ReviewIssue",
    "IssueSeverity",
    "CorrectorAgent",
    "CorrectionRequest",
    "GlossaristaAgent",
    "GlossaryRequest",
    "GlossaryEntryModel",
    "OnomasticEntry",
    "DEFAULT_CATEGORIES",
    "FormatterAgent",
    "FormattingRequest",
    "WorkMetadata",
    "Section",
    "FormatterGlossaryEntry",
    "VeniceClient",
    "VeniceError",
    "VeniceAPIKeyError",
    "VeniceRequestError",
    "ImageGenerationRequest",
    "generar_portada_llibre",
    "AgentPortadista",
    "PortadistaConfig",
    "PALETES",
    "generar_portada_obra",
    "WebPublisher",
    "WebPublisherConfig",
    "ObraMetadata",
    "publicar_biblioteca",
    "EstilAgent",
    "StyleRequest",
    "StyleNote",
]
