"""Chat and stream routes."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent.agent_service import answer_chat
from app.services.agent.chat_stream_service import stream_chat

router = APIRouter(prefix="/api", tags=["AI 채팅"])

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> dict:
    try:
        return await answer_chat(payload, request.app)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail="세션을 확인할 수 없습니다.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="육아 정보 검색 서비스를 사용할 수 없습니다.") from exc

@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(stream_chat(payload, request.app), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
