from typing import Any

from constants import EMERGENCY_TERMS, KnowledgeCategory
from repositories.rag_repository import RagRepository
from schemas.knowledge import KnowledgeSource, KnowledgeToolResponse
from services.answer_service import AnswerService
from services.embedding_service import EmbeddingService


class RagService:
    def __init__(
        self,
        embeddings: EmbeddingService,
        repository: RagRepository,
        answers: AnswerService,
        min_similarity: float,
        max_context_chars: int,
    ) -> None:
        self.embeddings = embeddings
        self.repository = repository
        self.answers = answers
        self.min_similarity = min_similarity
        self.max_context_chars = max_context_chars

    async def search(
        self,
        category: KnowledgeCategory,
        query: str,
        baby_age_months: int | None,
        top_k: int,
    ) -> dict[str, Any]:
        emergency = self._contains_emergency_term(query)
        vector = await self.embeddings.embed(query)
        rows = await self.repository.search(
            vector, category, baby_age_months, top_k, self.min_similarity
        )
        safety_notice = (
            "위급하거나 호흡·의식에 문제가 있다면 일반 안내보다 119와 의료기관의 도움을 우선하세요."
            if emergency else None
        )
        if not rows:
            return KnowledgeToolResponse(
                answer="확인 가능한 근거를 충분히 찾지 못했습니다.",
                category=category,
                sources=[],
                confidence="low",
                safety_notice=safety_notice,
            ).model_dump(mode="json")

        context_parts: list[str] = []
        sources: list[KnowledgeSource] = []
        used_chars = 0
        for row in rows:
            content = str(row["content"])
            remaining = self.max_context_chars - used_chars
            if remaining <= 0:
                break
            context_parts.append(content[:remaining])
            used_chars += min(len(content), remaining)
            sources.append(KnowledgeSource(
                document_id=str(row["document_id"]),
                chunk_id=str(row["chunk_id"]),
                title=str(row["title"]),
                organization=str(row["organization"]),
                url=str(row["url"]),
                verified_at=row.get("verified_at"),
                score=max(0.0, min(1.0, float(row["score"]))),
            ))

        answer = await self.answers.generate(query, "\n\n".join(context_parts), safety_notice)
        return KnowledgeToolResponse(
            answer=answer,
            category=category,
            sources=sources,
            confidence="high",
            safety_notice=safety_notice,
        ).model_dump(mode="json")

    @staticmethod
    def _contains_emergency_term(query: str) -> bool:
        return any(term in query for term in EMERGENCY_TERMS)
