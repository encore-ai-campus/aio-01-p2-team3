"""Public-data emergency hospital adapter."""

from datetime import datetime, timezone

from ..config import settings
from .hospital_service import _nullable, _request_public_data, _value

EMERGENCY_NOTICE = "실시간 진료 가능 여부는 의료기관에 확인하고 위급한 경우 119에 연락하세요."


async def search_emergency(region: str, page: int, limit: int) -> dict:
    rows = await _request_public_data(settings.emergency_api_url, settings.emergency_api_key, region, page, limit)
    data = []
    for row in rows:
        name, address = _value(row, "hospital_name", "dutyName", "yadmNm", "name"), _value(row, "address", "dutyAddr", "addr")
        if not name or not address:
            continue
        data.append({"hospital_name": name, "address": address, "phone": _nullable(_value(row, "phone", "dutyTel1", "telno")), "emergency_level": _nullable(_value(row, "emergency_level", "emergencyLevel", "hpid"))})
    return {"success": True, "region": region, "data": data, "source": "public_data", "checked_at": datetime.now(timezone.utc).isoformat(), "notice": EMERGENCY_NOTICE}
