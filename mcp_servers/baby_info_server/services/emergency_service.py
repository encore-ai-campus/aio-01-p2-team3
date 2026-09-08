from services.hospital_service import HospitalService


class EmergencyService:
    def __init__(self, hospital_service: HospitalService) -> None:
        self.hospital_service = hospital_service

    async def search(self, region: str, page: int, limit: int):
        return await self.hospital_service.search("emergency", region, page, limit)

