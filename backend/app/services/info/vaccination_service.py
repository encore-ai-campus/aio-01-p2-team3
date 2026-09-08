"""예방접종 목데이터를 아기의 월령에 맞춰 조회합니다."""

import json
from datetime import date, timedelta
from pathlib import Path

from app.models.baby import Baby


VACCINATION_DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "vaccinations.json"


def get_vaccinations(baby: Baby) -> dict:
    """실제 접종 이력이 아닌, 시연용 권장 일정만 반환합니다."""
    try:
        schedule = json.loads(VACCINATION_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("예방접종 목데이터를 읽을 수 없습니다.") from error

    if not isinstance(schedule, list):
        raise RuntimeError("예방접종 목데이터 형식이 올바르지 않습니다.")

    age_months = max(0, (date.today() - baby.birth_date).days // 30)
    items = []
    for item in schedule:
        recommended_month = item["recommended_month"]
        scheduled_date = baby.birth_date + timedelta(days=recommended_month * 30)
        items.append(
            {
                "name": item["name"],
                "dose": item["dose"],
                "recommended_month": recommended_month,
                "scheduled_date": scheduled_date.isoformat(),
                "status": "completed_mock" if recommended_month < age_months else "upcoming",
            }
        )

    next_item = next((item for item in items if item["status"] == "upcoming"), None)
    return {
        "baby_id": baby.id,
        "age_months": age_months,
        "completed": [item for item in items if item["status"] == "completed_mock"],
        "next": next_item,
        "items": items,
        "notice": "예방접종 정보는 실제 접종 이력이 아닌 테스트용 목데이터입니다.",
    }
