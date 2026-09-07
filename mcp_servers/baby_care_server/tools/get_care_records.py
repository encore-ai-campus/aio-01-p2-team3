"""육아 기록 조회 MCP Tool 함수입니다."""

from typing import Literal

from ..schemas.care import GetCareRecordsInput
from ..services.care_query_service import get_care_records as query_care_records


def get_care_records(
    baby_id: str,
    query_type: Literal["today", "range", "pattern", "latest_feeding"],
    days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """오늘·기간·패턴 또는 가장 최근 수유 기록을 조회합니다."""
    request = GetCareRecordsInput(
        baby_id=baby_id, query_type=query_type, days=days,
        start_date=start_date, end_date=end_date,
    )
    return query_care_records(request).model_dump(mode="json")
