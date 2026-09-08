"""Persistence and retrieval for safe answer-preference memories."""

from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_memory import UserMemory
from .memory_safety_service import extract_safe_memory
from .memory_selector import select_memories

async def get_relevant_memories(engine, user_id: str, question: str):
    async with AsyncSession(engine) as session:
        records = (await session.execute(select(UserMemory).where(UserMemory.user_id == user_id).order_by(UserMemory.updated_at.desc()).limit(20))).scalars().all()
    return select_memories(records, question)

async def save_memory_candidate(engine, user_id: str, message: str) -> int:
    candidate = extract_safe_memory(message)
    if not candidate:
        return 0
    content, tags = candidate
    async with AsyncSession(engine) as session:
        existing = (await session.execute(select(UserMemory).where(UserMemory.user_id == user_id, UserMemory.content == content))).scalar_one_or_none()
        if existing is None:
            session.add(UserMemory(id=str(uuid4()), user_id=user_id, memory_type="preference", content=content, tags=tags))
            await session.commit()
            return 1
    return 0
