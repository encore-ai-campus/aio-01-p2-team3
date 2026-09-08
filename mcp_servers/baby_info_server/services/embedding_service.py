"""Ollama embedding client used for query and document vectors."""

import httpx

from ..config import settings


async def embed_text(text: str) -> list[float]:
    """Return one embedding and reject malformed provider responses."""
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/embed",
                json={"model": settings.ollama_embedding_model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("RAG 임베딩 서비스를 사용할 수 없습니다.") from exc
    embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
    vector = embeddings[0] if isinstance(embeddings, list) and embeddings else None
    if not isinstance(vector, list) or not all(isinstance(value, (int, float)) for value in vector):
        raise RuntimeError("RAG 임베딩 응답 형식이 올바르지 않습니다.")
    if len(vector) != settings.ollama_embedding_dimension:
        raise RuntimeError("RAG 임베딩 차원이 설정과 일치하지 않습니다.")
    return [float(value) for value in vector]
