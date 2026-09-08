from typing import Any

from pydantic import ValidationError

from config import get_hospital_service
from schemas.hospital import HospitalSearchRequest, ToolErrorResponse
from services.hospital_service import ExternalApiError, RateLimitError


async def run(region: str, page: int = 1, limit: int = 10) -> dict[str, Any]:
    try:
        request = HospitalSearchRequest(region=region, page=page, limit=limit)
        return await get_hospital_service().search("emergency", request.region, request.page, request.limit)
    except ValidationError:
        return ToolErrorResponse(message="지역명과 페이지 입력값을 확인해 주세요.", error_code="VALIDATION_ERROR").model_dump()
    except RateLimitError:
        return ToolErrorResponse(message="외부 서비스 호출 한도를 초과했습니다.", error_code="RATE_LIMIT_EXCEEDED").model_dump()
    except ExternalApiError:
        return ToolErrorResponse(message="공공데이터 API를 호출할 수 없습니다.", error_code="EXTERNAL_API_ERROR").model_dump()
