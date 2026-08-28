from __future__ import annotations

import pytest

from cardlab.authoring.generated.keyword_batch import CARDS as KEYWORD_CARDS
from cardlab.cards import CARDS
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef


def _game() -> Game:
    registry = dict(CARDS)
    registry.update(KEYWORD_CARDS)
    return Game(seed=20260828, card_registry=registry)


def _attacks(game: Game, source_id: int) -> list[Action]:
    return [
        action
        for action in game.legal_actions()
        if action.action_type == ActionType.ATTACK and action.source_id == source_id
    ]


def test_stealth_blocks_enemy_targets_and_attacks_then_breaks_on_attack() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].mana = 10
    game.state.players[actor].hand = [HandCard(1_001, "CS2_029")]
    game.state.players[actor].board = [Minion(1_002, "CS2_120", 2, 3, 3)]
    game.state.players[enemy].board = [
        Minion(1_003, "CORE_EX1_028", 5, 5, 5, stealth=True, summoned_turn=0)
    ]

    hidden_target = TargetRef.minion(enemy, 1_003)
    assert all(action.target != hidden_target for action in game.legal_actions())

    game.state.active_player = enemy
    game.state.players[enemy].board[0].summoned_turn = game.state.turn - 1
    attack = Action(ActionType.ATTACK, 1_003, TargetRef.hero(actor))
    assert attack in game.legal_actions()
    game.apply(attack)
    assert game.state.players[enemy].board[0].stealth is False


def test_lifesteal_heals_for_damage_dealt_and_caps_at_thirty() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].hero_health = 29
    game.state.players[actor].board = [
        Minion(2_001, "CORE_GIL_558", 2, 1, 1, lifesteal=True, summoned_turn=0)
    ]
    game.apply(Action(ActionType.ATTACK, 2_001, TargetRef.hero(enemy)))
    assert game.state.players[actor].hero_health == 30
    assert game.state.players[enemy].hero_health == 28

    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].hero_health = 20
    game.state.players[actor].board = [
        Minion(2_002, "CORE_GIL_558", 2, 1, 1, lifesteal=True, summoned_turn=0)
    ]
    game.state.players[enemy].board = [
        Minion(2_003, "CORE_ICC_038", 0, 1, 1, divine_shield=True)
    ]
    game.apply(Action(ActionType.ATTACK, 2_002, TargetRef.minion(enemy, 2_003)))
    assert game.state.players[actor].hero_health == 20


def test_defending_lifesteal_minion_heals_its_owner() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[enemy].hero_health = 20
    game.state.players[actor].board = [
        Minion(2_004, "CS2_120", 2, 3, 3, summoned_turn=0)
    ]
    game.state.players[enemy].board = [
        Minion(2_005, "CORE_GIL_558", 2, 1, 1, lifesteal=True)
    ]

    game.apply(Action(ActionType.ATTACK, 2_004, TargetRef.minion(enemy, 2_005)))

    assert game.state.players[enemy].hero_health == 22


def test_reborn_returns_a_new_one_health_entity_only_once() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].board = [
        Minion(3_001, "CORE_ULD_723", 1, 1, 1, reborn=True, summoned_turn=0)
    ]
    game.state.players[enemy].board = [Minion(3_002, "CS2_120", 1, 1, 1)]
    game.apply(Action(ActionType.ATTACK, 3_001, TargetRef.minion(enemy, 3_002)))
    returned = game.state.players[actor].board[0]
    assert returned.entity_id != 3_001
    assert returned.health == 1
    assert returned.reborn is False

    returned.health = 0
    game._cleanup_deaths()
    assert game.state.players[actor].board == []


def test_elusive_rejects_spell_and_hero_power_targets_but_allows_attacks() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].mana = 10
    game.state.players[actor].hand = [HandCard(4_001, "CS2_029")]
    game.state.players[actor].board = [Minion(4_002, "CS2_120", 2, 3, 3)]
    game.state.players[enemy].board = [
        Minion(4_003, "CORE_NEW1_023", 3, 2, 2, elusive=True)
    ]
    target = TargetRef.minion(enemy, 4_003)
    legal = game.legal_actions()
    assert Action(ActionType.PLAY, 4_001, target) not in legal
    assert Action(ActionType.HERO_POWER, target=target) not in legal
    assert Action(ActionType.ATTACK, 4_002, target) in legal


def test_rush_can_only_attack_minions_on_its_summoning_turn() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].board = [
        Minion(5_001, "CS3_038", 3, 1, 1, rush=True, summoned_turn=game.state.turn)
    ]
    game.state.players[enemy].board = [Minion(5_002, "CS2_120", 0, 5, 5)]
    targets = {action.target for action in _attacks(game, 5_001)}
    assert targets == {TargetRef.minion(enemy, 5_002)}

    game.state.players[actor].board[0].summoned_turn -= 1
    targets = {action.target for action in _attacks(game, 5_001)}
    assert TargetRef.hero(enemy) in targets


def test_divine_shield_replaces_the_first_damage_only() -> None:
    game = _game()
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.players[actor].board = [Minion(6_001, "CS2_120", 2, 3, 3)]
    game.state.players[enemy].board = [
        Minion(6_002, "CORE_GVG_085", 1, 2, 2, divine_shield=True)
    ]
    target = TargetRef.minion(enemy, 6_002)
    game.apply(Action(ActionType.ATTACK, 6_001, target))
    shielded = game.state.players[enemy].board[0]
    assert shielded.health == 2
    assert shielded.divine_shield is False

    game.state.players[actor].board[0].attacks_this_turn = 0
    game.apply(Action(ActionType.ATTACK, 6_001, target))
    assert game.state.players[enemy].board == []


@pytest.mark.parametrize("card_id,amount", [("CORE_AT_052", 1), ("CORE_EX1_250", 2)])
def test_overload_locks_mana_on_the_owners_next_turn(card_id: str, amount: int) -> None:
    game = _game()
    actor = game.state.active_player
    player = game.state.players[actor]
    player.mana = player.max_mana = 10
    player.hand = [HandCard(7_001, card_id)]
    game.apply(Action(ActionType.PLAY, 7_001))
    assert player.overload_pending == amount

    game.apply(Action.end_turn())
    game.apply(Action.end_turn())
    assert player.overload_pending == 0
    assert player.overloaded_mana == amount
    assert player.mana == player.max_mana - amount
