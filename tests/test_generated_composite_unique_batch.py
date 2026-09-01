from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import generated_dependencies, runtime_registry
from cardlab.authoring.generated.composite_unique_batch import (
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
    "CORE_BT_156",
    "CORE_EX1_058",
    "CORE_SCH_605",
    "CORE_ULD_178",
    "CS3_035",
    "CORE_WON_145",
    "CORE_CATA_004",
    "CORE_EX1_323",
    "CORE_BT_120",
}


def _game(*card_ids: str) -> tuple[Game, int, int]:
    game = Game(seed=83, card_registry=runtime_registry(card_ids))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"] * 10
    opposing.deck = ["CS2_120"] * 10
    return game, actor, enemy


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
            "card_module": "src/cardlab/authoring/generated/composite_unique_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_composite_unique_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    assert {"EX1_323w", "EX1_tk34"} <= set(generated_dependencies("CORE_EX1_323"))
    assert "CORE_EX1_238" in generated_dependencies("CORE_CATA_004")
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("composite_unique_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert document["scenario"]["assertions"]


def test_dormant_minion_is_untargetable_then_wakes_with_rush() -> None:
    game, actor, enemy = _game("CORE_BT_156")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [HandCard(260_000, "CORE_BT_156")]
    opposing.board = [Minion(260_001, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 260_000))
    dormant = own.board[0]
    assert dormant.dormant_turns_remaining == 2
    assert TargetRef.minion(actor, dormant.entity_id) not in game._valid_targets(
        actor, CARDS["CORE_BT_120"].target_mode
    )

    game.apply(Action.end_turn())
    game.apply(Action.end_turn())
    assert dormant.dormant_turns_remaining == 1
    game.apply(Action.end_turn())
    game.apply(Action.end_turn())
    assert dormant.dormant_turns_remaining == 0
    assert (
        Action(ActionType.ATTACK, dormant.entity_id, TargetRef.minion(enemy, 260_001))
        in game.legal_actions()
    )


def test_sunfury_uses_explicit_board_position_and_buffs_both_neighbors() -> None:
    game, actor, _ = _game("CORE_EX1_058")
    own = game.state.players[actor]
    own.board = [
        Minion(260_010, "CS2_120", 2, 3, 3, summoned_turn=0),
        Minion(260_011, "CS2_182", 4, 5, 5, summoned_turn=0),
    ]
    own.hand = [HandCard(260_012, "CORE_EX1_058")]
    action = Action(ActionType.PLAY, 260_012, position=1)
    assert action in game.legal_actions()
    game.apply(action)
    assert [minion.card_id for minion in own.board] == [
        "CS2_120",
        "CORE_EX1_058",
        "CS2_182",
    ]
    assert own.board[0].taunt and own.board[2].taunt
    assert not own.board[1].taunt


def test_lake_thresher_damages_both_adjacent_defenders_without_retaliation() -> None:
    game, actor, enemy = _game("CORE_SCH_605")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(260_020, "CORE_SCH_605", 4, 6, 6, summoned_turn=0)]
    opposing.board = [
        Minion(260_021, "CS2_120", 1, 5, 5, summoned_turn=0),
        Minion(260_022, "CS2_120", 1, 5, 5, summoned_turn=0),
        Minion(260_023, "CS2_120", 1, 5, 5, summoned_turn=0),
    ]
    game.apply(Action(ActionType.ATTACK, 260_020, TargetRef.minion(enemy, 260_022)))
    assert [minion.health for minion in opposing.board] == [1, 1, 1]
    assert own.board[0].health == 5


def test_siamat_choice_grants_exactly_two_keywords() -> None:
    game, actor, _ = _game("CORE_ULD_178")
    own = game.state.players[actor]
    own.hand = [HandCard(260_030, "CORE_ULD_178")]
    choices = [
        action
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 260_030
    ]
    assert len(choices) == 6
    game.apply(Action(ActionType.PLAY, 260_030, choice=2))
    siamat = own.board[0]
    assert siamat.rush and siamat.windfury
    assert not siamat.taunt and not siamat.divine_shield


def test_nozdormu_requires_both_starting_decks() -> None:
    registry = runtime_registry(["CS3_035"])
    both = Game(
        seed=89,
        decks=(["CS3_035"] + ["CS2_120"] * 5, ["CS3_035"] + ["CS2_120"] * 5),
        card_registry=registry,
    )
    one = Game(
        seed=89,
        decks=(["CS3_035"] + ["CS2_120"] * 5, ["CS2_120"] * 6),
        card_registry=registry,
    )
    assert both.state.turn_time_limit_seconds == 15
    assert one.state.turn_time_limit_seconds == 0


def test_avatar_opens_five_registered_cards_and_plays_them_for_free() -> None:
    game, actor, _ = _game("CORE_WON_145")
    own = game.state.players[actor]
    own.hand = [HandCard(260_040, "CORE_WON_145")]
    own.mana = 9
    game.apply(Action(ActionType.PLAY, 260_040))
    assert len(own.last_pack_card_ids) == 5
    assert len(set(own.last_pack_card_ids)) == 5
    assert own.cards_played_this_turn == 6
    assert own.mana == 0


def test_rehgar_generates_lightning_bolt_after_self_or_adjacent_attack() -> None:
    game, actor, enemy = _game("CORE_CATA_004")
    own = game.state.players[actor]
    own.board = [
        Minion(260_050, "CS2_120", 2, 3, 3, summoned_turn=0),
        Minion(260_051, "CORE_CATA_004", 3, 5, 5, summoned_turn=0),
        Minion(260_052, "CS2_182", 4, 5, 5, summoned_turn=0),
    ]
    game.apply(Action(ActionType.ATTACK, 260_050, TargetRef.hero(enemy)))
    assert [card.card_id for card in own.hand] == ["CORE_EX1_238"]


def test_jaraxxus_equips_weapon_gains_armor_and_replaces_hero_power() -> None:
    game, actor, _ = _game("CORE_EX1_323")
    own = game.state.players[actor]
    own.hand = [HandCard(260_060, "CORE_EX1_323")]
    game.apply(Action(ActionType.PLAY, 260_060))
    assert own.hero_armor == 5
    assert own.weapon is not None
    assert (own.weapon.card_id, own.weapon.attack, own.weapon.durability) == (
        "EX1_323w",
        3,
        8,
    )
    assert own.hero_power_kind == "summon_infernal"
    own.mana = 2
    game.apply(Action(ActionType.HERO_POWER))
    assert own.board[0].card_id == "EX1_tk34"


def test_warmaul_challenger_repeats_combat_until_one_minion_dies() -> None:
    game, actor, enemy = _game("CORE_BT_120")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [HandCard(260_070, "CORE_BT_120")]
    opposing.board = [Minion(260_071, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 260_070, TargetRef.minion(enemy, 260_071)))
    assert opposing.board == []
    assert len(own.board) == 1
    assert own.board[0].card_id == "CORE_BT_120"
    assert own.board[0].health == 4
