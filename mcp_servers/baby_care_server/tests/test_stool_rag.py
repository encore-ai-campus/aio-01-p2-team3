"""Ollama Query 임베딩과 stool 전용 pgvector 검색 테스트입니다."""

from types import SimpleNamespace

import pytest

from ..config import settings
from ..repositories.rag_repository import STOOL_SEARCH_SQL, search_stool_documents
from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation
from ..services import stool_rag_service
from ..services.embedding_service import RagServiceError, create_query_embedding
from ..services.stool_rag_service import build_stool_search_query, find_stool_sources


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def post(self, path, json):
        self.request = (path, json)
        return FakeResponse(self.payload)


def make_observation() -> StoolObservation:
    return StoolObservation(
        color="yellow",
        consistency="loose",
        visible_red_area=False,
        black_tarry_appearance=False,
        pale_or_white_appearance=False,
        uncertainty="low",
        notes=[],
    )


def make_request() -> AnalyzeInfantStoolInput:
    return AnalyzeInfantStoolInput(
        baby_id="baby-001",
        image_path="temporary/test.jpg",
        baby_age_months=3,
        feeding_type="formula",
    )


def test_ollama_embedding_request_and_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_embedding_dimension", 3)
    monkeypatch.setattr(settings, "ollama_embedding_model", "nomic-embed-text")
    client = FakeClient({"embeddings": [[0.1, 0.2, 0.3]]})

    result = create_query_embedding("영아 변 색상", client=client)

    assert result == [0.1, 0.2, 0.3]
    assert client.request == (
        "/api/embed",
        {"model": "nomic-embed-text", "input": "영아 변 색상"},
    )


def test_rejects_wrong_embedding_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_embedding_dimension", 3)
    client = FakeClient({"embeddings": [[0.1, 0.2]]})

    with pytest.raises(RagServiceError):
        create_query_embedding("검색어", client=client)


def test_search_query_contains_observation_and_age() -> None:
    query = build_stool_search_query(make_observation(), make_request())

    assert "생후 3개월" in query
    assert "yellow" in query
    assert "loose" in query


def test_white_stool_query_contains_medical_document_terms() -> None:
    observation = make_observation().model_copy(
        update={"color": "white", "pale_or_white_appearance": True}
    )
    request = make_request().model_copy(update={"baby_age_months": 0})

    query = build_stool_search_query(observation, request)

    assert "생후 0개월" in query
    assert "흰색 변" in query
    assert "회백색 변" in query
    assert "창백한 변" in query
    assert "무담즙변" in query


def test_black_stool_query_contains_black_stool_terms() -> None:
    observation = make_observation().model_copy(
        update={"color": "black", "black_tarry_appearance": True}
    )

    query = build_stool_search_query(observation, make_request())

    assert "검은 변" in query
    assert "타르 같은 변" in query
    assert "흑색변" in query


def test_repository_uses_fixed_stool_and_age_filters() -> None:
    captured = {}

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, query, parameters):
            captured["query"] = query
            captured["parameters"] = parameters

        def fetchall(self):
            return []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def cursor(self):
            return Cursor()

    result = search_stool_documents(
        query_embedding=[0.1, 0.2],
        baby_age_months=3,
        top_k=5,
        min_similarity=0.70,
        connection_factory=Connection,
    )

    assert result == []
    assert "d.category = 'stool'" in captured["query"]
    assert "d.is_active = TRUE" in captured["query"]
    assert "age_min_months" in captured["query"]
    assert captured["parameters"]["baby_age_months"] == 3
    assert captured["parameters"]["top_k"] == 5


def test_rag_sql_is_read_only() -> None:
    normalized = " ".join(STOOL_SEARCH_SQL.upper().split())

    assert normalized.startswith("SELECT ")
    for keyword in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ", "ALTER ", "DROP "):
        assert keyword not in normalized


def test_find_sources_excludes_internal_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stool_rag_service, "create_query_embedding", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        stool_rag_service,
        "search_stool_documents",
        lambda **kwargs: [
            {
                "document_id": "doc-001",
                "chunk_id": "chunk-001",
                "title": "영아 배변 안내",
                "organization": "공식기관",
                "source_url": "https://example.org/stool",
                "verified_at": None,
                "content": "내부 검색 근거",
                "score": 0.9,
            }
        ],
    )

    sources = find_stool_sources(make_observation(), make_request())

    assert sources[0].document_id == "doc-001"
    assert "content" not in sources[0].model_dump()
