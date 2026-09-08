"""Pediatric hospital search MCP tool."""

from ..schemas.hospital import HospitalSearchInput
from ..services.hospital_service import search_pediatric


async def search_pediatric_hospitals(region: str, page: int = 1, limit: int = 10) -> dict:
    request = HospitalSearchInput(region=region.strip(), page=page, limit=limit)
    return await search_pediatric(request.region, request.page, request.limit)
