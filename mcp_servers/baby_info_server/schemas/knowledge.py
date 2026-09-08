"""Stable input/output contracts for the five knowledge-search MCP tools."""

from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    baby_age_months: int | None = Field(default=None, ge=0, le=36)
    top_k: int = Field(default=5, ge=1, le=10)


class KnowledgeSource(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    organization: str
    url: str
    verified_at: str | None = None
    score: float = Field(ge=0, le=1)


class KnowledgeSearchResult(BaseModel):
    success: bool = True
    answer: str
    category: Literal["feeding", "sleep", "weaning", "development", "safety"]
    sources: list[KnowledgeSource] = Field(default_factory=list)
    confidence: Literal["high", "low"]
    safety_notice: str | None = None
