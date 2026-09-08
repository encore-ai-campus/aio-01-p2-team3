from typing import Any

import psycopg
from psycopg.rows import dict_row


class RagRepositoryError(RuntimeError):
    pass


class RagRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def search(
        self,
        embedding: list[float],
        category: str,
        baby_age_months: int | None,
        top_k: int,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        vector = "[" + ",".join(str(value) for value in embedding) + "]"
        sql = """
            SELECT d.id AS document_id, c.id AS chunk_id, d.title, d.organization,
                   d.source_url AS url, d.verified_at, c.content,
                   1 - (c.embedding <=> %s::vector) AS score
              FROM document_chunks c
              JOIN documents d ON d.id = c.document_id
             WHERE d.is_active = TRUE
               AND d.category = %s
               AND (%s::int IS NULL OR
                    (COALESCE(c.age_min_months, 0) <= %s AND
                     COALESCE(c.age_max_months, 36) >= %s))
               AND 1 - (c.embedding <=> %s::vector) >= %s
             ORDER BY c.embedding <=> %s::vector
             LIMIT %s
        """
        params = (vector, category, baby_age_months, baby_age_months, baby_age_months,
                  vector, min_similarity, vector, top_k)
        try:
            async with await psycopg.AsyncConnection.connect(self.dsn, row_factory=dict_row) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, params)
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            raise RagRepositoryError("RAG 데이터베이스를 조회할 수 없습니다.") from exc

