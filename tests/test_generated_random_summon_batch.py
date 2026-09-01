from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.random_summon_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    TOKEN_CARDS,
    build_review_scenario,
)
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef

EXPECTED_CARD_IDS = {
    "CORE_AT_062",
    "CORE_NEW1_031",
    "CORE_OG_211",
    "CORE_BOT_256",
    "CORE_WW_374",
    "CORE_LOOT_309",
}


def _document(card_id: str) -> dict[str, object]:
    metadata = AUTHORING_METADATA[card_id]
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": card_id,
            "name_zh": metadata["name_zh"],
            "source_text_zh": metadata["source_text_zh"],
            "source_version": metadata["source_version"],
        },
        "implementation": {
            "card_module": "src/cardlab/authoring/generated/random_summon_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=23, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(116_000, card_id)]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_random_summon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("random_summon_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    assert scenario["special_cases"]
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "召唤" in rendered


def test_ball_of_spiders_summons_three_independent_webspinners() -> None:
    game, actor, _ = _game("CORE_AT_062")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 116_000))
    spiders = [minion for minion in own.board if minion.card_id == "CORE_FP1_011"]
    assert len(spiders) == 3
    assert len({minion.entity_id for minion in spiders}) == 3
    assert all((minion.attack, minion.health, minion.races) == (1, 1, ("BEAST",)) for minion in spiders)


def test_webspinner_deathrattle_generates_a_registered_collectible_beast() -> None:
    game, actor, _ = _game("CORE_AT_062")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 116_000))
    spider = own.board[0]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, spider.entity_id)))
    assert [card.card_id for card in own.hand] == ["CS2_120"]


def test_animal_companion_uses_only_the_three_companion_tokens() -> None:
    game, actor, _ = _game("CORE_NEW1_031")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 116_000))
    assert len(own.board) == 1
    assert own.board[0].card_id in {"NEW1_032", "NEW1_033", "NEW1_034"}


def test_call_of_the_wild_summons_all_companions_and_applies_leokk_aura() -> None:
    game, actor, _ = _game("CORE_OG_211")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 116_000))
    assert [minion.card_id for minion in own.board] == [
        "NEW1_032",
        "NEW1_033",
        "NEW1_034",
    ]
    assert [minion.attack for minion in own.board] == [5, 2, 5]
    assert own.board[0].taunt is True
    assert own.board[2].charge is True


def test_astromancer_reads_hand_count_after_it_leaves_the_hand() -> None:
    game, actor, _ = _game("CORE_BOT_256")
    own = game.state.players[actor]
    own.hand.extend(HandCard(116_010 + index, "CS2_231") for index in range(6))
    game.apply(Action(ActionType.PLAY, 116_000))
    assert [minion.card_id for minion in own.board] == ["CORE_BOT_256", "CS2_200"]


def test_coldfeet_farm_spends_up_to_eight_corpses_and_summons_matching_cost() -> None:
    game, actor, _ = _game("CORE_WW_374")
    own = game.state.players[actor]
    own.corpses = 4
    game.apply(Action(ActionType.PLAY, 116_000))
    assert own.corpses == 0
    assert len(own.board) == 1
    assert game.cards[own.board[0].card_id].cost == 4


def test_oaken_summons_only_an_eligible_minion_from_deck() -> None:
    game, actor, _ = _game("CORE_LOOT_309")
    own = game.state.players[actor]
    own.deck = ["CS2_200", "CS2_120"]
    game.apply(Action(ActionType.PLAY, 116_000))
    assert own.hero_armor == 6
    assert own.deck == ["CS2_200"]
    assert [minion.card_id for minion in own.board] == ["CS2_120"]


def test_oaken_does_not_remove_a_deck_card_when_the_board_is_full() -> None:
    game, actor, _ = _game("CORE_LOOT_309")
    own = game.state.players[actor]
    own.deck = ["CS2_120"]
    own.board = [
        Minion(116_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(7)
    ]
    game.apply(Action(ActionType.PLAY, 116_000))
    assert own.deck == ["CS2_120"]
    assert len(own.board) == 7
