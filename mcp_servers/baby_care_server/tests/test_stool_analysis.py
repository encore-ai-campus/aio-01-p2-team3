"""기저귀 이미지 입력 보안 검증 테스트입니다."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from ..config import settings
from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation, StoolSource
from ..services.embedding_service import RagServiceError
from ..services.stool_analysis_service import (
    ImageValidationError,
    VisionAnalysisError,
    assess_image_quality,
    observe_stool_image,
    validate_stool_image,
)
from ..services.triage_service import evaluate_stool_risk
from ..tools import analyze_infant_stool as stool_tool_module
from ..tools.analyze_infant_stool import analyze_infant_stool


@pytest.fixture
def image_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "shared-images"
    directory.mkdir()
    monkeypatch.setattr(settings, "image_temp_directory", directory)
    return directory


def make_image(path: Path, image_format: str = "PNG") -> Path:
    Image.new("RGB", (32, 24), color=(245, 210, 80)).save(
        path, format=image_format
    )
    return path


def make_sharp_image(path: Path) -> Path:
    image = Image.new("RGB", (320, 320), color=(220, 190, 80))
    draw = ImageDraw.Draw(image)
    for position in range(0, 320, 20):
        draw.line((position, 0, position, 319), fill=(40, 30, 20), width=4)
        draw.line((0, position, 319, position), fill=(250, 245, 220), width=4)
    image.save(path, format="PNG")
    return path


def assert_validation_error(path: str, expected_code: str) -> None:
    with pytest.raises(ImageValidationError) as captured:
        validate_stool_image(path)
    assert captured.value.code == expected_code


def test_rejects_path_outside_allowed_directory(
    image_directory: Path, tmp_path: Path
) -> None:
    outside = make_image(tmp_path / "outside.png")
    assert_validation_error(str(outside), "INVALID_IMAGE_PATH")


def test_rejects_relative_path_traversal(
    image_directory: Path, tmp_path: Path
) -> None:
    outside = make_image(tmp_path / "outside-relative.png")
    relative_escape = f"../{outside.name}"

    assert_validation_error(relative_escape, "INVALID_IMAGE_PATH")


def test_rejects_missing_image_inside_allowed_directory(
    image_directory: Path,
) -> None:
    assert_validation_error(
        str(image_directory / "missing.png"),
        "IMAGE_NOT_FOUND",
    )


def test_rejects_unsupported_extension(image_directory: Path) -> None:
    unsupported = image_directory / "stool.gif"
    unsupported.write_bytes(b"GIF89a")
    assert_validation_error(str(unsupported), "UNSUPPORTED_IMAGE_TYPE")


def test_rejects_oversized_image(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = make_image(image_directory / "large.png")
    monkeypatch.setattr(settings, "image_max_bytes", image.stat().st_size - 1)
    assert_validation_error(str(image), "IMAGE_TOO_LARGE")


def test_rejects_fake_image_with_allowed_extension(image_directory: Path) -> None:
    fake = image_directory / "fake.jpg"
    fake.write_text("not an image", encoding="utf-8")
    assert_validation_error(str(fake), "UNSUPPORTED_IMAGE_TYPE")


def test_rejects_mismatched_extension_and_content(image_directory: Path) -> None:
    mismatch = make_image(image_directory / "mismatch.jpg", image_format="PNG")
    assert_validation_error(str(mismatch), "UNSUPPORTED_IMAGE_TYPE")


@pytest.mark.parametrize(
    ("filename", "image_format"),
    [("valid.png", "PNG"), ("valid.jpg", "JPEG"), ("valid.jpeg", "JPEG")],
)
def test_accepts_real_supported_images(
    image_directory: Path, filename: str, image_format: str
) -> None:
    path = make_image(image_directory / filename, image_format=image_format)
    result = validate_stool_image(str(path))

    assert result.path == path.resolve()
    assert result.image_format == image_format
    assert result.width == 32
    assert result.height == 24
    assert result.size_bytes == path.stat().st_size


def test_resolves_relative_path_from_shared_upload_root(image_directory: Path) -> None:
    temporary = image_directory / "temporary"
    temporary.mkdir()
    path = make_image(temporary / "relative.png")

    result = validate_stool_image("temporary/relative.png")

    assert result.path == path.resolve()


def test_tool_returns_common_error_response(image_directory: Path) -> None:
    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(image_directory / "missing.png"),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response == {
        "success": False,
        "message": "이미지 파일을 찾을 수 없습니다.",
        "data": None,
        "error": {
            "code": "IMAGE_NOT_FOUND",
            "detail": "전달된 임시 이미지가 존재하지 않습니다.",
        },
    }


def test_quality_check_reports_small_and_blurry_image(image_directory: Path) -> None:
    path = make_image(image_directory / "valid.png")
    image = validate_stool_image(str(path))
    issues = assess_image_quality(image)

    assert any("해상도" in issue for issue in issues)
    assert any("흐리거나" in issue for issue in issues)


def test_tool_returns_success_with_unanalyzable_quality(image_directory: Path) -> None:
    path = make_image(image_directory / "small.png")
    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response["success"] is True
    assert response["data"]["is_analyzable"] is False
    assert response["data"]["observation"] is None
    assert response["error"] is None
    assert not path.exists()


def test_tool_returns_structured_vision_observation(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_sharp_image(image_directory / "sharp.png")
    expected = StoolObservation(
        color="yellow",
        consistency="loose",
        visible_red_area=False,
        black_tarry_appearance=False,
        pale_or_white_appearance=False,
        uncertainty="medium",
        notes=["조명에 따라 색상이 다르게 보일 수 있습니다."],
    )
    monkeypatch.setattr(
        stool_tool_module,
        "observe_stool_image",
        lambda **kwargs: expected,
    )
    monkeypatch.setattr(stool_tool_module, "find_stool_sources", lambda *args: [])

    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response["success"] is True
    assert response["data"]["is_analyzable"] is True
    assert response["data"]["observation"]["color"] == "yellow"
    assert response["data"]["risk"]["level"] == "none"
    assert len(response["data"]["follow_up_questions"]) == 2
    assert response["data"]["safety_notice"] == "사진만으로 질환을 진단할 수 없습니다."
    assert not path.exists()


def test_tool_returns_rag_sources(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_sharp_image(image_directory / "rag-source.png")
    observation = make_observation()
    source = StoolSource(
        document_id="doc-001",
        title="영아 배변 안내",
        organization="공식기관",
        source_url="https://example.org/stool",
        score=0.91,
    )
    monkeypatch.setattr(stool_tool_module, "observe_stool_image", lambda **kwargs: observation)
    monkeypatch.setattr(stool_tool_module, "find_stool_sources", lambda *args: [source])

    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response["success"] is True
    assert response["data"]["sources"][0]["document_id"] == "doc-001"
    assert response["data"]["warnings"] == []


def test_tool_keeps_analysis_when_rag_fails(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_sharp_image(image_directory / "rag-error.png")
    monkeypatch.setattr(stool_tool_module, "observe_stool_image", lambda **kwargs: make_observation())

    def raise_rag_error(*args):
        raise RagServiceError("test")

    monkeypatch.setattr(stool_tool_module, "find_stool_sources", raise_rag_error)
    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response["success"] is True
    assert response["data"]["observation"] is not None
    assert response["data"]["sources"] == []
    assert response["data"]["warnings"][0]["code"] == "RAG_SERVICE_ERROR"
    assert not path.exists()


def test_tool_returns_vision_api_error(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_sharp_image(image_directory / "vision-error.png")

    def raise_vision_error(**kwargs):
        raise VisionAnalysisError("Vision API 호출에 실패했습니다.")

    monkeypatch.setattr(
        stool_tool_module,
        "observe_stool_image",
        raise_vision_error,
    )
    response = analyze_infant_stool(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )

    assert response["success"] is False
    assert response["error"]["code"] == "VISION_API_ERROR"
    assert path.exists()


def test_responses_api_request_uses_image_and_structured_output(
    image_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_sharp_image(image_directory / "api-input.png")
    image = validate_stool_image(str(path))
    request = AnalyzeInfantStoolInput(
        baby_id="baby-001",
        image_path=str(path),
        baby_age_months=3,
        feeding_type="formula",
    )
    expected = StoolObservation(
        color="yellow",
        consistency="soft",
        visible_red_area=False,
        black_tarry_appearance=False,
        pale_or_white_appearance=False,
        uncertainty="low",
        notes=[],
    )
    captured = {}

    class FakeResponses:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_parsed=expected)

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(settings, "openai_vision_model", "test-vision-model")

    result = observe_stool_image(
        image=image,
        request=request,
        client=fake_client,
    )

    assert result == expected
    assert captured["model"] == "test-vision-model"
    assert captured["text_format"] is StoolObservation
    assert captured["store"] is False
    image_input = captured["input"][0]["content"][1]
    assert image_input["type"] == "input_image"
    assert image_input["image_url"].startswith("data:image/png;base64,")


def make_observation(**changes) -> StoolObservation:
    values = {
        "color": "yellow",
        "consistency": "soft",
        "visible_red_area": False,
        "black_tarry_appearance": False,
        "pale_or_white_appearance": False,
        "uncertainty": "low",
        "notes": [],
    }
    values.update(changes)
    return StoolObservation(**values)


def make_request(**changes) -> AnalyzeInfantStoolInput:
    values = {
        "baby_id": "baby-001",
        "image_path": "unused.png",
        "baby_age_months": 3,
        "feeding_type": "formula",
        "has_fever": False,
        "stool_count_24h": 2,
    }
    values.update(changes)
    return AnalyzeInfantStoolInput(**values)


def test_triage_returns_none_without_predefined_signal() -> None:
    risk, questions = evaluate_stool_risk(make_observation(), make_request())

    assert risk.level == "none"
    assert risk.signals == []
    assert questions == []


@pytest.mark.parametrize(
    "signal_field",
    ["visible_red_area", "black_tarry_appearance", "pale_or_white_appearance"],
)
def test_triage_marks_visible_color_signals_as_urgent(signal_field: str) -> None:
    risk, questions = evaluate_stool_risk(
        make_observation(**{signal_field: True}),
        make_request(),
    )

    assert risk.level == "urgent"
    assert risk.signals
    assert questions


@pytest.mark.parametrize(
    ("observation_changes", "request_changes"),
    [
        ({"uncertainty": "high"}, {}),
        ({}, {"has_fever": True}),
        ({}, {"stool_count_24h": 8}),
    ],
)
def test_triage_marks_context_signals_as_attention(
    observation_changes: dict,
    request_changes: dict,
) -> None:
    risk, questions = evaluate_stool_risk(
        make_observation(**observation_changes),
        make_request(**request_changes),
    )

    assert risk.level == "attention"
    assert questions


def test_triage_uses_highest_matched_level() -> None:
    risk, _ = evaluate_stool_risk(
        make_observation(visible_red_area=True),
        make_request(has_fever=True, stool_count_24h=9),
    )

    assert risk.level == "urgent"
    assert len(risk.signals) == 3


def test_triage_asks_for_missing_context() -> None:
    risk, questions = evaluate_stool_risk(
        make_observation(),
        make_request(has_fever=None, stool_count_24h=None),
    )

    assert risk.level == "none"
    assert any("체온" in question for question in questions)
    assert any("24시간" in question for question in questions)


def test_triage_marks_fever_under_three_months_as_urgent() -> None:
    risk, questions = evaluate_stool_risk(
        make_observation(),
        make_request(baby_age_months=2, has_fever=True),
    )

    assert risk.level == "urgent"
    assert any("체온" in question for question in questions)


def test_newborn_black_stool_asks_about_meconium_period() -> None:
    risk, questions = evaluate_stool_risk(
        make_observation(black_tarry_appearance=True),
        make_request(baby_age_months=0),
    )

    assert risk.level == "urgent"
    assert any("태변" in question for question in questions)
