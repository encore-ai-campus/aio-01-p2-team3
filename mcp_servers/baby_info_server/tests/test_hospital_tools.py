"""Contract tests for hospital MCP tools without calling an external API."""

import asyncio

import pytest
from pydantic import ValidationError

from ..tools import search_emergency_hospitals, search_pediatric_hospitals


def test_pediatric_tool_normalizes_valid_request(monkeypatch):
    async def fake_search(region, page, limit):
        return {"success": True, "region": region, "data": [], "source": "public_data", "checked_at": "2026-09-07T00:00:00+00:00", "notice": "확인 안내"}
    monkeypatch.setattr(search_pediatric_hospitals, "search_pediatric", fake_search)
    result = asyncio.run(search_pediatric_hospitals.search_pediatric_hospitals(" 서울특별시 동작구 ", 1, 10))
    assert result["success"] is True
    assert result["region"] == "서울특별시 동작구"


def test_emergency_tool_rejects_invalid_page():
    with pytest.raises(ValidationError):
        asyncio.run(search_emergency_hospitals.search_emergency_hospitals("서울특별시 동작구", 0, 10))


def test_pediatric_tool_rejects_blank_region():
    with pytest.raises(ValidationError):
        asyncio.run(search_pediatric_hospitals.search_pediatric_hospitals(" ", 1, 10))
