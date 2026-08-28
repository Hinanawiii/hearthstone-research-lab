from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from cardlab.authoring.generated.keyword_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
    build_review_artifact,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.authoring.store import ReviewStore
from cardlab.cards import CARDS as BASE_CARDS

EXPECTED_CARDS = {
    "Core_CS2_200": ("石拳食人魔", 6, 6, 7, []),
    "CORE_BT_701": ("间谍女郎", 1, 3, 1, ["STEALTH"]),
    "CORE_EX1_010": ("狼人渗透者", 1, 2, 1, ["STEALTH"]),
    "CORE_GIL_558": ("沼泽水蛭", 1, 2, 1, ["LIFESTEAL"]),
    "CORE_ULD_723": ("鱼人木乃伊", 1, 1, 1, ["REBORN"]),
    "CORE_NEW1_023": ("精灵龙", 2, 3, 2, ["ELUSIVE"]),
    "CS3_038": ("红鳃锋颚战士", 2, 3, 1, ["RUSH"]),
    "CORE_EX1_028": ("荆棘谷猛虎", 5, 5, 5, ["STEALTH"]),
    "CORE_LOOT_137": ("贪睡巨龙", 9, 6, 12, ["TAUNT"]),
    "CORE_ICC_038": (
        "正义保护者",
        1,
        1,
        1,
        ["DIVINE_SHIELD", "TAUNT"],
    ),
    "CORE_GVG_085": (
        "吵吵机器人",
        2,
        1,
        2,
        ["DIVINE_SHIELD", "TAUNT"],
    ),
    "CORE_AT_052": ("图腾魔像", 2, 3, 4, ["OVERLOAD"]),
    "CORE_DRG_079": (
        "辟法巨龙",
        6,
        5,
        4,
        ["DIVINE_SHIELD", "ELUSIVE", "RUSH"],
    ),
    "CORE_EX1_250": ("土元素", 5, 7, 9, ["OVERLOAD", "TAUNT"]),
}


def _registry() -> dict[str, object]:
    registry = dict(BASE_CARDS)
    registry.update(CARDS)
    return registry


def _document(card_id: str) -> dict[str, object]:
    metadata = AUTHORING_METADATA[card_id]
    document = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": card_id,
            "name_zh": metadata["name_zh"],
            "source_text_zh": metadata["source_text_zh"],
            "source_version": metadata["source_version"],
        },
        "implementation": {
            "card_module": "src/cardlab/authoring/generated/keyword_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, _registry()),
    }
    return document


def test_batch_contracts_are_complete_and_self_contained() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == set(EXPECTED_CARDS)

    for card_id, expected in EXPECTED_CARDS.items():
        name, cost, attack, health, keywords = expected
        definition = CARDS[card_id]
        metadata = AUTHORING_METADATA[card_id]
        assert definition.name == metadata["name_zh"] == name
        assert definition.cost == metadata["cost"] == cost
        assert definition.attack == metadata["attack"] == attack
        assert definition.health == metadata["health"] == health
        assert metadata["source_version"] == "250339"
        assert metadata["keywords"] == keywords
        assert metadata["generated_by"] == "codex-gpt-5.6-sol-keyword-batch-v1"


def test_runner_registers_every_batch_card_without_local_run_files() -> None:
    batch_ids = set(EXPECTED_CARDS)
    assert batch_ids <= set(CARD_MODULES)
    assert batch_ids <= set(CARD_METADATA)
    assert batch_ids <= set(SCENARIO_BUILDERS)
    assert batch_ids <= set(SCENARIO_CARD_NAME_CATALOGS)

    with tempfile.TemporaryDirectory() as directory:
        store = ReviewStore(Path(directory) / "review.db")
        for card_id in EXPECTED_CARDS:
            metadata = AUTHORING_METADATA[card_id]
            store.upsert_card(
                card_id,
                metadata["name_zh"],
                metadata["source_text_zh"],
                source_version=metadata["source_version"],
            )
            store.set_interview_complete(card_id, True)
            store.approve_generation(card_id, "human-reviewer")
            artifact = build_review_artifact(store, card_id)
            assert artifact["card"]["card_id"] == card_id
            assert artifact["implementation"]["card_module"].endswith(
                "keyword_batch.py"
            )


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review_document(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    assert scenario["special_cases"] == []
    assert scenario["before"] != scenario["after"]

    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "核验目的" in rendered
    assert "执行动作" in rendered
    assert "操作前" in rendered
    assert "操作后" in rendered
    assert "逐项核对" in rendered
    assert "True" not in rendered
    assert "False" not in rendered


def test_combined_keyword_cards_keep_every_source_mechanic() -> None:
    wyrm = CARDS["CORE_DRG_079"]
    assert wyrm.rush and wyrm.divine_shield and wyrm.elusive
    wyrm_scenario = build_review_scenario("CORE_DRG_079", _registry())
    wyrm_after = next(
        minion
        for player in wyrm_scenario["after"]["players"]
        for minion in player["zones"]["board"]
        if minion["card_id"] == wyrm.card_id
    )
    assert "突袭" in wyrm_after["mechanics_zh"]
    assert "扰魔" in wyrm_after["mechanics_zh"]
    assert "圣盾" not in wyrm_after["mechanics_zh"]
    assert wyrm_after["health"] == wyrm.health

    for card_id in ("CORE_ICC_038", "CORE_GVG_085"):
        card = CARDS[card_id]
        assert card.taunt and card.divine_shield

    earth = CARDS["CORE_EX1_250"]
    assert earth.taunt and earth.overload == 2
    earth_after = build_review_scenario(earth.card_id, _registry())["after"]
    earth_owner = next(player for player in earth_after["players"] if player["role_zh"] == "敌方")
    earth_minion = next(
        minion for minion in earth_owner["zones"]["board"] if minion["card_id"] == earth.card_id
    )
    assert "嘲讽" in earth_minion["mechanics_zh"]
    assert earth_owner["resources"]["overloaded_mana"] == 2


def test_lifesteal_review_surfaces_the_less_obvious_defending_case() -> None:
    scenario = build_review_scenario("CORE_GIL_558", _registry())
    enemy_before = next(
        player for player in scenario["before"]["players"] if player["role_zh"] == "敌方"
    )
    enemy_after = next(
        player for player in scenario["after"]["players"] if player["role_zh"] == "敌方"
    )
    assert enemy_before["hero"]["health"] == 25
    assert enemy_after["hero"]["health"] == 27
    assert all(
        minion["card_id"] != "CORE_GIL_558"
        for minion in enemy_after["zones"]["board"]
    )
