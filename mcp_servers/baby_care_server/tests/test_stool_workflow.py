"""기저귀 분석 Workflow의 순서와 장애 격리 정책 테스트입니다."""

from pathlib import Path

import pytest

from ..schemas.stool import (
    AnalyzeInfantStoolInput,
    StoolObservation,
    StoolRisk,
    StoolSource,
)
from ..services.embedding_service import RagServiceError
from ..services.stool_analysis_service import ValidatedImage, VisionAnalysisError
from ..workflows.stool_analysis_workflow import run_stool_analysis_workflow


def make_request() -> AnalyzeInfantStoolInput:
    return AnalyzeInfantStoolInput(
        baby_id="baby-001",
        image_path="temporary/test.jpg",
        baby_age_months=3,
        feeding_type="formula",
    )


def make_image() -> ValidatedImage:
    return ValidatedImage(
        path=Path("temporary/test.jpg"),
        image_format="JPEG",
        width=320,
        height=320,
        size_bytes=1024,
    )


def make_observation() -> StoolObservation:
    return StoolObservation(
        color="yellow",
        consistency="soft",
        visible_red_area=False,
        black_tarry_appearance=False,
        pale_or_white_appearance=False,
        uncertainty="low",
        notes=[],
    )


def make_risk() -> StoolRisk:
    return StoolRisk(
        level="none",
        signals=[],
        recommended_action="다음 배변을 관찰하세요.",
    )


def test_workflow_runs_steps_in_fixed_order() -> None:
    calls: list[str] = []
    image = make_image()
    observation = make_observation()
    source = StoolSource(
        document_id="doc-001",
        title="배변 안내",
        organization="공식기관",
        source_url="https://example.org",
        score=0.9,
    )

    def validate(path):
        calls.append("validate")
        return image

    def quality(value):
        calls.append("quality")
        return []

    def observe(**kwargs):
        calls.append("vision")
        return observation

    def triage(value, request):
        calls.append("triage")
        return make_risk(), []

    def rag(value, request):
        calls.append("rag")
        return [source]

    def delete(path):
        calls.append("delete")

    response = run_stool_analysis_workflow(
        make_request(),
        validate_image=validate,
        assess_quality=quality,
        observe_image=observe,
        evaluate_risk=triage,
        find_sources=rag,
        delete_image=delete,
    )

    assert calls == ["validate", "quality", "vision", "triage", "rag", "delete"]
    assert response.data is not None
    assert response.data.sources == [source]


def test_quality_failure_stops_expensive_steps_and_deletes_image() -> None:
    calls: list[str] = []
    image = make_image()

    def must_not_run(*args, **kwargs):
        raise AssertionError("품질 실패 뒤 단계가 실행되었습니다.")

    response = run_stool_analysis_workflow(
        make_request(),
        validate_image=lambda path: image,
        assess_quality=lambda value: ["사진이 흐립니다."],
        observe_image=must_not_run,
        evaluate_risk=must_not_run,
        find_sources=must_not_run,
        delete_image=lambda path: calls.append("delete"),
    )

    assert response.success is True
    assert response.data is not None
    assert response.data.is_analyzable is False
    assert calls == ["delete"]


def test_vision_failure_does_not_delete_image() -> None:
    image = make_image()
    calls: list[str] = []

    def vision_failure(**kwargs):
        raise VisionAnalysisError("test")

    with pytest.raises(VisionAnalysisError):
        run_stool_analysis_workflow(
            make_request(),
            validate_image=lambda path: image,
            assess_quality=lambda value: [],
            observe_image=vision_failure,
            evaluate_risk=lambda value, request: (make_risk(), []),
            find_sources=lambda value, request: [],
            delete_image=lambda path: calls.append("delete"),
        )

    assert calls == []


def test_empty_rag_result_is_normal_success() -> None:
    image = make_image()
    response = run_stool_analysis_workflow(
        make_request(),
        validate_image=lambda path: image,
        assess_quality=lambda value: [],
        observe_image=lambda **kwargs: make_observation(),
        evaluate_risk=lambda value, request: (make_risk(), []),
        find_sources=lambda value, request: [],
        delete_image=lambda path: None,
    )

    assert response.success is True
    assert response.data is not None
    assert response.data.sources == []
    assert response.data.warnings == []


def test_rag_failure_keeps_observation_and_adds_warning() -> None:
    image = make_image()

    def rag_failure(value, request):
        raise RagServiceError("test")

    response = run_stool_analysis_workflow(
        make_request(),
        validate_image=lambda path: image,
        assess_quality=lambda value: [],
        observe_image=lambda **kwargs: make_observation(),
        evaluate_risk=lambda value, request: (make_risk(), []),
        find_sources=rag_failure,
        delete_image=lambda path: None,
    )

    assert response.success is True
    assert response.data is not None
    assert response.data.observation is not None
    assert response.data.sources == []
    assert response.data.warnings[0].code == "RAG_SERVICE_ERROR"
