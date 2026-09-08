import httpx


class EmbeddingUnavailableError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self, base_url: str, model: str, timeout_seconds: float, dimensions: int) -> None:
        self.url = f"{base_url.rstrip('/')}/api/embed"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        if not self.model:
            raise EmbeddingUnavailableError("Ollama 임베딩 모델 설정이 필요합니다.")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, json={"model": self.model, "input": text})
            response.raise_for_status()
            payload = response.json()
            embeddings = payload.get("embeddings")
            vector = embeddings[0] if embeddings else payload.get("embedding")
            if not isinstance(vector, list) or len(vector) != self.dimensions:
                raise ValueError("임베딩 차원이 설정과 다릅니다.")
            return [float(value) for value in vector]
        except (httpx.HTTPError, ValueError, TypeError, IndexError) as exc:
            raise EmbeddingUnavailableError("Ollama 임베딩을 생성할 수 없습니다.") from exc

