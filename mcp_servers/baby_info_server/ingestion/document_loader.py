import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pypdf import PdfReader


ALLOWED_CATEGORIES = {
    "feeding",
    "sleep",
    "weaning",
    "development",
    "safety",
    "stool",
}


def _validate_metadata(metadata: dict[str, Any]) -> None:
    required = {"title", "organization", "source_url", "category"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"필수 메타데이터 누락: {', '.join(sorted(missing))}")
    if metadata["category"] not in ALLOWED_CATEGORIES:
        raise ValueError("지원하지 않는 RAG 카테고리입니다.")

    for key in ("title", "organization", "source_url"):
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise ValueError(f"{key}는 비어 있지 않은 문자열이어야 합니다.")

    source_url = urlparse(metadata["source_url"])
    if source_url.scheme not in {"http", "https"} or not source_url.netloc:
        raise ValueError("source_url은 http 또는 https URL이어야 합니다.")

    for key in ("published_at", "verified_at"):
        value = metadata.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{key}은 YYYY-MM-DD 형식이어야 합니다.")
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"{key}은 YYYY-MM-DD 형식이어야 합니다.") from exc

    age_min = metadata.get("age_min_months")
    age_max = metadata.get("age_max_months")
    for value in (age_min, age_max):
        if value is not None and (not isinstance(value, int) or not 0 <= value <= 36):
            raise ValueError("월령 범위는 0~36개월 정수여야 합니다.")
    if age_min is not None and age_max is not None and age_min > age_max:
        raise ValueError("최소 월령은 최대 월령보다 클 수 없습니다.")

    pages = metadata.get("pages")
    if pages is not None and (
        not isinstance(pages, list)
        or not pages
        or any(not isinstance(page, int) or page < 1 for page in pages)
    ):
        raise ValueError("PDF pages는 1 이상의 페이지 번호 목록이어야 합니다.")


def _build_document(content: str, metadata: dict[str, Any]) -> dict[str, Any]:
    content = content.strip()
    if not content:
        raise ValueError("빈 문서는 색인할 수 없습니다.")
    _validate_metadata(metadata)
    return {
        **metadata,
        "content": content,
        "checksum": hashlib.sha256(content.encode()).hexdigest(),
    }


def load_text(path: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
    source = Path(path)
    return _build_document(source.read_text(encoding="utf-8"), metadata)


def load_pdf(path: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
    source = Path(path)
    reader = PdfReader(str(source))
    pages = metadata.get("pages")
    if pages is None:
        selected = range(len(reader.pages))
    else:
        selected = (page_number - 1 for page_number in pages)

    extracted: list[str] = []
    for page_index in selected:
        if page_index < 0 or page_index >= len(reader.pages):
            raise ValueError(f"PDF 페이지 범위 오류: {page_index + 1}")
        text = reader.pages[page_index].extract_text() or ""
        text = text.replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        if text.strip():
            extracted.append(text.strip())

    clean_metadata = {key: value for key, value in metadata.items() if key != "pages"}
    return _build_document("\n\n".join(extracted), clean_metadata)


def load_document(path: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
    source = Path(path)
    if source.suffix.casefold() == ".pdf":
        return load_pdf(source, metadata)
    return load_text(source, metadata)
