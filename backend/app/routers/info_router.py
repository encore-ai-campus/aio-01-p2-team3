"""Hospital search routes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.schemas.info import HospitalSearchResponse
from app.services.info.hospital_service import search_hospitals


router = APIRouter(prefix="/api", tags=["병원 검색"])


@router.get("/hospitals/search")
async def search_hospitals_api(
    region: str = Query(min_length=2, max_length=100),
    type: str = Query(pattern="^(pediatric|emergency)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=30),
) -> dict:
    try:
        data = await search_hospitals(type, region.strip(), page, limit)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="병원 검색 서비스에 연결할 수 없습니다.") from exc
    return {"success": True, "message": "병원 검색 결과를 조회했습니다.", "data": HospitalSearchResponse.model_validate(data), "request_id": str(uuid4())}
