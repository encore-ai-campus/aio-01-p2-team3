"""육아 기록 조회 업무 로직입니다."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..config import settings
from ..repositories import care_log_repository
from ..schemas.care import (
    CareRecord,
    CareRecordsData,
    CareRecordsToolResponse,
    GetCareRecordsInput,
)
from ..schemas.common import ToolError
from .pattern_service import calculate_pattern


def _failure(code: str, message: str, detail: str) -> CareRecordsToolResponse:
    return CareRecordsToolResponse(
        success=False,
        message=message,
        data=None,
        error=ToolError(code=code, detail=detail),
    )


def _day_start(value: date, timezone: ZoneInfo) -> datetime:
    """한국 날짜를 해당 날짜 자정의 timezone-aware datetime으로 변환합니다."""
    return datetime.combine(value, time.min, tzinfo=timezone)


def _to_record(row: dict) -> CareRecord:
    """Repository 조회 행을 외부 응답 Schema로 변환합니다."""
    return CareRecord(
        log_id=row["log_id"],
        baby_id=row["baby_id"],
        event_type=row["event_type"],
        recorded_at=row["recorded_at"],
        details=row["details"],
    )


def get_care_records(request: GetCareRecordsInput) -> CareRecordsToolResponse:
    """오늘·기간 기록 또는 가장 최근 수유 기록을 조회합니다."""
    if not care_log_repository.baby_exists(request.baby_id):
        return _failure(
            "BABY_NOT_FOUND",
            "아기 정보를 찾을 수 없습니다.",
            "baby_id에 해당하는 데이터가 없습니다.",
        )

    if request.query_type == "latest_feeding":
        row = care_log_repository.find_latest_feeding(request.baby_id)
        return CareRecordsToolResponse(
            success=True,
            message="최근 수유 기록을 조회했습니다.",
            data=CareRecordsData(
                baby_id=request.baby_id,
                query_type=request.query_type,
                records=[],
                pattern=None,
                latest_feeding=_to_record(row) if row is not None else None,
            ),
            error=None,
        )

    timezone = ZoneInfo(settings.app_timezone)
    if request.query_type == "pattern":
        end_date = datetime.now(timezone).date()
        start_date = end_date - timedelta(days=request.days - 1)
        rows = care_log_repository.find_records_by_date_range(
            baby_id=request.baby_id,
            start_at=_day_start(start_date, timezone),
            end_at=_day_start(end_date + timedelta(days=1), timezone),
        )
        pattern = calculate_pattern(
            rows=rows,
            period_days=request.days,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
        )
        return CareRecordsToolResponse(
            success=True,
            message="최근 육아 패턴을 계산했습니다.",
            data=CareRecordsData(
                baby_id=request.baby_id,
                query_type=request.query_type,
                records=[],
                pattern=pattern,
                latest_feeding=None,
            ),
            error=None,
        )

    if request.query_type == "today":
        start_date = datetime.now(timezone).date()
        end_date = start_date
    elif request.query_type == "range":
        # range 입력 필수값과 날짜 순서는 GetCareRecordsInput이 먼저 검증합니다.
        assert request.start_date is not None
        assert request.end_date is not None
        start_date = request.start_date
        end_date = request.end_date
    else:  # GetCareRecordsInput의 Literal 검증으로 실제 도달하지 않습니다.
        raise ValueError("지원하지 않는 query_type입니다.")

    rows = care_log_repository.find_records_by_date_range(
        baby_id=request.baby_id,
        start_at=_day_start(start_date, timezone),
        end_at=_day_start(end_date + timedelta(days=1), timezone),
    )
    return CareRecordsToolResponse(
        success=True,
        message="육아 기록을 조회했습니다.",
        data=CareRecordsData(
            baby_id=request.baby_id,
            query_type=request.query_type,
            records=[_to_record(row) for row in rows],
            pattern=None,
            latest_feeding=None,
        ),
        error=None,
    )
