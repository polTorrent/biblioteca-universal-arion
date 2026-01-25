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
from agents.translator_agent import TranslationRequest, TranslatorAgent
from agents.corrector import CorrectorAgent, CorrectionRequest
from agents.glossarista import (
    GlossaristaAgent,
    GlossaryRequest,
    GlossaryEntry as GlossaryEntryModel,
    OnomasticEntry,
)
from agents.formatter import (
    FormatterAgent,
    FormattingRequest,
    WorkMetadata,
    Section,
    GlossaryEntry as FormatterGlossaryEntry,
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
    "FormatterAgent",
    "FormattingRequest",
    "WorkMetadata",
    "Section",
    "FormatterGlossaryEntry",
]
