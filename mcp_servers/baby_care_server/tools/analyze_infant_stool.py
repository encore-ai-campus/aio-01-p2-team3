"""기저귀 변 사진 분석 MCP Tool 함수입니다."""

from typing import Literal

from ..schemas.stool import AnalyzeInfantStoolInput
from ..services.stool_analysis_service import (
    ImageValidationError,
    VisionAnalysisError,
    assess_image_quality,
    delete_temporary_image,
    observe_stool_image,
    validate_stool_image,
)
from ..services.triage_service import evaluate_stool_risk
from ..services.stool_rag_service import find_stool_sources
from ..workflows.stool_analysis_workflow import run_stool_analysis_workflow


def analyze_infant_stool(
    baby_id: str,
    image_path: str,
    baby_age_months: int,
    feeding_type: Literal["breast", "formula", "mixed"],
    has_fever: bool | None = None,
    stool_count_24h: int | None = None,
) -> dict:
    """이미지 품질을 검사하고 사진에서 직접 보이는 특징만 관찰합니다."""
    request = AnalyzeInfantStoolInput(
        baby_id=baby_id,
        image_path=image_path,
        baby_age_months=baby_age_months,
        feeding_type=feeding_type,
        has_fever=has_fever,
        stool_count_24h=stool_count_24h,
    )
    try:
        response = run_stool_analysis_workflow(
            request,
            validate_image=validate_stool_image,
            assess_quality=assess_image_quality,
            observe_image=observe_stool_image,
            evaluate_risk=evaluate_stool_risk,
            find_sources=find_stool_sources,
            delete_image=delete_temporary_image,
        )
        return response.model_dump(mode="json")
    except (ImageValidationError, VisionAnalysisError) as error:
        return {
            "success": False,
            "message": error.message,
            "data": None,
            "error": {"code": error.code, "detail": error.detail},
        }
