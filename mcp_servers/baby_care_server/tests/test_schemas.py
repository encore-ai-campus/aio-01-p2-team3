"""2단계 Pydantic Schema 테스트입니다."""

from datetime import date

import pytest
from pydantic import ValidationError

from ..schemas.care import GetCareRecordsInput, RecordCareEventInput
from ..schemas.stool import AnalyzeInfantStoolInput


def test_amount_ml_zero_is_allowed() -> None:
    request = RecordCareEventInput(
        baby_id="baby-001",
        event_type="feeding",
        input_source="ui",
        idempotency_key="test-001",
        feeding_type="formula",
        amount_ml=0,
    )
    assert request.amount_ml == 0


def test_negative_amount_ml_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RecordCareEventInput(
            baby_id="baby-001",
            event_type="feeding",
            input_source="ui",
            idempotency_key="test-002",
            feeding_type="formula",
            amount_ml=-1,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("weight_kg", 0),
        ("height_cm", -1),
        ("head_circumference_cm", 0),
    ],
)
def test_growth_values_must_be_positive(
    field_name: str, invalid_value: float
) -> None:
    with pytest.raises(ValidationError):
        RecordCareEventInput(
            baby_id="baby-001",
            event_type="growth",
            input_source="ui",
            idempotency_key=f"test-growth-{field_name}",
            **{field_name: invalid_value},
        )


def test_range_requires_both_dates() -> None:
    with pytest.raises(ValidationError):
        GetCareRecordsInput(
            baby_id="baby-001",
            query_type="range",
            start_date=date(2026, 9, 1),
        )


def test_range_rejects_reversed_dates() -> None:
    with pytest.raises(ValidationError):
        GetCareRecordsInput(
            baby_id="baby-001",
            query_type="range",
            start_date=date(2026, 9, 4),
            end_date=date(2026, 9, 1),
        )


def test_stool_age_is_limited_to_36_months() -> None:
    with pytest.raises(ValidationError):
        AnalyzeInfantStoolInput(
            baby_id="baby-001",
            image_path="temporary/test.jpg",
            baby_age_months=37,
            feeding_type="formula",
        )
