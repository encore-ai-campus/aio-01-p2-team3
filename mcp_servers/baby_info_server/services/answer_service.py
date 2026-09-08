"""Generate an answer strictly from retrieved RAG context."""

from openai import AsyncOpenAI

from ..config import settings
from ..repositories.rag_repository import RetrievedChunk


async def generate_grounded_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(f"[출처 {index + 1}] {chunk.content}" for index, chunk in enumerate(chunks))
    if not settings.openai_api_key:
        # A keyless local setup remains truthful: it never fills gaps with model knowledge.
        return "검색된 공식 자료의 핵심 내용입니다: " + chunks[0].content.strip()
    instructions = ("0~36개월 영유아 보호자에게 한국어로 답하세요. 제공된 출처 내용만 사용하고 "
                    "진단·처방은 하지 마세요. 근거에 없는 내용은 모른다고 말하고 짧게 답하세요.")
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.responses.create(
            model=settings.openai_model, instructions=instructions,
            input=f"질문: {query}\n\n출처:\n{context}",
        )
        answer = response.output_text.strip()
    except Exception as exc:
        raise RuntimeError("근거 기반 답변 생성에 실패했습니다.") from exc
    if not answer:
        raise RuntimeError("근거 기반 답변 생성에 실패했습니다.")
    return answer
