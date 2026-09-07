"""Care MCP를 이용한 육아 기록 업무를 처리합니다."""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_clients.baby_care_client import (
    get_care_records as get_care_records_from_mcp,
    record_care_event,
)
from app.schemas.care import CareLogCreateRequest, CareRecordsQuery
from app.services.baby_service import get_baby


def get_mcp_data(result: dict) -> dict:
    """Care MCP 성공 응답에서 실제 data 값을 추출합니다."""
    if not result.get("success"):
        raise ValueError(result.get("message", "Care MCP 요청에 실패했습니다."))

    data = result.get("data")

    if not isinstance(data, dict):
        raise RuntimeError("Care MCP 응답 형식이 올바르지 않습니다.")

    return data


async def create_care_log(
    session: AsyncSession,
    user_id: str,
    care_request: CareLogCreateRequest,
) -> dict:
    """소유권을 확인한 뒤 육아 기록을 Care MCP에 저장합니다."""
    await get_baby(session, user_id, care_request.baby_id)

    # STT 기록은 사용자가 승인한 경우에만 Care MCP로 전달합니다.
    if care_request.input_source == "stt" and not care_request.confirmed_by_user:
        raise ValueError("STT 기록은 사용자 승인 후 저장할 수 있습니다.")

    # 모든 기록 유형에 공통으로 필요한 값입니다.
    arguments = {
        "baby_id": care_request.baby_id,
        "event_type": care_request.event_type,
        "input_source": care_request.input_source,
        "idempotency_key": care_request.idempotency_key,
    }

    if care_request.recorded_at is not None:
        arguments["recorded_at"] = care_request.recorded_at.isoformat()

    if care_request.input_source == "stt":
        arguments["confirmed_by_user"] = True

    # MCP Tool에는 현재 기록 유형에 필요한 필드만 전달합니다.
    if care_request.event_type == "feeding":
        arguments["feeding_type"] = care_request.feeding_type

        if care_request.amount_ml is not None:
            arguments["amount_ml"] = care_request.amount_ml

    if care_request.event_type == "sleep":
        arguments["action"] = care_request.action

    if care_request.event_type == "diaper":
        arguments["urine"] = care_request.urine
        arguments["stool"] = care_request.stool

        if care_request.color is not None:
            arguments["color"] = care_request.color

        if care_request.consistency is not None:
            arguments["consistency"] = care_request.consistency

        if care_request.note is not None:
            arguments["note"] = care_request.note

    if care_request.event_type == "growth":
        if care_request.weight_kg is not None:
            arguments["weight_kg"] = care_request.weight_kg

        if care_request.height_cm is not None:
            arguments["height_cm"] = care_request.height_cm

        if care_request.head_circumference_cm is not None:
            arguments["head_circumference_cm"] = care_request.head_circumference_cm

    result = await record_care_event(arguments)

    return get_mcp_data(result)


async def get_care_logs(
    session: AsyncSession,
    user_id: str,
    query: CareRecordsQuery,
) -> dict:
    """소유권을 확인한 뒤 육아 기록을 조회합니다."""
    await get_baby(session, user_id, query.baby_id)

    arguments = {
        "baby_id": query.baby_id,
        "query_type": query.query_type,
    }

    if query.start_date is not None:
        arguments["start_date"] = query.start_date.isoformat()

    if query.end_date is not None:
        arguments["end_date"] = query.end_date.isoformat()

    if query.query_type == "pattern":
        arguments["days"] = query.days

    result = await get_care_records_from_mcp(arguments)

    return get_mcp_data(result)


async def get_care_pattern(
    session: AsyncSession,
    user_id: str,
    baby_id: str,
    days: int,
) -> dict:
    """소유권을 확인한 뒤 최근 생활 패턴을 조회합니다."""
    await get_baby(session, user_id, baby_id)

    result = await get_care_records_from_mcp(
        {
            "baby_id": baby_id,
            "query_type": "pattern",
            "days": days,
        }
    )

    return get_mcp_data(result)
