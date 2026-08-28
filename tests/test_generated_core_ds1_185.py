from dataclasses import asdict

from cardlab.authoring.generated.core_ds1_185 import (
    AUTHORING_METADATA,
    CARD,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.cards import CARDS
from cardlab.model import CardType, TargetMode


def _runtime_registry():
    return {**CARDS, CARD.card_id: CARD}


def test_arcane_shot_matches_the_approved_card_contract() -> None:
    assert CARD.card_id == "CORE_DS1_185"
    assert CARD.name == "奥术射击"
    assert CARD.card_type == CardType.SPELL
    assert CARD.cost == 1
    assert CARD.target_mode == TargetMode.ANY_CHARACTER
    assert [(effect.kind, effect.amount, effect.target) for effect in CARD.effects] == [
        ("damage", 2, "selected")
    ]
    assert AUTHORING_METADATA["source_version"] == "250339"
    assert AUTHORING_METADATA["source_text_zh"] == "造成2点伤害。"


def test_arcane_shot_review_scenario_selects_the_friendly_hero() -> None:
    scenario = build_review_scenario(_runtime_registry())
    before_players = {player["role_zh"]: player for player in scenario["before"]["players"]}
    after_players = {player["role_zh"]: player for player in scenario["after"]["players"]}

    assert scenario["action"]["target"] == {
        "player_id": scenario["before"]["viewer_player_id"],
        "kind": "hero",
        "entity_id": None,
        "description_zh": "我方英雄",
    }
    assert scenario["action"]["engine_action"]["target"] == {
        "player": scenario["before"]["viewer_player_id"],
        "kind": "hero",
        "entity_id": None,
    }
    assert before_players["我方"]["hero"]["health"] == 30
    assert after_players["我方"]["hero"]["health"] == 28
    assert after_players["敌方"]["hero"]["health"] == 30
    assert after_players["我方"]["zones"]["board"][0]["health"] == 3
    assert after_players["敌方"]["zones"]["board"][0]["health"] == 1
    assert after_players["我方"]["resources"]["mana"] == 0
    assert after_players["我方"]["zones"]["hand"]["count"] == 0
    assert scenario["special_cases"] == []


def test_arcane_shot_scenario_is_a_valid_chinese_review_document() -> None:
    scenario = build_review_scenario(_runtime_registry())
    document = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": CARD.card_id,
            "name_zh": CARD.name,
            "source_text_zh": AUTHORING_METADATA["source_text_zh"],
            "source_version": AUTHORING_METADATA["source_version"],
        },
        "implementation": {
            "card_module": "src/cardlab/authoring/generated/core_ds1_185.py",
            "generator": AUTHORING_METADATA["generated_by"],
            "definition": asdict(CARD),
        },
        "scenario": scenario,
    }

    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert "奥术射击：选择我方英雄" in rendered
    assert "我方使用《奥术射击》，选择我方英雄作为目标。" in rendered
    assert "我方英雄是合法目标，受到2点伤害" in rendered
    assert "特殊情况" not in rendered
