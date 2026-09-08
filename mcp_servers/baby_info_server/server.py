"""Baby information Streamable HTTP MCP server."""

from mcp.server.fastmcp import FastMCP

from .config import settings
from .tools.search_emergency_hospitals import search_emergency_hospitals
from .tools.search_pediatric_hospitals import search_pediatric_hospitals
from .tools.search_feeding_guide import search_feeding_guide
from .tools.search_sleep_guide import search_sleep_guide
from .tools.search_weaning_guide import search_weaning_guide
from .tools.search_development_guide import search_development_guide
from .tools.search_safety_guide import search_safety_guide


mcp = FastMCP("baby_info_server", host=settings.mcp_host, port=settings.mcp_port, stateless_http=True, json_response=True)
mcp.tool()(search_pediatric_hospitals)
mcp.tool()(search_emergency_hospitals)
mcp.tool()(search_feeding_guide)
mcp.tool()(search_sleep_guide)
mcp.tool()(search_weaning_guide)
mcp.tool()(search_development_guide)
mcp.tool()(search_safety_guide)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
