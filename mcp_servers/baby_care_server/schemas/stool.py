"""기저귀 사진 분석 입력과 응답 Schema입니다."""

from typing import Literal

from pydantic import Field

from .common import StrictBaseModel, ToolError, ToolWarning


class AnalyzeInfantStoolInput(StrictBaseModel):
    baby_id: str = Field(min_length=1, max_length=100)
    image_path: str = Field(min_length=1, max_length=500)
    baby_age_months: int = Field(ge=0, le=36)
    feeding_type: Literal["breast", "formula", "mixed"]
    has_fever: bool | None = None
    stool_count_24h: int | None = Field(default=None, ge=0)


class StoolObservation(StrictBaseModel):
    color: str
    consistency: str
    visible_red_area: bool
    black_tarry_appearance: bool
    pale_or_white_appearance: bool
    uncertainty: Literal["low", "medium", "high"]
    notes: list[str] = Field(default_factory=list)


class StoolRisk(StrictBaseModel):
    level: Literal["none", "attention", "urgent", "emergency"]
    signals: list[str] = Field(default_factory=list)
    recommended_action: str


class StoolSource(StrictBaseModel):
    document_id: str
    title: str
    organization: str
    source_url: str
    score: float = Field(ge=0, le=1)


class StoolAnalysisData(StrictBaseModel):
    baby_id: str
    is_analyzable: bool
    quality_issues: list[str] = Field(default_factory=list)
    observation: StoolObservation | None = None
    risk: StoolRisk | None = None
    follow_up_questions: list[str] = Field(default_factory=list)
    sources: list[StoolSource] = Field(default_factory=list)
    warnings: list[ToolWarning] = Field(default_factory=list)
    safety_notice: str


class StoolAnalysisToolResponse(StrictBaseModel):
    success: bool
    message: str
    data: StoolAnalysisData | None = None
    error: ToolError | None = None
