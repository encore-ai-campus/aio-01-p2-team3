"""기저귀 사진 분석의 고정 실행 순서를 관리합니다."""

from collections.abc import Callable
from pathlib import Path

from ..schemas.common import ToolWarning
from ..schemas.stool import (
    AnalyzeInfantStoolInput,
    StoolAnalysisData,
    StoolAnalysisToolResponse,
    StoolObservation,
    StoolRisk,
    StoolSource,
)
from ..services.embedding_service import RagServiceError
from ..services.stool_analysis_service import ValidatedImage


SAFETY_NOTICE = "사진만으로 질환을 진단할 수 없습니다."


def run_stool_analysis_workflow(
    request: AnalyzeInfantStoolInput,
    *,
    validate_image: Callable[[str], ValidatedImage],
    assess_quality: Callable[[ValidatedImage], list[str]],
    observe_image: Callable[..., StoolObservation],
    evaluate_risk: Callable[
        [StoolObservation, AnalyzeInfantStoolInput],
        tuple[StoolRisk, list[str]],
    ],
    find_sources: Callable[
        [StoolObservation, AnalyzeInfantStoolInput], list[StoolSource]
    ],
    delete_image: Callable[[Path], None],
) -> StoolAnalysisToolResponse:
    """정해진 순서로 분석하며 정상 응답을 만든 뒤 임시 파일을 삭제합니다."""
    image = validate_image(request.image_path)
    quality_issues = assess_quality(image)
    if quality_issues:
        response = StoolAnalysisToolResponse(
            success=True,
            message="사진 품질이 충분하지 않아 다시 촬영이 필요합니다.",
            data=StoolAnalysisData(
                baby_id=request.baby_id,
                is_analyzable=False,
                quality_issues=quality_issues,
                observation=None,
                risk=None,
                follow_up_questions=[
                    "밝은 곳에서 기저귀 전체가 선명하게 보이도록 다시 촬영해 주세요."
                ],
                sources=[],
                warnings=[],
                safety_notice=SAFETY_NOTICE,
            ),
            error=None,
        )
        delete_image(image.path)
        return response

    observation = observe_image(image=image, request=request)
    risk, follow_up_questions = evaluate_risk(observation, request)
    warnings: list[ToolWarning] = []
    try:
        sources = find_sources(observation, request)
    except RagServiceError:
        sources = []
        warnings.append(
            ToolWarning(
                code="RAG_SERVICE_ERROR",
                detail="육아 참고자료를 조회하지 못했습니다.",
            )
        )

    response = StoolAnalysisToolResponse(
        success=True,
        message="기저귀 사진에서 관찰 가능한 특징을 정리했습니다.",
        data=StoolAnalysisData(
            baby_id=request.baby_id,
            is_analyzable=True,
            quality_issues=[],
            observation=observation,
            risk=risk,
            follow_up_questions=follow_up_questions,
            sources=sources,
            warnings=warnings,
            safety_notice=SAFETY_NOTICE,
        ),
        error=None,
    )
    delete_image(image.path)
    return response
