"""RAG 입력·결과·월령 계약을 외부 서비스 없이 검증한다."""

from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from schemas.knowledge import KnowledgeSearchRequest
from services.rag_service import RagService
from tools.search_feeding_guide import run as search_feeding_guide


class StubEmbeddingService:
    async def embed(self, query: str) -> list[float]:
        assert query == "수유 간격"
        return [0.1, 0.2]


class StubRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple] = []

    async def search(self, *args):
        self.calls.append(args)
        return self.rows


class StubAnswerService:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, query: str, context: str, safety_notice: str | None) -> str:
        self.calls += 1
        assert query == "수유 간격"
        assert context == "공식 수유 안내"
        return "검색 근거 기반 답변"


def test_knowledge_request_normalizes_query_and_validates_age() -> None:
    request = KnowledgeSearchRequest(query="  수유 간격  ", baby_age_months=3, top_k=5)

    assert request.query == "수유 간격"
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query=" ", baby_age_months=3, top_k=5)
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query="수유", baby_age_months=37, top_k=5)
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query="수유", baby_age_months=3, top_k=11)


@pytest.mark.asyncio
async def test_rag_search_applies_category_age_and_returns_sources() -> None:
    repository = StubRepository([
        {
            "document_id": "doc-001",
            "chunk_id": "chunk-001",
            "title": "공식 수유 안내",
            "organization": "질병관리청",
            "url": "https://example.org/feeding",
            "verified_at": "2026-09-03",
            "content": "공식 수유 안내",
            "score": 1.2,
        }
    ])
    answers = StubAnswerService()
    service = RagService(StubEmbeddingService(), repository, answers, 0.70, 8000)

    response = await service.search("feeding", "수유 간격", 3, 5)

    assert repository.calls[0][1:] == ("feeding", 3, 5, 0.70)
    assert response["success"] is True
    assert response["category"] == "feeding"
    assert response["confidence"] == "high"
    assert response["sources"][0]["score"] == 1.0
    assert answers.calls == 1


@pytest.mark.asyncio
async def test_rag_no_evidence_is_normal_low_confidence_response() -> None:
    answers = StubAnswerService()
    service = RagService(StubEmbeddingService(), StubRepository([]), answers, 0.70, 8000)

    response = await service.search("feeding", "수유 간격", None, 5)

    assert response["success"] is True
    assert response["sources"] == []
    assert response["confidence"] == "low"
    assert answers.calls == 0


@pytest.mark.asyncio
async def test_invalid_tool_input_returns_structured_validation_error() -> None:
    response = await search_feeding_guide(" ", baby_age_months=3, top_k=5)

    assert response == {
        "success": False,
        "message": "질문과 월령 입력값을 확인해 주세요.",
        "error_code": "VALIDATION_ERROR",
    }
