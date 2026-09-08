"""Emergency hospital search MCP tool."""

from ..schemas.hospital import HospitalSearchInput
from ..services.emergency_service import search_emergency


async def search_emergency_hospitals(region: str, page: int = 1, limit: int = 10) -> dict:
    request = HospitalSearchInput(region=region.strip(), page=page, limit=limit)
    return await search_emergency(request.region, request.page, request.limit)
