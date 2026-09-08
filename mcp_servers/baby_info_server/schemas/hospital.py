"""Hospital search schemas shared by the two hospital MCP tools."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HospitalSearchInput(StrictModel):
    region: str = Field(min_length=2, max_length=100)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=30)


class PediatricHospital(StrictModel):
    hospital_name: str
    address: str
    phone: str | None = None
    operating_hours: str | None = None


class EmergencyHospital(StrictModel):
    hospital_name: str
    address: str
    phone: str | None = None
    emergency_level: str | None = None


class HospitalSearchResult(StrictModel):
    success: bool = True
    region: str
    data: list[dict]
    source: Literal["public_data"] = "public_data"
    checked_at: datetime
    notice: str
