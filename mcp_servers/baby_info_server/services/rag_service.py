"""Category-fixed RAG orchestration shared by knowledge MCP tools."""

import re

from ..config import settings
from ..repositories.rag_repository import search_chunks
from ..schemas.knowledge import KnowledgeSearchResult, KnowledgeSource
from .answer_service import generate_grounded_answer
from .embedding_service import embed_text

LOW_CONFIDENCE_ANSWER = "확인 가능한 근거를 충분히 찾지 못했습니다."
EMERGENCY_PATTERN = re.compile(r"(의식.*없|호흡.*곤란|청색증|경련|심한.*출혈|119)")


async def search_knowledge(category: str, query: str, baby_age_months: int | None, top_k: int) -> dict:
    safety_notice = "위급해 보이거나 호흡 곤란, 의식 저하, 경련이 있으면 119 또는 응급의료기관에 즉시 연락하세요." if EMERGENCY_PATTERN.search(query) else None
    embedding = await embed_text(query.strip())
    chunks = await search_chunks(category, embedding, baby_age_months, top_k)
    usable = [chunk for chunk in chunks if chunk.score >= settings.rag_min_similarity]
    if not usable:
        return KnowledgeSearchResult(answer=LOW_CONFIDENCE_ANSWER, category=category, confidence="low", safety_notice=safety_notice).model_dump()
    answer = await generate_grounded_answer(query, usable)
    return KnowledgeSearchResult(
        answer=answer, category=category, confidence="high", safety_notice=safety_notice,
        sources=[KnowledgeSource(document_id=item.document_id, chunk_id=item.chunk_id, title=item.title,
                                 organization=item.organization, url=item.url, verified_at=item.verified_at,
                                 score=item.score) for item in usable],
    ).model_dump()
