"""Info·Care·Backend 사이의 정적 계약을 검증한다."""

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INFO_SERVER = PROJECT_ROOT / "mcp_servers" / "baby_info_server" / "server.py"
CARE_RAG_REPOSITORY = PROJECT_ROOT / "mcp_servers" / "baby_care_server" / "repositories" / "rag_repository.py"

EXPECTED_INFO_TOOLS = {
    "search_pediatric_hospitals",
    "search_emergency_hospitals",
    "search_feeding_guide",
    "search_sleep_guide",
    "search_weaning_guide",
    "search_development_guide",
    "search_safety_guide",
}


def test_info_server_registers_exactly_seven_planned_tools() -> None:
    tree = ast.parse(INFO_SERVER.read_text(encoding="utf-8"))
    tool_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "mcp"
            and decorator.func.attr == "tool"
            for decorator in node.decorator_list
        )
    }

    assert tool_names == EXPECTED_INFO_TOOLS
    assert "get_vaccination_info" not in tool_names
    assert "search_stool_guide" not in tool_names


def test_care_reads_only_stool_documents_with_same_age_filter_contract() -> None:
    sql = CARE_RAG_REPOSITORY.read_text(encoding="utf-8")

    assert "d.category = 'stool'" in sql
    assert "COALESCE(dc.age_min_months, 0) <= %(baby_age_months)s" in sql
    assert "COALESCE(dc.age_max_months, 36) >= %(baby_age_months)s" in sql
    assert "1 - (dc.embedding <=> %(query_embedding)s::vector)" in sql
