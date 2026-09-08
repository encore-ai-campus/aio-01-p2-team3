"""Contract tests for fixed-category knowledge tools."""

import asyncio

import pytest
from pydantic import ValidationError

from ..tools import search_feeding_guide


def test_feeding_tool_fixes_category(monkeypatch):
    async def fake_search(category, query, age, top_k):
        return {"success": True, "answer": "근거 답변", "category": category, "sources": [], "confidence": "low", "safety_notice": None}
    monkeypatch.setattr(search_feeding_guide, "search_category", fake_search)
    result = asyncio.run(search_feeding_guide.search_feeding_guide("수유 간격", 3, 2))
    assert result["category"] == "feeding"


def test_knowledge_tool_rejects_invalid_query():
    with pytest.raises(ValidationError):
        asyncio.run(search_feeding_guide.search_feeding_guide(" "))
