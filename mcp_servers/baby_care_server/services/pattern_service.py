"""최근 육아 기록의 간단한 생활 패턴 계산 로직입니다."""

from datetime import date
from zoneinfo import ZoneInfo

from ..schemas.care import CarePattern, DiaperPattern, FeedingPattern, SleepPattern


def _average(values: list[float]) -> float | None:
    """값이 있을 때만 소수점 첫째 자리 평균을 반환합니다."""
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def calculate_pattern(
    *,
    rows: list[dict],
    period_days: int,
    start_date: date,
    end_date: date,
    timezone: ZoneInfo,
) -> CarePattern:
    """조회된 기록으로 수유·수면·기저귀 패턴을 계산합니다."""
    recorded_dates = {
        row["recorded_at"].astimezone(timezone).date() for row in rows
    }
    record_count = len(rows)
    recorded_day_count = len(recorded_dates)
    sufficient_data = record_count >= 5 and recorded_day_count >= 3
    insufficient_reason = None
    if not sufficient_data:
        insufficient_reason = (
            "패턴 분석에는 전체 기록 5건 이상과 서로 다른 날짜 3일 이상의 기록이 필요합니다. "
            f"현재 {record_count}건, {recorded_day_count}일입니다."
        )

    feeding_rows = [row for row in rows if row["event_type"] == "feeding"]
    feeding_amounts = [
        float(row["details"]["amount_ml"])
        for row in feeding_rows
        if row["details"].get("amount_ml") is not None
    ]
    feeding_intervals = [
        (current["recorded_at"] - previous["recorded_at"]).total_seconds() / 60
        for previous, current in zip(feeding_rows, feeding_rows[1:])
    ]

    sleep_durations: list[float] = []
    open_sleep_at = None
    for row in rows:
        if row["event_type"] != "sleep":
            continue
        action = row["details"].get("action")
        if action == "start":
            open_sleep_at = row["recorded_at"]
        elif action == "end" and open_sleep_at is not None:
            duration = (row["recorded_at"] - open_sleep_at).total_seconds() / 60
            if duration >= 0:
                sleep_durations.append(duration)
            open_sleep_at = None

    diaper_rows = [row for row in rows if row["event_type"] == "diaper"]

    return CarePattern(
        period_days=period_days,
        start_date=start_date,
        end_date=end_date,
        record_count=record_count,
        recorded_day_count=recorded_day_count,
        sufficient_data=sufficient_data,
        insufficient_reason=insufficient_reason,
        feeding=FeedingPattern(
            count=len(feeding_rows),
            average_amount_ml=_average(feeding_amounts),
            average_interval_minutes=_average(feeding_intervals),
        ),
        sleep=SleepPattern(
            completed_session_count=len(sleep_durations),
            total_sleep_minutes=round(sum(sleep_durations)) if sleep_durations else None,
            average_sleep_minutes=_average(sleep_durations),
        ),
        diaper=DiaperPattern(
            urine_count=sum(row["details"].get("urine") is True for row in diaper_rows),
            stool_count=sum(row["details"].get("stool") is True for row in diaper_rows),
        ),
    )
