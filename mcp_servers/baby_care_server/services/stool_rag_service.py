"""변 관찰 결과를 검색어로 바꾸고 공용 stool RAG를 조회합니다."""

from ..config import settings
from ..repositories.rag_repository import search_stool_documents
from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation, StoolSource
from .embedding_service import RagServiceError, create_query_embedding


def build_stool_search_query(
    observation: StoolObservation,
    request: AnalyzeInfantStoolInput,
) -> str:
    """사진 관찰값만 사용해 짧고 재현 가능한 검색어를 만듭니다."""
    signals: list[str] = []
    if observation.visible_red_area:
        signals.append("붉은 영역")
    if observation.black_tarry_appearance:
        signals.append("검고 타르 같은 모습")
    if observation.pale_or_white_appearance:
        signals.append("흰색 또는 회백색")
    signal_text = ", ".join(signals) if signals else "뚜렷한 색상 위험 신호 없음"
    return (
        f"생후 {request.baby_age_months}개월 영아의 변 관찰 안내. "
        f"색상 {observation.color}, 형태 {observation.consistency}, "
        f"관찰 신호 {signal_text}"
    )


def find_stool_sources(
    observation: StoolObservation,
    request: AnalyzeInfantStoolInput,
) -> list[StoolSource]:
    """동일 Ollama 모델과 pgvector 검색으로 사용자용 출처를 반환합니다."""
    query = build_stool_search_query(observation, request)
    embedding = create_query_embedding(query)
    try:
        rows = search_stool_documents(
            query_embedding=embedding,
            baby_age_months=request.baby_age_months,
            top_k=settings.rag_top_k,
            min_similarity=settings.rag_min_similarity,
        )
    except Exception as error:
        raise RagServiceError("stool 참고자료 조회에 실패했습니다.") from error

    try:
        return [
            StoolSource(
                document_id=row["document_id"],
                title=row["title"],
                organization=row["organization"],
                source_url=row["source_url"],
                score=float(row["score"]),
            )
            for row in rows
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise RagServiceError("stool 참고자료 응답 형식이 올바르지 않습니다.") from error
