"""care_logs 테이블에 직접 접근하는 Repository입니다."""

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ..config import settings


def connect() -> psycopg.Connection:
    """환경변수의 DSN으로 PostgreSQL 연결을 만듭니다."""
    dsn = settings.postgres_dsn.replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return psycopg.connect(dsn, row_factory=dict_row)


def baby_exists(baby_id: str) -> bool:
    """외래키 오류 전에 아기 ID가 존재하는지 확인합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM babies WHERE id = %s) AS exists",
            (baby_id,),
        )
        row = cursor.fetchone()
        return bool(row and row["exists"])


def find_by_idempotency_key(idempotency_key: str) -> dict[str, Any] | None:
    """이미 처리한 저장 요청인지 확인합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id AS log_id, baby_id, log_type AS event_type,
                   recorded_at, details, idempotency_key, created_at, updated_at
            FROM care_logs
            WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def insert_care_log(
    *,
    log_id: str,
    baby_id: str,
    event_type: str,
    recorded_at: datetime,
    details: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    """검증이 끝난 육아 기록 한 건을 저장하고 저장 결과를 반환합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO care_logs
                (id, baby_id, log_type, recorded_at, details, idempotency_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id AS log_id, baby_id, log_type AS event_type,
                      recorded_at, details, idempotency_key, created_at, updated_at
            """,
            (
                log_id,
                baby_id,
                event_type,
                recorded_at,
                Jsonb(details),
                idempotency_key,
            ),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("care_logs 저장 결과를 가져오지 못했습니다.")
        return dict(row)


def find_records_by_date_range(
    *,
    baby_id: str,
    start_at: datetime,
    end_at: datetime,
) -> list[dict[str, Any]]:
    """시작 시각 이상, 종료 시각 미만에 기록된 아기 기록을 조회합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id AS log_id, baby_id, log_type AS event_type,
                   recorded_at, details, idempotency_key, created_at, updated_at
            FROM care_logs
            WHERE baby_id = %s
              AND recorded_at >= %s
              AND recorded_at < %s
            ORDER BY recorded_at ASC, created_at ASC
            """,
            (baby_id, start_at, end_at),
        )
        return [dict(row) for row in cursor.fetchall()]


def find_latest_feeding(baby_id: str) -> dict[str, Any] | None:
    """아기의 가장 최근 수유 기록 한 건을 조회합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id AS log_id, baby_id, log_type AS event_type,
                   recorded_at, details, idempotency_key, created_at, updated_at
            FROM care_logs
            WHERE baby_id = %s AND log_type = 'feeding'
            ORDER BY recorded_at DESC, created_at DESC
            LIMIT 1
            """,
            (baby_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def find_open_sleep(baby_id: str) -> dict[str, Any] | None:
    """가장 최근 수면 동작이 start이면 진행 중인 수면 기록을 반환합니다."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id AS log_id, baby_id, log_type AS event_type,
                   recorded_at, details, idempotency_key, created_at, updated_at
            FROM care_logs
            WHERE baby_id = %s
              AND log_type = 'sleep'
              AND details->>'action' IN ('start', 'end')
            ORDER BY recorded_at DESC, created_at DESC
            LIMIT 1
            """,
            (baby_id,),
        )
        row = cursor.fetchone()
        if row is None or row["details"].get("action") != "start":
            return None
        return dict(row)
