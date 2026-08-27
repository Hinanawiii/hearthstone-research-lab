import unittest

from cardlab.cards import DECK_CARD_IDS, default_deck
from cardlab.engine import Game, IllegalAction
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef


class EngineTests(unittest.TestCase):
    def test_reference_deck_has_two_copies_of_fifteen_cards(self) -> None:
        deck = default_deck()
        self.assertEqual(len(DECK_CARD_IDS), 15)
        self.assertEqual(len(deck), 30)
        self.assertTrue(all(deck.count(card_id) == 2 for card_id in DECK_CARD_IDS))

    def test_opening_hands_coin_and_first_mana(self) -> None:
        game = Game(seed=3)
        first = game.state.active_player
        second = 1 - first
        self.assertEqual(game.state.players[first].max_mana, 1)
        self.assertEqual(len(game.state.players[first].hand), 4)
        self.assertEqual(len(game.state.players[second].hand), 5)
        self.assertIn("GAME_005", [card.card_id for card in game.state.players[second].hand])

    def test_summoning_sickness_then_ready(self) -> None:
        game = Game(seed=4)
        actor = game.state.active_player
        game.state.players[actor].hand = [HandCard(900, "CS2_231")]
        game.apply(Action(ActionType.PLAY, 900))
        attacks = [a for a in game.legal_actions() if a.action_type == ActionType.ATTACK]
        self.assertEqual(attacks, [])
        game.apply(Action.end_turn())
        game.apply(Action.end_turn())
        attacks = [a for a in game.legal_actions() if a.action_type == ActionType.ATTACK]
        self.assertTrue(attacks)

    def test_charge_can_attack_immediately(self) -> None:
        game = Game(seed=5)
        actor = game.state.active_player
        player = game.state.players[actor]
        player.mana = 10
        player.hand = [HandCard(901, "CS2_124")]
        game.apply(Action(ActionType.PLAY, 901))
        attacks = [a for a in game.legal_actions() if a.action_type == ActionType.ATTACK]
        self.assertGreaterEqual(len(attacks), 1)

    def test_minion_combat_damage_is_simultaneous(self) -> None:
        game = Game(seed=51)
        actor = game.state.active_player
        enemy = 1 - actor
        game.state.players[actor].board = [Minion(910, "CS2_172", 3, 2, 2)]
        game.state.players[enemy].board = [Minion(911, "CS2_172", 3, 2, 2)]
        game.apply(Action(ActionType.ATTACK, 910, TargetRef.minion(enemy, 911)))
        self.assertEqual(game.state.players[actor].board, [])
        self.assertEqual(game.state.players[enemy].board, [])

    def test_taunt_is_only_attack_target(self) -> None:
        game = Game(seed=6)
        actor = game.state.active_player
        enemy = 1 - actor
        game.state.players[actor].board = [Minion(100, "CS2_172", 3, 2, 2)]
        game.state.players[enemy].board = [
            Minion(101, "CS1_042", 1, 2, 2, taunt=True),
            Minion(102, "CS2_172", 3, 2, 2),
        ]
        attacks = [a for a in game.legal_actions() if a.action_type == ActionType.ATTACK]
        self.assertEqual({a.target.entity_id for a in attacks}, {101})

    def test_targeted_damage_and_death_cleanup(self) -> None:
        game = Game(seed=7)
        actor = game.state.active_player
        enemy = 1 - actor
        game.state.players[actor].mana = 10
        game.state.players[actor].hand = [HandCard(902, "CS2_029")]
        game.state.players[enemy].board = [Minion(103, "CS2_182", 4, 5, 5)]
        game.apply(Action(ActionType.PLAY, 902, TargetRef.minion(enemy, 103)))
        self.assertEqual(game.state.players[enemy].board, [])

    def test_hero_power_is_once_per_turn(self) -> None:
        game = Game(seed=52)
        actor = game.state.active_player
        enemy = 1 - actor
        game.state.players[actor].mana = 10
        power = Action(ActionType.HERO_POWER, target=TargetRef.hero(enemy))
        game.apply(power)
        self.assertEqual(game.state.players[enemy].hero_health, 29)
        self.assertNotIn(power, game.legal_actions())

    def test_fatigue_increases_after_empty_deck_draws(self) -> None:
        game = Game(seed=53)
        actor = game.state.active_player
        game.state.players[actor].deck = []
        game._draw(actor)
        game._draw(actor)
        self.assertEqual(game.state.players[actor].fatigue, 2)
        self.assertEqual(game.state.players[actor].hero_health, 27)

    def test_illegal_friendly_fireball_when_not_enough_mana(self) -> None:
        game = Game(seed=8)
        actor = game.state.active_player
        game.state.players[actor].mana = 0
        game.state.players[actor].hand = [HandCard(903, "CS2_029")]
        with self.assertRaises(IllegalAction):
            game.apply(Action(ActionType.PLAY, 903, TargetRef.hero(actor)))

    def test_seed_and_actions_make_random_damage_reproducible(self) -> None:
        first = Game(seed=9)
        actor = first.state.active_player
        enemy = 1 - actor
        first.state.players[actor].mana = 10
        first.state.players[actor].hand = [HandCard(904, "EX1_277")]
        first.state.players[enemy].board = [
            Minion(104, "CS2_120", 2, 3, 3),
            Minion(105, "CS2_120", 2, 3, 3),
        ]
        second = first.clone()
        action = Action(ActionType.PLAY, 904)
        first.apply(action)
        second.apply(action)
        self.assertEqual(first.public_snapshot(), second.public_snapshot())

    def test_observation_hides_opponent_hand_and_deck_order(self) -> None:
        game = Game(seed=10)
        view = game.observation(game.state.active_player)
        self.assertIn("hand", view["own"])
        self.assertNotIn("hand", view["enemy"])
        self.assertNotIn("deck", view["own"])
        self.assertNotIn("deck", view["enemy"])


if __name__ == "__main__":
    unittest.main()
