"""MCP Tool이 공통으로 사용하는 응답 Schema입니다."""

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolError(StrictBaseModel):
    code: str
    detail: str


class ToolWarning(StrictBaseModel):
    code: str
    detail: str
