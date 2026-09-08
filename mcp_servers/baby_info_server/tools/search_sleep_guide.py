"""Sleep guide RAG MCP tool."""
from .knowledge import search_category

async def search_sleep_guide(query: str, baby_age_months: int | None = None, top_k: int = 5) -> dict:
    return await search_category("sleep", query, baby_age_months, top_k)
