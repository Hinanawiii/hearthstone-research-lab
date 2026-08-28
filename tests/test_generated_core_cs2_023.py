from dataclasses import asdict

from cardlab.authoring.generated.core_cs2_023 import (
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
from cardlab.model import CardDef


def _registry() -> dict[str, CardDef]:
    registry = dict(CARDS)
    registry[CARD.card_id] = CARD
    return registry


def test_arcane_intellect_matches_the_approved_card_contract() -> None:
    assert CARD.card_id == "CORE_CS2_023"
    assert CARD.name == "奥术智慧"
    assert CARD.cost == 3
    assert [(effect.kind, effect.amount, effect.target) for effect in CARD.effects] == [
        ("draw", 2, "owner")
    ]
    assert AUTHORING_METADATA["source_version"] == "250339"
    assert AUTHORING_METADATA["source_text_zh"] == "抽两张牌。"


def test_arcane_intellect_draws_twice_in_deck_order() -> None:
    scenario = build_review_scenario(_registry())
    before_own = scenario["before"]["players"][0]
    after_own = scenario["after"]["players"][0]

    assert before_own["zones"]["deck"] == {
        "count": 3,
        "order_known": True,
        "known_top_card_ids": ["CS2_231", "CS2_189", "CS1_042"],
    }
    assert [card["card_id"] for card in before_own["zones"]["hand"]["cards"]] == [
        "CORE_CS2_023",
        "CS2_120",
    ]
    assert [card["card_id"] for card in after_own["zones"]["hand"]["cards"]] == [
        "CS2_120",
        "CS2_231",
        "CS2_189",
    ]
    assert after_own["zones"]["deck"] == {
        "count": 1,
        "order_known": True,
        "known_top_card_ids": ["CS1_042"],
    }
    assert after_own["resources"]["mana"] == 2

    deck_change = scenario["special_cases"][0]
    assert deck_change["kind"] == "deck_change"
    assert deck_change["details"] == {
        "player_id": scenario["before"]["viewer_player_id"],
        "before_count": 3,
        "after_count": 1,
        "drawn_count": 2,
        "added_count": 0,
        "shuffled_count": 0,
        "order_changed": False,
        "known_top_before": ["CS2_231", "CS2_189", "CS1_042"],
        "known_top_after": ["CS1_042"],
    }


def test_arcane_intellect_scenario_fits_the_chinese_review_document() -> None:
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
            "card_module": "src/cardlab/authoring/generated/core_cs2_023.py",
            "generator": AUTHORING_METADATA["generated_by"],
            "definition": asdict(CARD),
        },
        "scenario": build_review_scenario(_registry()),
    }

    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert "奥术智慧：连续抽取两张已知牌" in rendered
    assert "淡水鳄（CS2_120）、小精灵（CS2_231）、精灵弓箭手（CS2_189）" in rendered
    assert "抽取数量=2" in rendered
    assert "洗入数量=0" in rendered
    assert "牌序是否改变=否" in rendered
    assert "变更后已知牌库顶=闪金镇步兵（CS1_042）" in rendered
