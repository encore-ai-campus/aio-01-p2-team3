from datetime import date
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from constants import Confidence, ErrorCode, KnowledgeCategory


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolErrorResponse(StrictModel):
    success: Literal[False] = False
    message: str = Field(min_length=1, max_length=500)
    error_code: ErrorCode


class KnowledgeSearchRequest(StrictModel):
    """다섯 RAG Tool이 공통으로 사용하는 검색 입력 계약입니다."""

    query: str = Field(min_length=2, max_length=500)
    baby_age_months: int | None = Field(default=None, ge=0, le=36)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("query는 공백을 제외하고 2자 이상이어야 합니다.")
        return normalized


class KnowledgeSource(StrictModel):
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    url: AnyHttpUrl
    verified_at: date | None = None
    score: float = Field(ge=0.0, le=1.0)


class KnowledgeToolResponse(StrictModel):
    success: Literal[True] = True
    answer: str = Field(min_length=1)
    category: KnowledgeCategory
    sources: list[KnowledgeSource]
    confidence: Confidence
    safety_notice: str | None = None
