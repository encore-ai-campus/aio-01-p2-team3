"""Public chat API contract shared with the Streamlit client."""

from typing import Literal
from pydantic import BaseModel, Field

ResponseType = Literal["text", "options", "record_confirmation", "hospital_list", "diaper_analysis", "stt_record_approval", "speech_transcription", "out_of_scope", "unsupported_feature", "clarification_required", "policy_blocked", "error"]

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    baby_id: str = Field(min_length=1, max_length=100)
    session_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)

class ChatSource(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    organization: str
    url: str
    verified_at: str | None = None
    score: float

class ChatData(BaseModel):
    response_type: ResponseType
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    confidence: Literal["high", "low"] | None = None
    safety_notice: str | None = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    data: ChatData
    request_id: str
