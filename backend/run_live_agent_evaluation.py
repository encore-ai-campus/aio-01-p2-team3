"""Run 20 read-only live Agent requests and preserve redacted Trace evidence.

Start the Backend, Redis, and both MCP servers first. This evaluator uses a
fresh test-login session and does not create care records, so it is safe to run
against the local demonstration database.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import REDIS_URL


BASE_URL = os.getenv("LIVE_AGENT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TEST_USER_ID = os.getenv("LIVE_AGENT_TEST_USER_ID", "user-002")
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "artifacts"


CASES = (
    ("오늘 수유 몇번했어", ("get_care_records",), "text"),
    ("오늘 수면 총 몇시간 했어", ("get_care_records",), "text"),
    ("오늘 소변 대변 몇번했어", ("get_care_records",), "text"),
    ("지난 7일 수유 패턴 알려줘", ("get_care_records",), "text"),
    ("분유 먹었어", (), "clarification_required"),
    ("낮잠 잤어", (), "clarification_required"),
    ("서울 동작구 소아과 찾아줘", ("search_pediatric_hospitals",), "hospital_list"),
    ("부산 응급실 알려줘", ("search_emergency_hospitals",), "hospital_list"),
    ("근처 소아과 알려줘", (), "clarification_required"),
    ("병원 알려줘", (), "clarification_required"),
    ("생후 4개월 아기 수유 간격 알려줘", ("search_feeding_guide",), "text"),
    ("아기가 자다가 울면서 깨는데 어떻게 해야 해?", ("search_sleep_guide",), "text"),
    ("이유식은 언제 시작해?", ("search_weaning_guide",), "text"),
    ("뒤집기는 보통 언제 해?", ("search_development_guide",), "text"),
    ("아기 침대 안전수칙 알려줘", ("search_safety_guide",), "text"),
    ("아기 목욕은 어떻게 시키면 좋아?", (), "text"),
    ("오늘 서울 날씨 알려줘", (), "out_of_scope"),
    ("주식 종목 추천해 줘", (), "out_of_scope"),
    ("땅콩 알레르기가 있으면 무엇을 조심해야 해?", (), "text"),
    ("안녕하세요", (), "text"),
)


def post_json(path: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return {"http_status": response.status, "body": json.loads(response.read().decode("utf-8"))}
    except HTTPError as error:
        return {"http_status": error.code, "body": json.loads(error.read().decode("utf-8"))}
    except (URLError, TimeoutError) as error:
        return {"http_status": 0, "body": {"detail": str(error)}}


async def read_trace(redis, user_id: str, session_id: str, request_id: str) -> dict | None:
    for _ in range(10):
        raw = await redis.get(f"trace:{user_id}:{session_id}:{request_id}")
        if raw:
            return json.loads(raw)
        await asyncio.sleep(0.1)
    return None


async def main() -> int:
    login = post_json("/api/test-login", {"user_id": TEST_USER_ID})
    if login["http_status"] != 200:
        raise SystemExit(f"로그인 실패: {login}")

    session = login["body"]["data"]
    user_id, baby_id, session_id = session["user_id"], session["baby_id"], session["session_id"]
    headers = {"X-User-Id": user_id, "X-Session-Id": session_id}
    redis = __import__("redis.asyncio", fromlist=["from_url"]).from_url(REDIS_URL, decode_responses=True)
    results: list[dict] = []
    try:
        for index, (message, expected_tools, expected_type) in enumerate(CASES, start=1):
            response = post_json("/api/chat", {"message": message, "baby_id": baby_id, "session_id": session_id}, headers)
            body = response["body"]
            data = body.get("data") or {}
            request_id = body.get("request_id")
            trace = await read_trace(redis, user_id, session_id, request_id) if request_id else None
            actual_tools = tuple((trace or {}).get("selected_tools") or ())
            passed = (
                response["http_status"] == 200
                and data.get("response_type") == expected_type
                and actual_tools == expected_tools
                and trace is not None
            )
            results.append({
                "id": f"L-{index:02d}", "message": message,
                "expected_tools": expected_tools, "expected_response_type": expected_type,
                "http_status": response["http_status"], "actual_tools": actual_tools,
                "actual_response_type": data.get("response_type"), "request_id": request_id,
                "trace": trace, "passed": passed,
            })
            sleep(0.05)
    finally:
        await redis.aclose()

    summary = {
        "evaluated_at": datetime.now().astimezone().isoformat(),
        "base_url": BASE_URL, "test_user_id": user_id, "baby_id": baby_id,
        "read_only": True, "total": len(results), "passed": sum(item["passed"] for item in results),
        "failed": sum(not item["passed"] for item in results), "results": results,
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"live_agent_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed; evidence: {output_path}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
