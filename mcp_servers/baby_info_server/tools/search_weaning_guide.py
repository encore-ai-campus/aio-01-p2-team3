from typing import Any

from pydantic import ValidationError

from config import get_rag_service
from repositories.rag_repository import RagRepositoryError
from schemas.knowledge import KnowledgeSearchRequest, ToolErrorResponse
from services.answer_service import AnswerGenerationError
from services.embedding_service import EmbeddingUnavailableError


async def run(query: str, baby_age_months: int | None = None, top_k: int = 5) -> dict[str, Any]:
    try:
        request = KnowledgeSearchRequest(query=query, baby_age_months=baby_age_months, top_k=top_k)
        return await get_rag_service().search("weaning", request.query, request.baby_age_months, request.top_k)
    except ValidationError:
        return ToolErrorResponse(message="질문과 월령 입력값을 확인해 주세요.", error_code="VALIDATION_ERROR").model_dump()
    except (EmbeddingUnavailableError, RagRepositoryError):
        return ToolErrorResponse(message="육아 지식 검색 서비스를 사용할 수 없습니다.", error_code="RAG_SERVICE_UNAVAILABLE").model_dump()
    except AnswerGenerationError:
        return ToolErrorResponse(message="검색 근거로 답변을 생성할 수 없습니다.", error_code="ANSWER_GENERATION_FAILED").model_dump()
