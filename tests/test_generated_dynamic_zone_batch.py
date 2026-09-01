from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.dynamic_zone_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
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
    "CORE_AT_123",
    "CORE_EX1_014",
    "CORE_EX1_198",
    "CORE_EX1_246",
    "CORE_EX1_310",
    "CORE_ICC_214",
    "CORE_ICC_407",
    "CORE_RLK_063",
    "CORE_RLK_087",
    "CORE_SCH_512",
    "CORE_SW_108",
    "CORE_TRL_900",
    "CORE_TSC_076",
    "CORE_ULD_165",
    "CORE_ULD_280",
    "CORE_UNG_809",
    "CS3_024",
    "RLK_511",
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
            "card_module": "src/cardlab/authoring/generated/dynamic_zone_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=7, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 20
    own.mana = own.max_mana = 10
    own.hand = [HandCard(111_000, card_id)]
    own.board = []
    opposing.hand = []
    opposing.board = [
        Minion(111_001, "CS2_182", 4, 6, 6, summoned_turn=0),
        Minion(111_002, "CS2_231", 1, 1, 1, summoned_turn=0),
    ]
    return game, actor, enemy


def _kill_fixture(game: Game, actor: int, card_id: str, entity_id: int = 111_100) -> None:
    card = CARDS[card_id]
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.board = [
        Minion(
            entity_id,
            card_id,
            card.attack,
            1,
            card.health,
            taunt=card.taunt,
            lifesteal=card.lifesteal,
            races=card.races,
            summoned_turn=0,
        )
    ]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, entity_id)))


def test_dynamic_zone_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("dynamic_zone_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "操作前" in rendered and "操作后" in rendered


def test_asphyxiate_destroys_only_the_highest_attack_enemy() -> None:
    game, _, enemy = _game("CORE_RLK_087")
    game.apply(Action(ActionType.PLAY, 111_000))
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_231"]


def test_natalie_gains_the_destroyed_minions_current_health() -> None:
    game, actor, enemy = _game("CORE_EX1_198")
    game.apply(Action(ActionType.PLAY, 111_000, TargetRef.minion(enemy, 111_001)))
    natalie = game.state.players[actor].board[0]
    assert (natalie.attack, natalie.health, natalie.max_health) == (7, 7, 7)
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_231"]


def test_riftcleaver_damages_hero_by_destroyed_minions_current_health() -> None:
    game, actor, enemy = _game("CORE_ULD_165")
    game.apply(Action(ActionType.PLAY, 111_000, TargetRef.minion(enemy, 111_001)))
    assert game.state.players[actor].hero_health == 14
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_231"]


def test_initiation_summons_a_fresh_copy_only_when_damage_is_lethal() -> None:
    game, actor, enemy = _game("CORE_SCH_512")
    game.apply(Action(ActionType.PLAY, 111_000, TargetRef.minion(enemy, 111_002)))
    assert [(minion.card_id, minion.health) for minion in game.state.players[actor].board] == [
        ("CS2_231", 1)
    ]
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_182"]


def test_obsidian_statue_deathrattle_destroys_the_only_enemy_minion() -> None:
    game, actor, enemy = _game("CORE_ICC_214")
    game.state.players[enemy].board = [game.state.players[enemy].board[0]]
    _kill_fixture(game, actor, "CORE_ICC_214")
    assert game.state.players[enemy].board == []


def test_sahket_sapper_returns_the_only_enemy_minion_to_hand() -> None:
    game, actor, enemy = _game("CORE_ULD_280")
    opposing = game.state.players[enemy]
    opposing.board = [opposing.board[0]]
    _kill_fixture(game, actor, "CORE_ULD_280")
    assert opposing.board == []
    assert [card.card_id for card in opposing.hand] == ["CS2_182"]


def test_chillmaw_only_deals_aoe_while_owner_holds_a_dragon() -> None:
    game, actor, enemy = _game("CORE_AT_123")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = []
    _kill_fixture(game, actor, "CORE_AT_123")
    assert [(minion.card_id, minion.health) for minion in opposing.board] == [
        ("CS2_182", 6),
        ("CS2_231", 1),
    ]

    game, actor, enemy = _game("CORE_AT_123")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [HandCard(111_110, "RLK_063t")]
    _kill_fixture(game, actor, "CORE_AT_123")
    assert [(minion.card_id, minion.health) for minion in opposing.board] == [("CS2_182", 3)]


def test_taelan_draws_highest_cost_minion() -> None:
    game, actor, _ = _game("CS3_024")
    own = game.state.players[actor]
    own.hand = []
    own.deck = ["CS2_120", "CS2_200", "CS2_172"]
    _kill_fixture(game, actor, "CS3_024")
    assert [card.card_id for card in own.hand] == ["CS2_200"]
    assert own.deck == ["CS2_120", "CS2_172"]


def test_harbinger_draws_frost_spell_and_skips_non_frost_cards() -> None:
    registry = runtime_registry(["RLK_511", "CORE_CS2_024"])
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.hand = []
    own.deck = ["CS2_029", "CORE_CS2_024"]
    _kill_fixture(game, actor, "RLK_511")
    assert [card.card_id for card in own.hand] == ["CORE_CS2_024"]
    assert own.deck == ["CS2_029"]


def test_frostwyrms_fury_runs_damage_freeze_and_summon_steps() -> None:
    game, actor, enemy = _game("CORE_RLK_063")
    opposing = game.state.players[enemy]
    game.apply(Action(ActionType.PLAY, 111_000, TargetRef.hero(enemy)))
    assert opposing.hero_health == 25
    assert all(minion.frozen for minion in opposing.board)
    assert [
        (minion.card_id, minion.attack, minion.health) for minion in game.state.players[actor].board
    ] == [("RLK_063t", 5, 5)]


def test_immortalized_in_stone_respects_sequence_and_board_limit() -> None:
    game, actor, _ = _game("CORE_TSC_076")
    own = game.state.players[actor]
    own.board = [Minion(111_200 + index, "CS2_120", 2, 3, 3, summoned_turn=0) for index in range(5)]
    game.apply(Action(ActionType.PLAY, 111_000))
    assert [minion.card_id for minion in own.board[-2:]] == ["TSC_076t3", "TSC_076t2"]
    assert len(own.board) == 7


def test_hex_resets_card_stats_and_keywords_but_preserves_entity_id() -> None:
    game, _, enemy = _game("CORE_EX1_246")
    target = game.state.players[enemy].board[0]
    target.divine_shield = True
    game.apply(Action(ActionType.PLAY, 111_000, TargetRef.minion(enemy, 111_001)))
    assert target.entity_id == 111_001
    assert (target.card_id, target.attack, target.health, target.taunt, target.divine_shield) == (
        "hexfrog",
        0,
        1,
        True,
        False,
    )


def test_doomguard_discards_only_cards_remaining_after_it_is_played() -> None:
    game, actor, _ = _game("CORE_EX1_310")
    own = game.state.players[actor]
    own.hand.extend([HandCard(111_300, "CS2_120"), HandCard(111_301, "CS2_172")])
    game.apply(Action(ActionType.PLAY, 111_000))
    assert own.hand == []
    assert own.board[0].card_id == "CORE_EX1_310" and own.board[0].charge


def test_gnomeferatu_removes_top_deck_card_without_drawing_it() -> None:
    game, _, enemy = _game("CORE_ICC_407")
    opposing = game.state.players[enemy]
    opposing.deck = ["CS2_120", "CS2_172"]
    game.apply(Action(ActionType.PLAY, 111_000))
    assert opposing.deck == ["CS2_120"]
    assert opposing.hand == []


def test_mukla_respects_opponent_hand_limit_when_giving_bananas() -> None:
    game, _, enemy = _game("CORE_EX1_014")
    opposing = game.state.players[enemy]
    opposing.hand = [HandCard(111_400 + index, "CS2_120") for index in range(9)]
    game.apply(Action(ActionType.PLAY, 111_000))
    assert len(opposing.hand) == 10
    assert sum(card.card_id == "EX1_014t" for card in opposing.hand) == 1


@pytest.mark.parametrize(
    ("card_id", "generated_card_id"),
    [("CORE_UNG_809", "UNG_809t1"), ("CORE_SW_108", "SW_108t")],
)
def test_fixed_card_generation_adds_playable_card_to_hand(
    card_id: str, generated_card_id: str
) -> None:
    game, actor, enemy = _game(card_id)
    target = TargetRef.minion(enemy, 111_001) if card_id == "CORE_SW_108" else None
    game.apply(Action(ActionType.PLAY, 111_000, target))
    assert [card.card_id for card in game.state.players[actor].hand] == [generated_card_id]


def test_halazzi_fills_hand_with_rush_lynxes() -> None:
    game, actor, _ = _game("CORE_TRL_900")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 111_000))
    assert len(own.hand) == 10
    assert all(card.card_id == "TRL_348t" for card in own.hand)
    assert runtime_registry([])["TRL_348t"].rush is True
