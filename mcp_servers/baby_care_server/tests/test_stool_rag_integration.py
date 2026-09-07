"""실제 Ollama·PostgreSQL·pgvector stool 검색 통합 테스트입니다."""

import os

import pytest

from ..config import settings
from ..repositories.care_log_repository import connect
from ..repositories.rag_repository import search_stool_documents
from ..services.embedding_service import create_query_embedding


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RAG_DB_TESTS") != "1",
    reason="RUN_RAG_DB_TESTS=1일 때 실제 stool RAG 통합 테스트를 실행합니다.",
)


def test_real_ollama_embedding_and_stool_search() -> None:
    query = "생후 3개월 아기의 변 색깔과 묽기 관찰 안내"
    embedding = create_query_embedding(query)

    assert len(embedding) == settings.ollama_embedding_dimension == 768

    rows = search_stool_documents(
        query_embedding=embedding,
        baby_age_months=3,
        top_k=settings.rag_top_k,
        min_similarity=settings.rag_min_similarity,
    )

    assert rows, "Info Server의 category='stool' 테스트 색인 데이터가 필요합니다."
    assert all(0 <= float(row["score"]) <= 1 for row in rows)
    assert all(row["document_id"] and row["content"] for row in rows)


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
