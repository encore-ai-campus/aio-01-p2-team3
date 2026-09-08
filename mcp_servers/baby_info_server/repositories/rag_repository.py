"""Read-only pgvector retrieval repository.

`category` intentionally lives only on `documents`, matching the shared DB
contract.  The query uses cosine similarity and age ranges are open when null.
"""

from dataclasses import dataclass

from ..config import settings


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    chunk_id: str
    content: str
    title: str
    organization: str
    url: str
    verified_at: str | None
    score: float


async def search_chunks(category: str, embedding: list[float], baby_age_months: int | None, top_k: int) -> list[RetrievedChunk]:
    if not settings.postgres_dsn:
        raise RuntimeError("RAG 데이터베이스 설정이 없습니다.")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("RAG 데이터베이스 드라이버를 사용할 수 없습니다.") from exc
    vector = "[" + ",".join(str(value) for value in embedding) + "]"
    sql = """
        SELECT d.id AS document_id, c.id AS chunk_id, c.content, d.title,
               d.organization, d.source_url AS url, d.verified_at,
               1 - (c.embedding <=> %(embedding)s::vector) AS score
        FROM document_chunks c JOIN documents d ON d.id = c.document_id
        WHERE d.category = %(category)s
          AND (%(age)s IS NULL OR ((c.age_min_months IS NULL OR c.age_min_months <= %(age)s)
              AND (c.age_max_months IS NULL OR c.age_max_months >= %(age)s)))
        ORDER BY c.embedding <=> %(embedding)s::vector LIMIT %(top_k)s
    """
    try:
        async with await psycopg.AsyncConnection.connect(settings.postgres_dsn, row_factory=dict_row) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, {"embedding": vector, "category": category, "age": baby_age_months, "top_k": top_k})
                rows = await cursor.fetchall()
    except psycopg.Error as exc:
        raise RuntimeError("RAG 지식 저장소를 사용할 수 없습니다.") from exc
    return [RetrievedChunk(
        document_id=row["document_id"], chunk_id=row["chunk_id"], content=row["content"],
        title=row["title"], organization=row["organization"], url=row["url"],
        verified_at=row["verified_at"].isoformat() if row["verified_at"] else None,
        score=max(0.0, min(1.0, float(row["score"]))),
    ) for row in rows]
