"""Safe, deterministic RAG-chat orchestration for the current MVP."""

import json
from datetime import date
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_clients.baby_info_client import search_knowledge_from_mcp
from app.models.baby import Baby
from .memory_service import get_relevant_memories, save_memory_candidate
from .memory_trace_service import write_chat_trace

CATEGORY_KEYWORDS = {
    "feeding": ("수유", "분유", "모유", "트림"),
    "sleep": ("수면", "잠", "낮잠", "재우"),
    "weaning": ("이유식", "식재료", "알레르기"),
    "development": ("발달", "뒤집", "기어", "말", "걸음"),
    "safety": ("안전", "질식", "낙상", "화상", "카시트"),
}

OUT_OF_SCOPE = "AI 육아 도우미는 수유·수면·이유식·발달·안전 관련 육아 정보를 도와드릴 수 있어요."


def classify_category(message: str) -> str | None:
    return next((category for category, words in CATEGORY_KEYWORDS.items() if any(word in message for word in words)), None)


async def _validate_context(request, app) -> Baby:
    raw = await app.state.redis.get(f"session:{request.user_id}:{request.session_id}")
    if not raw:
        raise PermissionError("세션이 없거나 만료되었습니다.")
    session_data = json.loads(raw)
    if session_data.get("user_id") != request.user_id or session_data.get("baby_id") != request.baby_id:
        raise PermissionError("요청한 아기 정보에 접근할 수 없습니다.")
    async with AsyncSession(app.state.db_engine, expire_on_commit=False) as db:
        baby = (await db.execute(select(Baby).where(Baby.id == request.baby_id, Baby.user_id == request.user_id))).scalar_one_or_none()
    if baby is None:
        raise PermissionError("아기 정보를 찾을 수 없습니다.")
    return baby


async def answer_chat(request, app) -> dict:
    request_id = str(uuid4())
    baby = await _validate_context(request, app)
    memories = await get_relevant_memories(app.state.db_engine, request.user_id, request.message)
    category = classify_category(request.message)
    if category is None:
        created = await save_memory_candidate(app.state.db_engine, request.user_id, request.message)
        await write_chat_trace(app.state.redis, user_id=request.user_id, session_id=request.session_id, baby_id=request.baby_id, request_id=request_id, tool_used=False, memory_count=len(memories), memory_created=created)
        return {"success": True, "message": "지원 범위를 안내했습니다.", "request_id": request_id,
                "data": {"response_type": "out_of_scope", "answer": OUT_OF_SCOPE, "sources": []}}
    age_months = max(0, min(36, (date.today() - baby.birth_date).days // 30))
    result = await search_knowledge_from_mcp(category, request.message, age_months)
    if not result.get("success"):
        raise RuntimeError("육아 정보 검색에 실패했습니다.")
    chat = {"response_type": "text", "answer": result["answer"], "sources": result.get("sources", []),
            "confidence": result.get("confidence"), "safety_notice": result.get("safety_notice")}
    await app.state.redis.rpush(f"chat:{request.user_id}:{request.session_id}", json.dumps({"role": "user", "content": request.message}, ensure_ascii=False), json.dumps({"role": "assistant", "content": chat["answer"]}, ensure_ascii=False))
    await app.state.redis.ltrim(f"chat:{request.user_id}:{request.session_id}", -8, -1)
    await app.state.redis.expire(f"chat:{request.user_id}:{request.session_id}", 86400)
    created = await save_memory_candidate(app.state.db_engine, request.user_id, request.message)
    await write_chat_trace(app.state.redis, user_id=request.user_id, session_id=request.session_id, baby_id=request.baby_id, request_id=request_id, tool_used=True, memory_count=len(memories), memory_created=created)
    return {"success": True, "message": "AI 답변을 생성했습니다.", "request_id": request_id, "data": chat}
