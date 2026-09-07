"""Ollama를 사용해 RAG 검색 Query 임베딩을 생성합니다."""

from typing import Any

import httpx

from ..config import settings


class RagServiceError(Exception):
    """Ollama 또는 pgvector 검색을 완료하지 못한 경우입니다."""

    code = "RAG_SERVICE_ERROR"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def create_query_embedding(query: str, client: Any = None) -> list[float]:
    """문서 색인과 동일한 Ollama 모델로 Query를 벡터화합니다."""
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=settings.ollama_timeout_seconds,
        )

    try:
        response = client.post(
            "/api/embed",
            json={"model": settings.ollama_embedding_model, "input": query},
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not embeddings or not isinstance(embeddings[0], list):
            raise ValueError("embeddings가 없습니다.")
        embedding = [float(value) for value in embeddings[0]]
        if len(embedding) != settings.ollama_embedding_dimension:
            raise ValueError(
                f"임베딩 차원이 {settings.ollama_embedding_dimension}이 아닙니다."
            )
        return embedding
    except (httpx.HTTPError, TypeError, ValueError, KeyError) as error:
        raise RagServiceError("Ollama Query 임베딩 생성에 실패했습니다.") from error
    finally:
        if owns_client:
            client.close()
