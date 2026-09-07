"""Info Server가 관리하는 공용 RAG 테이블을 읽기 전용으로 조회합니다."""

from typing import Any, Callable

from .care_log_repository import connect


STOOL_SEARCH_SQL = """
SELECT d.id AS document_id,
       dc.id AS chunk_id,
       d.title,
       d.organization,
       d.source_url,
       d.verified_at,
       dc.content,
       GREATEST(0.0, LEAST(1.0, 1 - (dc.embedding <=> %(query_embedding)s::vector))) AS score
FROM document_chunks AS dc
JOIN documents AS d ON d.id = dc.document_id
WHERE d.is_active = TRUE
  AND d.category = 'stool'
  AND (
        %(baby_age_months)s::int IS NULL
        OR (
            COALESCE(dc.age_min_months, 0) <= %(baby_age_months)s
            AND COALESCE(dc.age_max_months, 36) >= %(baby_age_months)s
        )
      )
  AND 1 - (dc.embedding <=> %(query_embedding)s::vector) >= %(min_similarity)s
ORDER BY dc.embedding <=> %(query_embedding)s::vector
LIMIT %(top_k)s
"""


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def search_stool_documents(
    *,
    query_embedding: list[float],
    baby_age_months: int | None,
    top_k: int,
    min_similarity: float,
    connection_factory: Callable = connect,
) -> list[dict[str, Any]]:
    """활성 stool 문서 중 월령과 유사도 조건을 만족하는 청크를 찾습니다."""
    parameters = {
        "query_embedding": _vector_literal(query_embedding),
        "baby_age_months": baby_age_months,
        "min_similarity": min_similarity,
        "top_k": top_k,
    }
    with connection_factory() as connection, connection.cursor() as cursor:
        cursor.execute(STOOL_SEARCH_SQL, parameters)
        return [dict(row) for row in cursor.fetchall()]
