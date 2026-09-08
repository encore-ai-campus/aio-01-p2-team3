"""Streamlit과 FastAPI 사이의 공통 API 계층.

백엔드가 준비되기 전에는 ``USE_MOCK_API=true``로 목데이터를 사용한다.
준비 후에는 환경변수를 false로 바꾸고, 확정된 엔드포인트별 함수가
아래 공통 HTTP 클라이언트를 사용하도록 연결한다.
페이지 파일은 이 모듈의 함수만 호출하며 HTTP 세부 구현을 직접 갖지 않는다.
"""

from __future__ import annotations

import os
from typing import Any

import requests


BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000").rstrip("/")
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
API_TIMEOUT_SECONDS = float(os.getenv("BACKEND_API_TIMEOUT_SECONDS", "10"))


def backend_settings() -> dict[str, Any]:
    """현재 연결 대상 정보. 화면에는 URL이나 내부 오류를 그대로 노출하지 않는다."""
    return {"base_url": BACKEND_API_URL, "use_mock_api": USE_MOCK_API, "timeout_seconds": API_TIMEOUT_SECONDS}


def request_backend(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """문서의 공통 응답 형식으로 FastAPI 응답과 네트워크 오류를 정규화한다.

    실제 호출은 백엔드 개발 완료 후, 각 엔드포인트 함수에서 사용한다.
    """
    url = f"{BACKEND_API_URL}{path}"
    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json,
            data=data,
            files=files,
            headers=headers,
            timeout=API_TIMEOUT_SECONDS,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}

        if isinstance(body, dict):
            return {
                "success": bool(body.get("success", response.ok)),
                "message": body.get("message", "" if response.ok else "요청을 처리하지 못했습니다."),
                "data": body.get("data", {}),
                "request_id": body.get("request_id"),
                "status_code": response.status_code,
            }
        return {"success": response.ok, "message": "응답 형식이 올바르지 않습니다.", "data": {}, "request_id": None, "status_code": response.status_code}
    except requests.RequestException:
        return {
            "success": False,
            "message": "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
            "data": {},
            "request_id": None,
            "status_code": None,
        }


BABY = {
    "baby_id": "baby-seoa-001",
    "baby_name": "서아",
    "birth_date": "2026-08-03",
    "age_days": 31,
    "gender": "여아",
    "feeding_type": "분유",
    "current_weight_kg": 4.2,
    "birth_weight_kg": 3.2,
    "current_height_cm": 54.1,
    "head_circumference_cm": 37.0,
    "allergies": ["땅콩"],
}


def test_login(_: str) -> dict:
    return {"success": True, "data": {"user_id": "guardian-seoa", "baby_id": BABY["baby_id"], "session_id": "demo-session"}}


def get_baby(_: str) -> dict:
    return {"success": True, "data": BABY.copy()}


def get_dashboard(_: str) -> dict:
    return {
        "success": True,
        "data": {
            "feeding": {"average_count": 7, "average_interval": "평균 3시간 10분 간격"},
            "sleep": {"daily_hours": "15시간", "last": "어제 22:10"},
            "diaper": {"daily_count": 5, "detail": "소변 4회 · 대변 1회"},
            "next_vaccination": {"date": "9월 18일", "name": "DTaP 1차 · IPV 1차", "remaining": "14일 남았어요."},
        },
    }


def get_care_records(_: str) -> dict:
    return {
        "success": True,
        "data": [
            {"time": "오늘 14:30", "icon": "🍼", "title": "분유 수유", "detail": "100ml · 알림 확인으로 기록"},
            {"time": "오늘 12:05", "icon": "🌙", "title": "낮잠 종료", "detail": "10:20–12:05 · 1시간 45분"},
            {"time": "오늘 09:40", "icon": "💩", "title": "기저귀 · 대변", "detail": "노란색, 묽은 형태 · 사진 분석 메모 있음"},
            {"time": "9월 2일", "icon": "📏", "title": "성장 측정", "detail": "몸무게 4.2kg · 키 54.1cm · 머리둘레 37cm"},
        ],
    }


def get_care_pattern(_: str) -> dict:
    return {
        "success": True,
        "data": {
            "sufficient_data": True,
            "average_interval": "3시간 12분",
            "daily_feeding": "6.7회",
            "daily_sleep": "7.8시간",
            "daily_diaper": "2.7회",
            "intervals": [2.7, 3.0, 2.8, 3.4, 3.1, 3.6, 3.45],
        },
    }


def search_hospitals(region: str, hospital_type: str, page: int = 1, limit: int = 10) -> dict[str, Any]:
    """Search hospitals through FastAPI once ``USE_MOCK_API`` is disabled."""
    if not USE_MOCK_API:
        return request_backend("GET", "/api/hospitals/search", params={"region": region, "type": hospital_type, "page": page, "limit": limit})
    return {"success": True, "message": "목데이터 검색 결과입니다.", "data": {"region": region, "type": hospital_type, "data": [], "source": "mock", "checked_at": None, "notice": "실제 병원 검색은 백엔드 연결 후 이용할 수 있습니다."}, "request_id": None, "status_code": 200}


def analyze_diaper_image(image_file, baby_id: str, session_id: str, user_id: str, feeding_type: str, has_fever: bool | None = None, stool_count_24h: int | None = None) -> dict[str, Any]:
    """Upload a diaper image; analysis never saves a care record automatically."""
    if not USE_MOCK_API:
        return request_backend("POST", "/api/images/diaper-analysis", files={"image": image_file}, data={"baby_id": baby_id, "session_id": session_id, "user_id": user_id, "feeding_type": feeding_type, "has_fever": has_fever, "stool_count_24h": stool_count_24h})
    return {"success": True, "message": "목 분석 결과입니다.", "data": {"baby_id": baby_id, "is_analyzable": False, "quality_issues": ["실제 사진 분석은 백엔드 연결 후 이용할 수 있습니다."], "observation": None, "risk": None, "follow_up_questions": [], "sources": [], "warnings": [], "safety_notice": "사진만으로 질환을 진단할 수 없습니다."}, "request_id": None, "status_code": 200}


def create_care_log(payload: dict[str, Any], user_id: str, session_id: str) -> dict[str, Any]:
    """Save an explicitly entered care event through the authenticated API."""
    if not USE_MOCK_API:
        return request_backend("POST", "/api/care-logs", json=payload, headers={"X-User-Id": user_id, "X-Session-Id": session_id})
    return {"success": True, "message": "목데이터에 기록했습니다.", "data": {"event_type": payload["event_type"], "duplicated": False}, "request_id": None, "status_code": 200}


def get_growth(_: str) -> dict:
    return {
        "success": True,
        "data": {
            "weight": [3.2, 3.45, 3.7, 4.0, 4.2],
            "height": [50.0, 51.2, 52.4, 53.4, 54.1],
            "head": [34.0, 34.8, 35.8, 36.5, 37.0],
            "reference": [3.45, 3.6, 3.85, 4.1, 4.35],
        },
    }


def get_vaccinations(_: str) -> dict:
    return {
        "success": True,
        "data": {
            "next": {"name": "B형간염 2차", "period": "생후 1개월 권장 일정 기준", "date": "2026. 09. 06 예정"},
            "items": [
                ("BCG", "결핵 예방 · 1회", "접종 완료 · 8/10", "done"),
                ("B형간염 1차", "출생 직후", "접종 완료 · 8/03", "done"),
                ("B형간염 2차", "생후 1개월", "접종 예정 · 9/06", "soon"),
                ("DTaP·IPV·Hib 1차", "생후 2개월", "예정 · 10/03", "future"),
            ],
        },
    }


def send_chat(message: str, baby_id: str, session_id: str, user_id: str) -> dict:
    """Send the contract-required chat identifiers with every message."""
    if not USE_MOCK_API:
        return request_backend("POST", "/api/chat", json={"message": message, "baby_id": baby_id, "session_id": session_id, "user_id": user_id})
    return {
        "success": True,
        "data": {
            "response_type": "text",
            "answer": "생후 30일 아기의 수유량은 아기마다 달라요. 서아의 최근 수유 기록과 배고픔 신호를 함께 살펴보세요. 평소와 크게 달라지거나 걱정되는 변화가 있으면 소아과에 문의해 주세요.",
            "sources": [],
            "confidence": "low",
            "safety_notice": None,
        },
    }
