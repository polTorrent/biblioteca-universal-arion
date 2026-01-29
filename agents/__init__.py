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
from agents.glossarista import (
    GlossaristaAgent,
    GlossaryRequest,
    GlossaryEntry as GlossaryEntryModel,
    OnomasticEntry,
    DEFAULT_CATEGORIES,
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
from agents.anotador_critic import (
    AnotadorCriticAgent,
    AnotacioRequest,
    NotaCritica,
)
from agents.cercador_fonts import (
    PescadorTextosAgent as CercadorFontsAgent,
    SearchRequest,
    TextMetadata,
    TextSource,
)
from agents.agents_retratista import (
    AgentRetratista,
    generar_retrat_autor,
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
    # Glossarista
    "GlossaristaAgent",
    "GlossaryRequest",
    "GlossaryEntryModel",
    "OnomasticEntry",
    "DEFAULT_CATEGORIES",
    # Anotador Crític
    "AnotadorCriticAgent",
    "AnotacioRequest",
    "NotaCritica",
    # Cercador de Fonts
    "CercadorFontsAgent",
    "SearchRequest",
    "TextMetadata",
    "TextSource",
    # Retratista
    "AgentRetratista",
    "generar_retrat_autor",
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
