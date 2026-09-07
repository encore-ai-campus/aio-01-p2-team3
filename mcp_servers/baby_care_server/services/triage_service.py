"""Vision 관찰값과 보호자 입력을 고정 규칙으로 분류합니다."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..schemas.stool import AnalyzeInfantStoolInput, StoolObservation, StoolRisk


RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "infant_stool_triage.yaml"
LEVEL_ORDER = {"none": 0, "attention": 1, "urgent": 2, "emergency": 3}


@lru_cache(maxsize=1)
def load_triage_rules() -> dict[str, Any]:
    """검토하기 쉬운 YAML 규칙을 한 번 읽어 재사용합니다."""
    with RULES_PATH.open(encoding="utf-8") as rule_file:
        return yaml.safe_load(rule_file)


def evaluate_stool_risk(
    observation: StoolObservation,
    request: AnalyzeInfantStoolInput,
) -> tuple[StoolRisk, list[str]]:
    """진단 없이 위험 신호와 추가 확인 질문을 만듭니다."""
    rules = load_triage_rules()
    matched_levels = ["none"]
    signals: list[str] = []
    questions: list[str] = []

    for field_name, rule in rules["observation_rules"].items():
        if getattr(observation, field_name):
            matched_levels.append(rule["level"])
            signals.append(rule["signal"])
            questions.extend(rule.get("follow_up_questions", []))

    if observation.uncertainty == "high":
        rule = rules["context_rules"]["high_uncertainty"]
        matched_levels.append(rule["level"])
        signals.append(rule["signal"])
        questions.extend(rule["follow_up_questions"])

    if request.has_fever is True:
        rule_name = "young_infant_fever" if request.baby_age_months < 3 else "fever"
        rule = rules["context_rules"][rule_name]
        matched_levels.append(rule["level"])
        signals.append(rule["signal"])
        questions.extend(rule["follow_up_questions"])
    elif request.has_fever is None:
        questions.append("현재 체온을 측정했나요? 측정했다면 체온과 측정 방법을 알려주세요.")

    if request.stool_count_24h is None:
        questions.append("최근 24시간 동안 대변을 몇 번 보았나요?")
    elif request.stool_count_24h >= rules["thresholds"]["frequent_stool_count_24h"]:
        rule = rules["context_rules"]["frequent_stool"]
        matched_levels.append(rule["level"])
        signals.append(rule["signal"].format(count=request.stool_count_24h))
        questions.extend(rule["follow_up_questions"])

    if observation.black_tarry_appearance and request.baby_age_months == 0:
        questions.append("아기가 생후 며칠이며 현재 첫 태변을 보는 시기인가요?")

    level = max(matched_levels, key=LEVEL_ORDER.__getitem__)
    risk = StoolRisk(
        level=level,
        signals=list(dict.fromkeys(signals)),
        recommended_action=rules["actions"][level],
    )
    return risk, list(dict.fromkeys(questions))
