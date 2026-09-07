"""기저귀 이미지 입력 검증과 분석 준비 서비스입니다."""

import base64
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from ..config import settings
from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation


ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}
FORMAT_SUFFIXES = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
}


@dataclass(frozen=True)
class ValidatedImage:
    """검증을 통과하여 다음 분석 단계에 전달할 이미지 정보입니다."""

    path: Path
    image_format: str
    width: int
    height: int
    size_bytes: int


class ImageValidationError(Exception):
    """예상 가능한 이미지 입력 오류입니다."""

    def __init__(self, code: str, message: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.message = message
        self.detail = detail


class VisionAnalysisError(Exception):
    """Vision 관찰을 완료하지 못한 경우의 업무 오류입니다."""

    code = "VISION_API_ERROR"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.message = "이미지 관찰을 완료하지 못했습니다."
        self.detail = detail


def _resolve_image_path(image_path: str) -> Path:
    """입력 경로를 해석하고 허용된 임시 폴더 내부인지 확인합니다."""
    allowed_root = settings.image_temp_directory.resolve()
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = (allowed_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.is_relative_to(allowed_root):
        raise ImageValidationError(
            "INVALID_IMAGE_PATH",
            "허용되지 않은 이미지 경로입니다.",
            "이미지는 지정된 공용 임시 폴더 내부에 있어야 합니다.",
        )
    return candidate


def delete_temporary_image(path: Path) -> None:
    """정상 처리된 임시 이미지를 삭제하며 이미 없어도 성공으로 봅니다."""
    path.unlink(missing_ok=True)


def validate_stool_image(image_path: str) -> ValidatedImage:
    """경로·존재·확장자·크기·실제 이미지 형식을 순서대로 검사합니다."""
    path = _resolve_image_path(image_path)

    if not path.is_file():
        raise ImageValidationError(
            "IMAGE_NOT_FOUND",
            "이미지 파일을 찾을 수 없습니다.",
            "전달된 임시 이미지가 존재하지 않습니다.",
        )

    suffix = path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise ImageValidationError(
            "UNSUPPORTED_IMAGE_TYPE",
            "지원하지 않는 이미지 형식입니다.",
            "JPG, JPEG, PNG 이미지만 사용할 수 있습니다.",
        )

    size_bytes = path.stat().st_size
    if size_bytes > settings.image_max_bytes:
        raise ImageValidationError(
            "IMAGE_TOO_LARGE",
            "이미지 파일이 너무 큽니다.",
            f"이미지는 {settings.image_max_bytes}바이트 이하여야 합니다.",
        )

    try:
        with Image.open(path) as image:
            image_format = image.format or ""
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ImageValidationError(
            "UNSUPPORTED_IMAGE_TYPE",
            "올바른 이미지 파일이 아닙니다.",
            "파일 내용이 손상되었거나 지원하는 이미지 형식이 아닙니다.",
        ) from None

    if (
        image_format not in ALLOWED_IMAGE_FORMATS
        or suffix not in FORMAT_SUFFIXES[image_format]
    ):
        raise ImageValidationError(
            "UNSUPPORTED_IMAGE_TYPE",
            "이미지 확장자와 실제 형식이 일치하지 않습니다.",
            "JPG, JPEG, PNG 형식으로 다시 업로드해 주세요.",
        )

    return ValidatedImage(
        path=path,
        image_format=image_format,
        width=width,
        height=height,
        size_bytes=size_bytes,
    )


def assess_image_quality(image: ValidatedImage) -> list[str]:
    """해상도·밝기·선명도를 간단한 로컬 규칙으로 검사합니다."""
    issues: list[str] = []
    if image.width < settings.image_min_width or image.height < settings.image_min_height:
        issues.append(
            f"사진 해상도가 낮습니다. 최소 {settings.image_min_width}x{settings.image_min_height} 이상이 필요합니다."
        )

    with Image.open(image.path) as opened:
        grayscale = opened.convert("L")
        brightness = ImageStat.Stat(grayscale).mean[0]
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        if image.width > 2 and image.height > 2:
            edges = edges.crop((1, 1, image.width - 1, image.height - 1))
        edge_variance = ImageStat.Stat(edges).var[0]

    if brightness < settings.image_dark_threshold:
        issues.append("사진이 너무 어둡습니다.")
    elif brightness > settings.image_bright_threshold:
        issues.append("사진이 너무 밝습니다.")
    if edge_variance < settings.image_blur_threshold:
        issues.append("사진이 흐리거나 세부 형태가 충분히 보이지 않습니다.")
    return issues


def _image_data_url(image: ValidatedImage) -> str:
    mime_type = "image/jpeg" if image.image_format == "JPEG" else "image/png"
    encoded = base64.b64encode(image.path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _vision_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "stool_vision_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def observe_stool_image(
    *,
    image: ValidatedImage,
    request: AnalyzeInfantStoolInput,
    client=None,
) -> StoolObservation:
    """Responses API의 구조화 출력으로 사진에서 보이는 특징만 관찰합니다."""
    if not settings.openai_vision_model:
        raise VisionAnalysisError("OPENAI_VISION_MODEL이 설정되지 않았습니다.")
    if client is None:
        if not settings.openai_api_key:
            raise VisionAnalysisError("OPENAI_API_KEY가 설정되지 않았습니다.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

    context = (
        f"아기 월령: {request.baby_age_months}개월\n"
        f"수유 방식: {request.feeding_type}\n"
        f"발열 여부: {request.has_fever}\n"
        f"최근 24시간 배변 횟수: {request.stool_count_24h}"
    )
    try:
        response = client.responses.parse(
            model=settings.openai_vision_model,
            instructions=_vision_prompt(),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": context},
                        {
                            "type": "input_image",
                            "image_url": _image_data_url(image),
                            "detail": "high",
                        },
                    ],
                }
            ],
            text_format=StoolObservation,
            store=False,
        )
    except Exception as error:
        raise VisionAnalysisError("Vision API 호출에 실패했습니다.") from error

    observation = response.output_parsed
    if observation is None:
        raise VisionAnalysisError("Vision API가 관찰 결과를 반환하지 않았습니다.")
    return observation
