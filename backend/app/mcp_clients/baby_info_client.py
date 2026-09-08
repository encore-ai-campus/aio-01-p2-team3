"""Client for the two hospital-search tools on baby_info_server."""

import json
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.core.config import BABY_INFO_MCP_URL


@asynccontextmanager
async def baby_info_session():
    async with streamable_http_client(BABY_INFO_MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def search_hospitals_from_mcp(hospital_type: str, region: str, page: int, limit: int) -> dict:
    tool_name = {"pediatric": "search_pediatric_hospitals", "emergency": "search_emergency_hospitals"}[hospital_type]
    try:
        async with baby_info_session() as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            if tool_name not in tools:
                raise RuntimeError("baby_info_server에 병원 검색 Tool이 없습니다.")
            result = await session.call_tool(tool_name, {"region": region, "page": page, "limit": limit})
            text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
            if result.isError or not text:
                raise RuntimeError("병원 검색 Tool 실행에 실패했습니다.")
            return json.loads(text)
    except (RuntimeError, ValueError):
        raise
    except Exception as exc:
        raise RuntimeError("baby_info_server 연결에 실패했습니다.") from exc


async def search_knowledge_from_mcp(category: str, query: str, baby_age_months: int | None) -> dict:
    tool_name = f"search_{category}_guide"
    try:
        async with baby_info_session() as session:
            available = {tool.name for tool in (await session.list_tools()).tools}
            if tool_name not in available:
                raise RuntimeError("baby_info_server에 육아 정보 검색 Tool이 없습니다.")
            result = await session.call_tool(tool_name, {"query": query, "baby_age_months": baby_age_months, "top_k": 5})
            text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
            if result.isError or not text:
                raise RuntimeError("육아 정보 검색 Tool 실행에 실패했습니다.")
            return json.loads(text)
    except (RuntimeError, ValueError):
        raise
    except Exception as exc:
        raise RuntimeError("baby_info_server 연결에 실패했습니다.") from exc
