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
from agents.corrector import CorrectorAgent, CorrectionRequest  # DEPRECATED
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
from agents.agent_estil import (  # DEPRECATED
    EstilAgent,
    StyleRequest,
    StyleNote,
)
# Nous agents
from agents.perfeccionament_agent import (
    PerfeccionamentAgent,
    PerfeccionamentRequest,
)
from agents.anotador_critic import (
    AnotadorCriticAgent,
    AnotacioRequest,
    NotaCritica,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentResponse",
    # Chunker
    "ChunkerAgent",
    "ChunkingRequest",
    "ChunkingResult",
    "ChunkingStrategy",
    "ChunkMetadata",
    "TextChunk",
    # Translator
    "TranslatorAgent",
    "TranslationRequest",
    "SupportedLanguage",
    # Reviewer
    "ReviewerAgent",
    "ReviewRequest",
    "ReviewIssue",
    "IssueSeverity",
    # Perfeccionament (NOU - reemplaça Corrector i Estil)
    "PerfeccionamentAgent",
    "PerfeccionamentRequest",
    # Anotador Crític (NOU)
    "AnotadorCriticAgent",
    "AnotacioRequest",
    "NotaCritica",
    # Corrector (DEPRECATED)
    "CorrectorAgent",
    "CorrectionRequest",
    # Estil (DEPRECATED)
    "EstilAgent",
    "StyleRequest",
    "StyleNote",
    # Glossarista
    "GlossaristaAgent",
    "GlossaryRequest",
    "GlossaryEntryModel",
    "OnomasticEntry",
    "DEFAULT_CATEGORIES",
    # Formatter
    "FormatterAgent",
    "FormattingRequest",
    "WorkMetadata",
    "Section",
    "FormatterGlossaryEntry",
    # Venice Client
    "VeniceClient",
    "VeniceError",
    "VeniceAPIKeyError",
    "VeniceRequestError",
    "ImageGenerationRequest",
    "generar_portada_llibre",
    # Portadista
    "AgentPortadista",
    "PortadistaConfig",
    "PALETES",
    "generar_portada_obra",
    # Web Publisher
    "WebPublisher",
    "WebPublisherConfig",
    "ObraMetadata",
    "publicar_biblioteca",
]
