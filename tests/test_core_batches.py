from __future__ import annotations

import tempfile
from pathlib import Path

from cardlab.authoring.core_batches import (
    CATEGORIES,
    build_core_batch_report,
    classify_core_card,
)
from cardlab.authoring.store import ReviewStore


def _card(card_id: str, card_type: str, source_text: str) -> dict[str, object]:
    return {
        "card_id": card_id,
        "card_type": card_type,
        "source_text": source_text,
    }


def test_classification_routes_each_dominant_engine_dependency() -> None:
    examples = {
        "deterministic_damage": _card("CORE_CS2_029", "SPELL", "造成6点伤害。"),
        "weapons_and_hero_combat": _card("W", "WEAPON", "吸血"),
        "special_actions_and_zones": _card("L", "LOCATION", "造成1点伤害。"),
        "event_triggers_and_history": _card("T", "MINION", "在你的回合结束时，抽一张牌。"),
        "hand_deck_and_random": _card("H", "SPELL", "发现一张法术牌。"),
        "summon_death_and_corpses": _card("S", "SPELL", "召唤两个1/1的随从。"),
        "stats_status_and_resources": _card("B", "SPELL", "使一个随从获得+2/+3。"),
        "composite_and_unique": _card("U", "MINION", "你的英雄免疫。"),
    }
    assert {classify_core_card(card) for card in examples.values()} == set(examples)
    for category, card in examples.items():
        assert classify_core_card(card) == category


def test_report_assigns_every_remaining_core_card_once() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ReviewStore(Path(directory) / "review.db")
        samples = [
            ("CORE_CS2_029", "火球术", "SPELL", "造成6点伤害。"),
            ("W", "测试武器", "WEAPON", "吸血"),
            ("L", "测试地标", "LOCATION", "造成1点伤害。"),
            ("T", "测试触发", "MINION", "每当你抽一张牌时，获得+1攻击力。"),
            ("H", "测试发现", "SPELL", "发现一张法术牌。"),
            ("S", "测试召唤", "SPELL", "召唤一个1/1的随从。"),
            ("B", "测试强化", "SPELL", "使一个随从获得+1/+1。"),
            ("U", "测试独特", "MINION", "你的英雄免疫。"),
        ]
        for card_id, name, card_type, source_text in samples:
            store.upsert_card(
                card_id,
                name,
                source_text,
                card_set="CORE",
                card_class="NEUTRAL",
                card_type=card_type,
                cost=1,
                source_version="test",
            )

        report = build_core_batch_report(store)
        batches = report["batches"]
        assigned = [card["card_id"] for batch in batches for card in batch["cards"]]
        assert report["remaining_card_count"] == len(samples)
        assert len(batches) == len(CATEGORIES)
        assert len(assigned) == len(set(assigned)) == len(samples)

