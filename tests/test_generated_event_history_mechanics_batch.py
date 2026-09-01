from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import generated_dependencies, runtime_registry
from cardlab.authoring.generated.event_history_mechanics_batch import (
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
    "RLK_061",
    "CORE_RLK_121",
    "CORE_RLK_745",
    "RLK_720",
    "CORE_RLK_706",
    "CORE_BT_187",
    "CORE_TTN_866",
    "CORE_CATA_006",
    "CORE_EX1_012",
    "CORE_EX1_100",
    "CORE_ETC_111",
    "CORE_CFM_344",
    "CORE_SCH_717",
    "CORE_SW_047",
    "CORE_BAR_313",
    "CORE_CFM_781",
    "CORE_RLK_567",
    "CS3_007",
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
            "card_module": "src/cardlab/authoring/generated/event_history_mechanics_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=59, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    own.board = []
    game.state.players[enemy].hand = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_event_history_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    assert "RLK_061t" in generated_dependencies("RLK_061")
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("event_history_mechanics_batch.py")
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


def test_necromancer_spends_one_corpse_and_summons_no_corpse_token() -> None:
    game, actor, _ = _game("RLK_061")
    own = game.state.players[actor]
    own.corpses = 1
    own.board = [Minion(200_000, "RLK_061", 2, 2, 2, summoned_turn=0)]
    game.apply(Action.end_turn())
    assert own.corpses == 0
    assert [minion.card_id for minion in own.board] == ["RLK_061", "RLK_061t"]
    own.board[-1].health = 0
    game._cleanup_deaths()
    assert own.corpses == 0


def test_death_acolyte_draws_after_a_friendly_undead_dies() -> None:
    game, actor, _ = _game("CORE_RLK_121")
    own = game.state.players[actor]
    own.deck = ["CS2_120"]
    own.board = [
        Minion(200_010, "CORE_RLK_121", 2, 4, 4, summoned_turn=0),
        Minion(200_011, "CORE_EX1_012", 1, 1, 1, races=("UNDEAD",), summoned_turn=0),
    ]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 200_011)))
    assert [card.card_id for card in own.hand] == ["CS2_120"]


def test_horror_spends_four_corpses_and_summons_a_copy() -> None:
    game, actor, _ = _game("CORE_RLK_745")
    own = game.state.players[actor]
    own.corpses = 4
    own.board = [
        Minion(200_020, "CORE_RLK_745", 5, 7, 7, reborn=True, summoned_turn=0)
    ]
    game.apply(Action.end_turn())
    assert own.corpses == 0
    assert [(m.attack, m.health, m.reborn) for m in own.board] == [
        (5, 7, True),
        (5, 7, True),
    ]


def test_mograine_persistent_damage_survives_the_minion() -> None:
    game, actor, enemy = _game("CORE_RLK_706")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [HandCard(200_030, "CORE_RLK_706")]
    game.apply(Action(ActionType.PLAY, 200_030))
    own.board = []
    game.apply(Action.end_turn())
    assert opposing.hero_health == 27


def test_kayn_allows_friendly_attacks_to_ignore_taunt() -> None:
    game, actor, enemy = _game("CORE_BT_187")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [
        Minion(200_040, "CORE_BT_187", 3, 5, 5, charge=True, summoned_turn=0),
        Minion(200_041, "CS2_120", 2, 3, 3, summoned_turn=0),
    ]
    opposing.board = [
        Minion(200_042, "CS2_120", 2, 3, 3, taunt=True, summoned_turn=0),
        Minion(200_043, "CS2_120", 2, 3, 3, summoned_turn=0),
    ]
    assert Action(
        ActionType.ATTACK,
        200_041,
        TargetRef.minion(enemy, 200_043),
    ) in game.legal_actions()


def test_olfa_attaches_same_cost_deathrattle_to_other_minions() -> None:
    game, actor, _ = _game("CORE_CATA_006")
    own = game.state.players[actor]
    own.hand = [HandCard(200_050, "CORE_CATA_006")]
    own.board = [Minion(200_051, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 200_050))
    assert own.board[0].attached_deathrattle_effects[0].kind == (
        "summon_random_same_cost_as_source_snapshot"
    )


def test_spell_damage_and_thalnos_deathrattle_both_apply() -> None:
    game = Game(
        seed=61,
        card_registry=runtime_registry(["CORE_EX1_012", "CORE_CS2_029"]),
    )
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(200_060, "CORE_CS2_029")]
    own.board = [
        Minion(200_061, "CORE_EX1_012", 1, 1, 1, races=("UNDEAD",), summoned_turn=0)
    ]
    game.apply(Action(ActionType.PLAY, 200_060, TargetRef.hero(enemy)))
    assert game.state.players[enemy].hero_health == 23


def test_cho_copies_any_players_spell_to_the_other_player() -> None:
    game, actor, enemy = _game("CORE_EX1_100")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(200_070, "CORE_EX1_100", 0, 4, 4, summoned_turn=0)]
    own.hand = [HandCard(200_071, "CS2_029")]
    game.apply(Action(ActionType.PLAY, 200_071, TargetRef.hero(enemy)))
    assert [card.card_id for card in opposing.hand] == ["CS2_029"]


def test_finja_summons_two_murlocs_after_attack_kill() -> None:
    game, actor, enemy = _game("CORE_CFM_344")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(200_080, "CORE_CFM_344", 3, 5, 5, summoned_turn=0)]
    own.deck = ["CORE_EX1_506", "CORE_DMF_067"]
    opposing.board = [Minion(200_081, "CS2_120", 1, 3, 3, summoned_turn=0)]
    game.apply(
        Action(ActionType.ATTACK, 200_080, TargetRef.minion(enemy, 200_081))
    )
    assert len(own.board) == 3
    assert own.deck == []


def test_alabaster_copies_opponent_draw_at_one_cost() -> None:
    game, actor, enemy = _game("CORE_SCH_717")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(200_090, "CORE_SCH_717", 6, 8, 8, summoned_turn=0)]
    opposing.deck = ["CS2_182"]
    game.apply(Action.end_turn())
    assert [(card.card_id, card.cost_modifier) for card in own.hand] == [
        ("CS2_182", -3)
    ]


def test_fordragon_buffs_a_hand_minion_when_friendly_shield_is_lost() -> None:
    game, actor, _ = _game("CORE_SW_047")
    own = game.state.players[actor]
    own.board = [
        Minion(200_100, "CORE_SW_047", 5, 5, 5, divine_shield=True, summoned_turn=0),
        Minion(200_101, "CS2_120", 2, 3, 3, divine_shield=True, summoned_turn=0),
    ]
    own.hand = [HandCard(200_102, "CS2_120")]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 200_101)))
    assert (own.hand[0].attack_bonus, own.hand[0].health_bonus) == (5, 5)


def test_shadow_of_demise_keeps_origin_and_transforms_after_spell() -> None:
    game, actor, enemy = _game("CORE_RLK_567")
    own = game.state.players[actor]
    own.hand = [
        HandCard(200_110, "CORE_RLK_567"),
        HandCard(200_111, "CS2_029"),
    ]
    game.apply(Action(ActionType.PLAY, 200_111, TargetRef.hero(enemy)))
    assert [(card.card_id, card.origin_card_id) for card in own.hand] == [
        ("CS2_029", "CORE_RLK_567")
    ]
