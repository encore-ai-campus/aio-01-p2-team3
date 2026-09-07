"""실제 Ollama·PostgreSQL·pgvector stool 검색 통합 테스트입니다."""

import os

import pytest

from ..config import settings
from ..repositories.care_log_repository import connect
from ..repositories.rag_repository import search_stool_documents
from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation
from ..services.embedding_service import create_query_embedding
from ..services.stool_rag_service import build_stool_search_query


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RAG_DB_TESTS") != "1",
    reason="RUN_RAG_DB_TESTS=1일 때 실제 stool RAG 통합 테스트를 실행합니다.",
)


def search_real_stool_documents(
    *, baby_age_months: int, color: str, black: bool = False, pale: bool = False
) -> list[dict]:
    observation = StoolObservation(
        color=color,
        consistency="soft",
        visible_red_area=False,
        black_tarry_appearance=black,
        pale_or_white_appearance=pale,
        uncertainty="low",
        notes=[],
    )
    request = AnalyzeInfantStoolInput(
        baby_id="integration-test-baby",
        image_path="temporary/integration-test.jpg",
        baby_age_months=baby_age_months,
        feeding_type="formula",
    )
    query = build_stool_search_query(observation, request)
    embedding = create_query_embedding(query)
    assert len(embedding) == settings.ollama_embedding_dimension == 768
    return search_stool_documents(
        query_embedding=embedding,
        baby_age_months=baby_age_months,
        top_k=settings.rag_top_k,
        min_similarity=settings.rag_min_similarity,
    )


def test_newborn_white_stool_returns_acholic_stool_source() -> None:
    rows = search_real_stool_documents(
        baby_age_months=0,
        color="white",
        pale=True,
    )

    assert rows, "Info Server의 category='stool' 테스트 색인 데이터가 필요합니다."
    assert all(0 <= float(row["score"]) <= 1 for row in rows)
    assert all(row["document_id"] and row["content"] for row in rows)
    assert any("무담즙변" in row["title"] for row in rows)


def test_twelve_month_black_stool_returns_melena_source() -> None:
    rows = search_real_stool_documents(
        baby_age_months=12,
        color="black",
        black=True,
    )

    assert rows
    assert any("혈변" in row["title"] or "흑색변" in row["title"] for row in rows)


def test_twelve_month_white_stool_excludes_newborn_only_source() -> None:
    rows = search_real_stool_documents(
        baby_age_months=12,
        color="white",
        pale=True,
    )

    assert all("신생아 황달과 무담즙변" not in row["title"] for row in rows)


def test_indexed_embeddings_use_team_dimension() -> None:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT vector_dims(dc.embedding) AS dimensions
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE d.is_active = TRUE AND d.category = 'stool'
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    assert row is not None, "stool 임베딩 데이터가 필요합니다."
    assert row["dimensions"] == settings.ollama_embedding_dimension == 768


def test_care_db_role_cannot_modify_rag_tables() -> None:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                has_table_privilege(current_user, 'documents', 'SELECT') AS documents_select,
                has_table_privilege(current_user, 'document_chunks', 'SELECT') AS chunks_select,
                has_table_privilege(current_user, 'documents', 'INSERT,UPDATE,DELETE,TRUNCATE') AS documents_write,
                has_table_privilege(current_user, 'document_chunks', 'INSERT,UPDATE,DELETE,TRUNCATE') AS chunks_write
            """
        )
        privileges = cursor.fetchone()

    assert privileges is not None
    assert privileges["documents_select"] is True
    assert privileges["chunks_select"] is True
    assert privileges["documents_write"] is False
    assert privileges["chunks_write"] is False
