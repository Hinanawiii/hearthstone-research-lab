from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.deathrattle_batch import (
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
from cardlab.model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    HandCard,
    Minion,
    TargetRef,
    Weapon,
)

EXPECTED_CARD_IDS = {
    "CORE_AV_337",
    "CORE_BAR_310",
    "CORE_DMF_067",
    "CORE_DRG_107",
    "CORE_EX1_096",
    "CORE_EX1_110",
    "CORE_EX1_383",
    "CORE_LOOT_368",
    "CORE_LOOT_413",
    "CORE_OG_031",
    "CORE_RLK_657",
    "CORE_SW_068",
    "CORE_WC_701",
    "RLK_223",
    "RLK_708",
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
            "card_module": "src/cardlab/authoring/generated/deathrattle_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _dying_minion_game(card_id: str) -> tuple[Game, int]:
    game = Game(card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    card = CARDS[card_id]
    own.board = [
        Minion(
            106_000,
            card_id,
            card.attack,
            1,
            card.health,
            taunt=card.taunt,
            races=card.races,
            summoned_turn=0,
        )
    ]
    return game, actor


def _kill_with_hero_power(game: Game, actor: int, entity_id: int = 106_000) -> None:
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, entity_id)))


def test_deathrattle_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("deathrattle_batch.py")
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
    assert "亡语" in rendered


def test_loot_hoarder_draws_after_leaving_the_board() -> None:
    game, actor = _dying_minion_game("CORE_EX1_096")
    own = game.state.players[actor]
    own.deck = ["CS2_120", "CS2_172"]
    _kill_with_hero_power(game, actor)
    assert not own.board
    assert [card.card_id for card in own.hand] == ["CS2_172"]
    assert own.deck == ["CS2_120"]


def test_spellwing_adds_arcane_missiles_without_drawing_from_deck() -> None:
    game, actor = _dying_minion_game("CORE_DRG_107")
    own = game.state.players[actor]
    own.deck = ["CS2_120"]
    _kill_with_hero_power(game, actor)
    assert [card.card_id for card in own.hand] == ["EX1_277"]
    assert own.deck == ["CS2_120"]


def test_prize_vendor_battlecry_and_deathrattle_each_draw_for_both_players() -> None:
    game = Game(card_registry=runtime_registry(["CORE_DMF_067"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(106_010, "CORE_DMF_067")]
    own.deck = ["CS2_120", "CS2_172"]
    opposing.hand = []
    opposing.deck = ["CS2_120", "CS2_182"]
    game.apply(Action(ActionType.PLAY, 106_010))
    vendor = next(minion for minion in own.board if minion.card_id == "CORE_DMF_067")
    vendor.health = 1
    _kill_with_hero_power(game, actor, vendor.entity_id)
    assert [card.card_id for card in own.hand] == ["CS2_172", "CS2_120"]
    assert [card.card_id for card in opposing.hand] == ["CS2_182", "CS2_120"]
    assert not own.deck and not opposing.deck


def test_chillfallen_baron_draws_on_battlecry_and_deathrattle() -> None:
    game = Game(card_registry=runtime_registry(["RLK_708"]))
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(106_020, "RLK_708")]
    own.deck = ["CS2_120", "CS2_172"]
    game.apply(Action(ActionType.PLAY, 106_020))
    baron = next(minion for minion in own.board if minion.card_id == "RLK_708")
    baron.health = 1
    _kill_with_hero_power(game, actor, baron.entity_id)
    assert [card.card_id for card in own.hand] == ["CS2_172", "CS2_120"]


@pytest.mark.parametrize(
    ("card_id", "armor"),
    [("CORE_LOOT_413", 3), ("CORE_SW_068", 8)],
)
def test_armor_deathrattles_resolve_once(card_id: str, armor: int) -> None:
    game, actor = _dying_minion_game(card_id)
    _kill_with_hero_power(game, actor)
    assert game.state.players[actor].hero_armor == armor


def test_lightshower_heals_surviving_friendly_characters_but_not_itself() -> None:
    game, actor = _dying_minion_game("CORE_BAR_310")
    own = game.state.players[actor]
    own.hero_health = 12
    own.board.append(Minion(106_001, "CS2_120", 2, 1, 3, summoned_turn=0))
    _kill_with_hero_power(game, actor)
    assert own.hero_health == 20
    assert [(minion.card_id, minion.health) for minion in own.board] == [
        ("CS2_120", 3)
    ]


def test_underking_gains_armor_on_battlecry_and_deathrattle() -> None:
    game = Game(card_registry=runtime_registry(["CORE_RLK_657"]))
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(106_030, "CORE_RLK_657")]
    game.apply(Action(ActionType.PLAY, 106_030))
    underking = next(minion for minion in own.board if minion.card_id == "CORE_RLK_657")
    assert own.hero_armor == 6
    underking.health = 1
    _kill_with_hero_power(game, actor, underking.entity_id)
    assert own.hero_armor == 12


def test_felrattler_deathrattle_damages_all_enemy_minions_and_cleans_deaths() -> None:
    game, actor = _dying_minion_game("CORE_WC_701")
    enemy = 1 - actor
    opposing = game.state.players[enemy]
    opposing.board = [
        Minion(106_040, "CS2_120", 2, 1, 3, summoned_turn=0),
        Minion(106_041, "CS2_182", 4, 5, 5, summoned_turn=0),
    ]
    _kill_with_hero_power(game, actor)
    assert [(minion.card_id, minion.health) for minion in opposing.board] == [
        ("CS2_182", 4)
    ]


def test_thassarian_uses_random_enemy_damage_on_battlecry_and_deathrattle() -> None:
    game = Game(card_registry=runtime_registry(["RLK_223"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(106_050, "RLK_223")]
    opposing.board = []
    game.apply(Action(ActionType.PLAY, 106_050))
    thassarian = next(minion for minion in own.board if minion.card_id == "RLK_223")
    assert opposing.hero_health == 28
    thassarian.health = 1
    _kill_with_hero_power(game, actor, thassarian.entity_id)
    assert opposing.hero_health == 26
    assert len(own.board) == 1
    reborn_copy = own.board[0]
    assert (reborn_copy.card_id, reborn_copy.health, reborn_copy.reborn) == (
        "RLK_223",
        1,
        False,
    )


def test_cairne_summons_a_fresh_baine_after_leaving_the_board() -> None:
    game, actor = _dying_minion_game("CORE_EX1_110")
    _kill_with_hero_power(game, actor)
    assert [
        (minion.card_id, minion.attack, minion.health, minion.max_health)
        for minion in game.state.players[actor].board
    ] == [("EX1_110t", 5, 5, 5)]


def test_mountain_bear_summons_two_taunt_beast_cubs() -> None:
    game, actor = _dying_minion_game("CORE_AV_337")
    _kill_with_hero_power(game, actor)
    assert [
        (minion.card_id, minion.attack, minion.health, minion.taunt, minion.races)
        for minion in game.state.players[actor].board
    ] == [
        ("AV_337t", 2, 4, True, ("BEAST",)),
        ("AV_337t", 2, 4, True, ("BEAST",)),
    ]


def test_tirion_deathrattle_equips_ashbringer() -> None:
    game, actor = _dying_minion_game("CORE_EX1_383")
    _kill_with_hero_power(game, actor)
    own = game.state.players[actor]
    assert CARDS["CORE_EX1_383"].divine_shield is True
    assert own.weapon is not None
    assert (own.weapon.card_id, own.weapon.attack, own.weapon.durability) == (
        "EX1_383t",
        5,
        3,
    )
    assert own.hero_attack == 5


def test_voidlord_deathrattle_uses_space_opened_by_its_own_death() -> None:
    game, actor = _dying_minion_game("CORE_LOOT_368")
    own = game.state.players[actor]
    own.board.extend(
        Minion(106_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(6)
    )
    _kill_with_hero_power(game, actor)
    assert len(own.board) == 7
    voidwalkers = [minion for minion in own.board if minion.card_id == "CS2_065"]
    assert len(voidwalkers) == 1
    assert voidwalkers[0].taunt and voidwalkers[0].races == ("DEMON",)


def test_hammer_deathrattle_triggers_when_last_durability_is_spent() -> None:
    game = Game(card_registry=runtime_registry(["CORE_OG_031"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.weapon = Weapon(106_200, "CORE_OG_031", 4, 1)
    own.hero_attack = 4
    game.state.players[enemy].board = [
        Minion(106_201, "CS2_182", 0, 5, 5, summoned_turn=0)
    ]
    game.apply(
        Action(
            ActionType.HERO_ATTACK,
            106_200,
            TargetRef.minion(enemy, 106_201),
        )
    )
    assert own.weapon is None
    assert [(minion.card_id, minion.attack, minion.health) for minion in own.board] == [
        ("OG_031a", 4, 2)
    ]


def test_replacing_hammer_triggers_its_deathrattle_before_equipping_new_weapon() -> None:
    registry = runtime_registry(["CORE_OG_031"])
    registry["TEST_WEAPON"] = CardDef(
        "TEST_WEAPON", "测试武器", CardType.WEAPON, 1, attack=1, durability=2
    )
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.weapon = Weapon(106_300, "CORE_OG_031", 4, 2)
    own.hero_attack = 4
    own.hand = [HandCard(106_301, "TEST_WEAPON")]
    game.apply(Action(ActionType.PLAY, 106_301))
    assert own.weapon is not None and own.weapon.card_id == "TEST_WEAPON"
    assert [minion.card_id for minion in own.board] == ["OG_031a"]
