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
from cardlab.authoring.generated.special_zone_mechanics_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
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
    HandCard,
    Location,
    Minion,
    TargetRef,
)

EXPECTED_CARD_IDS = {
    "CORE_ETC_523",
    "CORE_BT_416",
    "CORE_CATA_001",
    "CORE_YOP_001",
    "CORE_OG_044",
    "CORE_ONY_018",
    "Core_LOE_115",
    "CORE_REV_308",
    "CORE_SCH_713",
    "CORE_DRG_403",
    "CORE_EDR_004_2026",
    "CORE_REV_023",
    "CORE_SW_066",
    "TTN_851",
    "CORE_KAR_077",
    "CORE_DMF_511",
    "CORE_EX1_145",
    "CORE_GIL_836",
    "CORE_CS2_053",
    "CORE_AV_107",
    "CORE_WON_096",
    "CORE_REV_990",
    "CORE_WON_337",
}


def _game(*card_ids: str) -> tuple[Game, int, int]:
    game = Game(seed=67, card_registry=runtime_registry(card_ids))
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
    own.deck = []
    opposing.deck = []
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
            "card_module": "src/cardlab/authoring/generated/special_zone_mechanics_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_special_zone_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert "CORE_BT_491" in generated_dependencies("CORE_YOP_001")
    assert "CORE_EX1_383" in generated_dependencies("CORE_AV_107")
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("special_zone_mechanics_batch.py")
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


def test_death_metal_knight_pays_health_after_real_healing() -> None:
    game, actor, _ = _game("CORE_ETC_523")
    own = game.state.players[actor]
    own.hero_health = 20
    own.healed_this_turn = True
    own.hand = [HandCard(220_000, "CORE_ETC_523")]
    game.apply(Action(ActionType.PLAY, 220_000))
    assert own.hero_health == 17
    assert own.mana == 10


def test_demon_discounts_are_consumed_at_the_correct_boundary() -> None:
    game, actor, _ = _game("CORE_BT_416", "CORE_CATA_001")
    own = game.state.players[actor]
    own.mana = own.max_mana = 20
    own.hand = [HandCard(220_010, "CORE_BT_416"), HandCard(220_011, "CORE_CATA_001")]
    game.apply(Action(ActionType.PLAY, 220_010))
    assert own.next_demon_discount == 2
    game.apply(Action(ActionType.PLAY, 220_011))
    assert own.mana == 9
    assert own.next_demon_discount == 0
    assert own.next_demon_cost_zero_this_turn


def test_illidari_studies_discovers_and_reduces_the_next_outcast_card() -> None:
    game, actor, _ = _game("CORE_YOP_001")
    own = game.state.players[actor]
    own.hand = [HandCard(220_020, "CORE_YOP_001")]
    game.apply(Action(ActionType.PLAY, 220_020))
    game.apply(Action(ActionType.DISCOVER, choice=0))
    discovered = own.hand[0]
    assert discovered.card_id == "CORE_BT_491"
    assert game._effective_card_cost(actor, discovered, game.cards[discovered.card_id]) == 1


def test_fandral_combines_both_furious_fowl_choices() -> None:
    game, actor, enemy = _game("CORE_OG_044", "CORE_ONY_018")
    own = game.state.players[actor]
    own.hero_health = 20
    own.board = [Minion(220_030, "CORE_OG_044", 3, 6, 6, summoned_turn=0)]
    own.hand = [HandCard(220_031, "CORE_ONY_018")]
    action = Action(ActionType.PLAY, 220_031, TargetRef.hero(enemy), -1)
    assert action in game.legal_actions()
    game.apply(action)
    assert own.hero_health == 28
    assert game.state.players[enemy].hero_health == 26


def test_raven_idol_queues_both_discovers_with_fandral() -> None:
    game, actor, _ = _game("CORE_OG_044", "Core_LOE_115")
    own = game.state.players[actor]
    own.board = [Minion(220_040, "CORE_OG_044", 3, 6, 6, summoned_turn=0)]
    own.hand = [HandCard(220_041, "Core_LOE_115")]
    game.apply(Action(ActionType.PLAY, 220_041, choice=-1))
    minion_choice = game.state.pending_discover_options.index("CS2_120")
    game.apply(Action(ActionType.DISCOVER, choice=minion_choice))
    spell_choice = game.state.pending_discover_options.index("CS2_029")
    game.apply(Action(ActionType.DISCOVER, choice=spell_choice))
    assert [card.card_id for card in own.hand] == ["CS2_120", "CS2_029"]


def test_spell_and_hero_power_taxes_expire_or_are_consumed() -> None:
    game, actor, enemy = _game("CORE_SCH_713", "CORE_DRG_403", "TTN_851")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [
        HandCard(220_050, "CORE_SCH_713"),
        HandCard(220_051, "CORE_DRG_403"),
    ]
    game.apply(Action(ActionType.PLAY, 220_050))
    game.apply(Action(ActionType.PLAY, 220_051))
    assert opposing.spell_tax_remaining_turns == 1
    assert opposing.next_hero_power_cost_increase == 2
    game.apply(Action.end_turn())
    hero_power = next(a for a in game.legal_actions() if a.action_type == ActionType.HERO_POWER)
    game.apply(hero_power)
    assert opposing.mana == 6
    assert opposing.next_hero_power_cost_increase == 0


def test_raptor_herald_marks_dark_gift_rewind_and_kindred_discount() -> None:
    game, actor, _ = _game("CORE_EDR_004_2026")
    own = game.state.players[actor]
    own.minion_types_played_previous_turn = ["BEAST"]
    own.hand = [HandCard(220_060, "CORE_EDR_004_2026")]
    game.apply(Action(ActionType.PLAY, 220_060))
    game.apply(Action(ActionType.DISCOVER, choice=0))
    discovered = own.hand[0]
    assert discovered.cost_modifier == -1
    assert discovered.special_tags == ("dark_gift", "rewind_eligible")


def test_destroy_location_silence_and_location_activation_are_explicit_actions() -> None:
    game, actor, enemy = _game("CORE_REV_023", "CORE_SW_066", "CORE_REV_990")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    opposing.locations = [Location(220_070, "CORE_REV_990", 3)]
    own.board = [Minion(220_071, "CS2_120", 5, 6, 6, taunt=True, summoned_turn=0)]
    own.hand = [HandCard(220_072, "CORE_REV_023"), HandCard(220_073, "CORE_SW_066")]
    game.apply(Action(ActionType.PLAY, 220_072, TargetRef(enemy, "location", 220_070)))
    assert opposing.locations == []
    game.apply(Action(ActionType.PLAY, 220_073, TargetRef.minion(actor, 220_071)))
    assert (own.board[0].attack, own.board[0].health, own.board[0].taunt) == (2, 3, False)

    own.locations = [Location(220_074, "CORE_REV_990", 3)]
    game.apply(Action(ActionType.LOCATION, 220_074, TargetRef.minion(actor, 220_071)))
    assert (own.board[0].attack, own.board[0].health) == (4, 2)
    assert own.locations[0].durability == 2
    assert own.locations[0].cooldown == 1


def test_temporary_combo_and_spell_discounts_reset_at_turn_end() -> None:
    game, actor, _ = _game("CORE_DMF_511", "CORE_EX1_145")
    own = game.state.players[actor]
    own.hand = [HandCard(220_080, "CORE_DMF_511"), HandCard(220_081, "CORE_EX1_145")]
    game.apply(Action(ActionType.PLAY, 220_080))
    game.apply(Action(ActionType.PLAY, 220_081))
    assert own.next_combo_discount_this_turn == 2
    assert own.next_spell_discount_this_turn == 2
    game.apply(Action.end_turn())
    assert own.next_combo_discount_this_turn == 0
    assert own.next_spell_discount_this_turn == 0


def test_discounted_discover_draw_and_frozen_summon_keep_instance_state() -> None:
    game, actor, _ = _game("CORE_GIL_836", "CORE_CS2_053", "CORE_AV_107")
    own = game.state.players[actor]
    own.deck = ["CS2_200"]
    own.hand = [HandCard(220_090, "CORE_GIL_836")]
    game.apply(Action(ActionType.PLAY, 220_090))
    game.apply(Action(ActionType.DISCOVER, choice=0))
    assert own.hand[0].cost_modifier == -1

    own.hand = [HandCard(220_091, "CORE_CS2_053")]
    game.apply(Action(ActionType.PLAY, 220_091))
    assert own.hand[0].card_id == "CS2_200"
    assert own.hand[0].cost_modifier == -3

    own.hand = [HandCard(220_092, "CORE_AV_107")]
    own.mana = 10
    game.apply(Action(ActionType.PLAY, 220_092))
    game.apply(Action(ActionType.DISCOVER, choice=0))
    assert own.board[-1].card_id == "CORE_EX1_383"
    assert own.board[-1].frozen


@pytest.mark.parametrize(
    ("card_id", "cost", "expected_armor"),
    [("CORE_KAR_077", 2, 0), ("CORE_WON_337", 4, 4)],
)
def test_portals_summon_the_exact_cost_and_ironforge_grants_armor(
    card_id: str, cost: int, expected_armor: int
) -> None:
    game, actor, _ = _game(card_id)
    own = game.state.players[actor]
    own.hand = [HandCard(220_100, card_id)]
    target = None
    if card_id == "CORE_KAR_077":
        own.board = [Minion(220_101, "CS2_120", 2, 3, 3, summoned_turn=0)]
        target = TargetRef.minion(actor, 220_101)
    game.apply(Action(ActionType.PLAY, 220_100, target))
    summoned = own.board[-1]
    assert game.cards[summoned.card_id].cost == cost
    assert own.hero_armor == expected_armor
