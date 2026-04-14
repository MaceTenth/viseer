"""Viseer: minimal, traceable web search for agents."""

from .config import PipelineConfig
from .pipeline import SearchPipeline
from .price_validation import PriceConsensusResult, PriceEvidence, validate_price_consensus
from .types import Answer, Citation, Evidence, PageDocument, SearchResult

__all__ = [
    "Answer",
    "Citation",
    "Evidence",
    "PageDocument",
    "PipelineConfig",
    "PriceConsensusResult",
    "PriceEvidence",
    "SearchPipeline",
    "SearchResult",
    "validate_price_consensus",
]

__version__ = "0.1.0"
