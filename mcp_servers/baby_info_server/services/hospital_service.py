"""Public-data pediatric hospital adapter.

The public provider URL is configured rather than embedded: providers differ by
deployment/account, but all must accept ``region``, ``page`` and ``limit`` and
return JSON.  The adapter normalizes common Korean public-data field names.
"""

from datetime import datetime, timezone

import httpx

from ..config import settings

PEDIATRIC_NOTICE = "운영시간과 진료 가능 여부는 방문 전 의료기관에 확인해 주세요."


async def search_pediatric(region: str, page: int, limit: int) -> dict:
    rows = await _request_public_data(settings.pediatric_api_url, settings.pediatric_api_key, region, page, limit)
    data = []
    for row in rows:
        name, address = _value(row, "hospital_name", "yadmNm", "dutyName", "name"), _value(row, "address", "addr", "dutyAddr")
        if not name or not address:
            continue
        data.append({"hospital_name": name, "address": address, "phone": _nullable(_value(row, "phone", "telno", "dutyTel1")), "operating_hours": _nullable(_value(row, "operating_hours", "hours", "dutyTime1s"))})
    return {"success": True, "region": region, "data": data, "source": "public_data", "checked_at": datetime.now(timezone.utc).isoformat(), "notice": PEDIATRIC_NOTICE}


async def _request_public_data(url: str, api_key: str, region: str, page: int, limit: int) -> list[dict]:
    if not url or not api_key:
        raise RuntimeError("병원 공공데이터 API 설정이 없습니다.")
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_seconds) as client:
            response = await client.get(url, params={"serviceKey": api_key, "region": region, "page": page, "limit": limit, "pageNo": page, "numOfRows": limit, "_type": "json"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("병원 공공데이터를 조회할 수 없습니다.") from exc
    return _extract_rows(payload)


def _extract_rows(payload: object) -> list[dict]:
    if isinstance(payload, list): return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict): return []
    body = payload.get("response", {}).get("body", payload.get("body", payload))
    items = body.get("items", body.get("data", body.get("results", []))) if isinstance(body, dict) else []
    if isinstance(items, dict): items = items.get("item", items.get("items", []))
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _value(row: dict, *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip(): return str(value).strip()
    return None


def _nullable(value: str | None) -> str | None: return value or None
