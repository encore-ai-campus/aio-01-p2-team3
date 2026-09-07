"""영유아 육아 기록용 Streamable HTTP MCP 서버입니다."""

from mcp.server.fastmcp import FastMCP

from .config import settings
from .tools.analyze_infant_stool import analyze_infant_stool
from .tools.get_care_records import get_care_records
from .tools.record_care_event import record_care_event


mcp = FastMCP(
    "baby_care_server",
    instructions=(
        "육아 기록 저장·조회와 기저귀 사진 분석을 제공하는 MCP 서버입니다. "
        "기록 Tool 두 개와 Vision·규칙·stool RAG 고정 Workflow가 구현되어 있습니다."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
    stateless_http=True,
    json_response=True,
)

mcp.tool()(record_care_event)
mcp.tool()(get_care_records)
mcp.tool()(analyze_infant_stool)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
