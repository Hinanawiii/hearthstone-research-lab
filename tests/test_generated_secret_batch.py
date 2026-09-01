from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import generated_dependencies, runtime_registry
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
)
from cardlab.authoring.generated.secret_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    TOKEN_CARDS,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef

EXPECTED_CARD_IDS = {
    "CORE_EX1_610",
    "CORE_EX1_611",
    "CORE_GIL_577",
    "CORE_ULD_152",
    "CORE_BAR_812",
    "CORE_EX1_287",
    "CORE_EX1_289",
    "CORE_LOOT_101",
}


def _game(*card_ids: str) -> tuple[Game, int, int]:
    game = Game(seed=71, card_registry=runtime_registry(card_ids))
    owner = game.state.active_player
    opponent = 1 - owner
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = []
    opposing.deck = []
    return game, owner, opponent


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
            "card_module": "src/cardlab/authoring/generated/secret_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_secret_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    assert "GIL_577t" in generated_dependencies("CORE_GIL_577")
    assert "CS2_033" in generated_dependencies("CORE_BAR_812")
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("secret_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_secret_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert document["scenario"]["assertions"]


def test_playing_a_secret_arms_hidden_zone_and_prevents_duplicate() -> None:
    game, owner, opponent = _game("CORE_EX1_610")
    own = game.state.players[owner]
    own.hand = [HandCard(240_000, "CORE_EX1_610"), HandCard(240_001, "CORE_EX1_610")]
    game.apply(Action(ActionType.PLAY, 240_000))
    assert own.secrets == ["CORE_EX1_610"]
    assert not any(action.source_id == 240_001 for action in game.legal_actions())
    assert game.observation(owner)["own"]["secrets"] == ["CORE_EX1_610"]
    assert game.observation(opponent)["enemy"]["secrets"] == ["未知奥秘"]


def test_explosive_trap_resolves_before_combat_and_can_cancel_attack() -> None:
    game, owner, opponent = _game("CORE_EX1_610")
    game.state.players[owner].secrets = ["CORE_EX1_610"]
    game.state.players[opponent].board = [Minion(240_010, "CS2_120", 3, 2, 2, summoned_turn=0)]
    game.state.active_player = opponent
    game.state.turn = 1
    game.apply(Action(ActionType.ATTACK, 240_010, TargetRef.hero(owner)))
    assert game.state.players[owner].hero_health == 30
    assert game.state.players[opponent].hero_health == 28
    assert game.state.players[opponent].board == []


def test_freezing_trap_returns_attacker_with_plus_two_cost() -> None:
    game, owner, opponent = _game("CORE_EX1_611")
    game.state.players[owner].secrets = ["CORE_EX1_611"]
    opposing = game.state.players[opponent]
    opposing.board = [Minion(240_020, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.state.active_player = opponent
    game.state.turn = 1
    game.apply(Action(ActionType.ATTACK, 240_020, TargetRef.hero(owner)))
    assert opposing.board == []
    assert [(card.card_id, card.cost_modifier) for card in opposing.hand] == [("CS2_120", 2)]
    assert game.state.players[owner].hero_health == 30


def test_rat_trap_triggers_only_after_the_third_card() -> None:
    game, owner, opponent = _game("CORE_GIL_577")
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.secrets = ["CORE_GIL_577"]
    opposing.cards_played_this_turn = 2
    opposing.hand = [HandCard(240_030, "GAME_005")]
    game.state.active_player = opponent
    game.apply(Action(ActionType.PLAY, 240_030))
    assert own.secrets == []
    assert [(m.card_id, m.attack, m.health) for m in own.board] == [("GIL_577t", 6, 6)]


def test_pressure_plate_waits_for_a_valid_enemy_minion() -> None:
    game, owner, opponent = _game("CORE_ULD_152")
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.secrets = ["CORE_ULD_152"]
    opposing.hand = [HandCard(240_040, "EX1_277")]
    game.state.active_player = opponent
    game.apply(Action(ActionType.PLAY, 240_040))
    assert own.secrets == ["CORE_ULD_152"]

    opposing.board = [Minion(240_041, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.hand = [HandCard(240_042, "EX1_277")]
    opposing.mana = 10
    game.apply(Action(ActionType.PLAY, 240_042))
    assert own.secrets == []
    assert opposing.board == []


def test_oasis_ally_summons_before_friendly_minion_combat() -> None:
    game, owner, opponent = _game("CORE_BAR_812")
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.secrets = ["CORE_BAR_812"]
    own.board = [Minion(240_050, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [Minion(240_051, "CS2_120", 1, 3, 3, summoned_turn=0)]
    game.state.active_player = opponent
    game.state.turn = 1
    game.apply(Action(ActionType.ATTACK, 240_051, TargetRef.minion(owner, 240_050)))
    assert [m.card_id for m in own.board] == ["CS2_120", "CS2_033"]
    assert own.secrets == []


def test_counterspell_spends_the_spell_but_skips_its_effect() -> None:
    game, owner, opponent = _game("CORE_EX1_287")
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.secrets = ["CORE_EX1_287"]
    opposing.hand = [HandCard(240_060, "CS2_029")]
    game.state.active_player = opponent
    game.apply(Action(ActionType.PLAY, 240_060, TargetRef.hero(owner)))
    assert own.hero_health == 30
    assert own.secrets == []
    assert opposing.mana == 6
    assert opposing.spells_played_this_turn == ["CS2_029"]


def test_ice_barrier_armor_is_present_before_attack_damage() -> None:
    game, owner, opponent = _game("CORE_EX1_289")
    own = game.state.players[owner]
    own.secrets = ["CORE_EX1_289"]
    game.state.players[opponent].board = [Minion(240_070, "CS2_120", 3, 3, 3, summoned_turn=0)]
    game.state.active_player = opponent
    game.state.turn = 1
    game.apply(Action(ActionType.ATTACK, 240_070, TargetRef.hero(owner)))
    assert own.hero_health == 30
    assert own.hero_armor == 5


def test_explosive_runes_deals_excess_damage_to_enemy_hero() -> None:
    game, owner, opponent = _game("CORE_LOOT_101")
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.secrets = ["CORE_LOOT_101"]
    opposing.hand = [HandCard(240_080, "CS2_120")]
    game.state.active_player = opponent
    game.apply(Action(ActionType.PLAY, 240_080))
    assert opposing.board == []
    assert opposing.hero_health == 27
    assert own.secrets == []
