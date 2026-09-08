from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from constants import ErrorCode


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolErrorResponse(StrictModel):
    success: Literal[False] = False
    message: str = Field(min_length=1, max_length=500)
    error_code: ErrorCode


class HospitalSearchRequest(StrictModel):
    """두 의료기관 Tool이 공통으로 사용하는 지역 검색 입력 계약입니다."""

    region: str = Field(min_length=2, max_length=100)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=30)

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("region은 공백을 제외하고 2자 이상이어야 합니다.")
        return normalized


class PediatricHospital(StrictModel):
    hospital_name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    phone: str | None = None
    operating_hours: str | None = None


class EmergencyHospital(StrictModel):
    hospital_name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    phone: str | None = None
    emergency_level: str | None = None


class HospitalToolResponse(StrictModel):
    success: Literal[True] = True
    region: str = Field(min_length=2, max_length=100)
    data: list[PediatricHospital | EmergencyHospital]
    source: Literal["public_data"] = "public_data"
    checked_at: datetime
    notice: str = Field(min_length=1)
