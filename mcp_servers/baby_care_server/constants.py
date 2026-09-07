"""Backend와 합의한 허용값을 한곳에서 관리합니다."""

EVENT_TYPES = ("feeding", "sleep", "diaper", "growth")
INPUT_SOURCES = ("text", "ui", "stt")
FEEDING_TYPES = ("breast", "formula", "mixed")
SLEEP_ACTIONS = ("start", "end")
QUERY_TYPES = ("today", "range", "pattern", "latest_feeding")
RISK_LEVELS = ("none", "attention", "urgent", "emergency")

DEFAULT_PATTERN_DAYS = 7
MIN_PATTERN_DAYS = 1
MAX_PATTERN_DAYS = 30

MIN_SUFFICIENT_RECORDS = 5
MIN_SUFFICIENT_RECORDED_DAYS = 3
