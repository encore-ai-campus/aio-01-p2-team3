def chunk_text(text: str, target_chars: int = 1600, overlap_chars: int = 240) -> list[str]:
    """문단 경계를 우선 보존하는 간단한 초기 Chunker입니다."""
    if target_chars <= overlap_chars or overlap_chars < 0:
        raise ValueError("target_chars는 overlap_chars보다 커야 합니다.")
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > target_chars:
            chunks.append(current)
            current = f"{current[-overlap_chars:]}\n\n{paragraph}".strip() if overlap_chars else paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks

