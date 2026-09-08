from typing import Final, Literal

KnowledgeCategory = Literal["feeding", "sleep", "weaning", "development", "safety"]
Confidence = Literal["high", "low"]
ErrorCode = Literal[
    "INVALID_REQUEST",
    "VALIDATION_ERROR",
    "EXTERNAL_API_ERROR",
    "RAG_SERVICE_UNAVAILABLE",
    "ANSWER_GENERATION_FAILED",
    "RATE_LIMIT_EXCEEDED",
]

CATEGORY_BY_TOOL: Final[dict[str, KnowledgeCategory]] = {
    "search_feeding_guide": "feeding",
    "search_sleep_guide": "sleep",
    "search_weaning_guide": "weaning",
    "search_development_guide": "development",
    "search_safety_guide": "safety",
}

EMERGENCY_TERMS: Final[tuple[str, ...]] = (
    "숨을 안", "호흡 곤란", "의식이 없", "경련", "청색증", "심한 출혈", "119"
)

