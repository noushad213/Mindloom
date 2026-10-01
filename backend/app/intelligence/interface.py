"""Member 4's pure processing boundary. These implementations are placeholders."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PageAnalysisResult:
    cleaned_text: str
    summary: str
    keywords: list[str]
    simhash: str | None
    embedding: list[float] | None
    summary_method: str | None = None
    embedding_model: str | None = None


@dataclass(frozen=True)
class RelationshipResult:
    candidate_edges: list[dict[str, Any]]
    clusters: list[dict[str, Any]]


def process_page(text: str, title: str, url: str) -> PageAnalysisResult:
    # Deliberately no extraction, NLP, embedding, model call, or network work here.
    return PageAnalysisResult(cleaned_text=text, summary=f"[Stub] {title}"[:400], keywords=[], simhash=None, embedding=None)


def compute_relationships(pages: list[Any], rejected_pairs: set[tuple[str, str]], params: Any) -> RelationshipResult:
    # Empty suggestions are valid until Member 4 supplies the real implementation.
    return RelationshipResult(candidate_edges=[], clusters=[])


def embed_query(query: str) -> list[float] | None:
    # Member 4 supplies the embedding implementation; no model runs in this stub.
    return None
