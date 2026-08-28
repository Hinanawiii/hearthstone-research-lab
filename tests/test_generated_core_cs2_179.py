import unittest
from dataclasses import asdict

from cardlab.authoring.generated.core_cs2_179 import (
    AUTHORING_METADATA,
    CARD,
    build_review_scenario,
)
from cardlab.authoring.review_format import REVIEW_SCHEMA_VERSION, validate_review_document
from cardlab.cards import CARDS
from cardlab.engine import Game
from cardlab.model import Action, ActionType, CardType, HandCard, Minion, TargetRef


def _registry():
    registry = dict(CARDS)
    registry[CARD.card_id] = CARD
    return registry


class GeneratedSenjinShieldmastaTests(unittest.TestCase):
    def test_card_matches_the_approved_source_contract(self) -> None:
        self.assertEqual(CARD.card_id, "CORE_CS2_179")
        self.assertEqual(CARD.name, "森金持盾卫士")
        self.assertEqual(CARD.card_type, CardType.MINION)
        self.assertEqual((CARD.cost, CARD.attack, CARD.health), (4, 3, 5))
        self.assertTrue(CARD.taunt)
        self.assertFalse(CARD.charge)
        self.assertEqual(CARD.effects, ())
        self.assertEqual(AUTHORING_METADATA["source_version"], "250339")
        self.assertEqual(AUTHORING_METADATA["source_text_zh"], "嘲讽")

    def test_review_scenario_is_valid_and_exposes_the_entry_state(self) -> None:
        scenario = build_review_scenario(_registry())
        document = {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "locale": "zh-CN",
            "card": {
                "card_id": CARD.card_id,
                "name_zh": CARD.name,
                "source_text_zh": AUTHORING_METADATA["source_text_zh"],
                "source_version": AUTHORING_METADATA["source_version"],
            },
            "implementation": {
                "card_module": "src/cardlab/authoring/generated/core_cs2_179.py",
                "generator": AUTHORING_METADATA["generated_by"],
                "definition": asdict(CARD),
            },
            "scenario": scenario,
        }
        validate_review_document(document)

        before_players = {player["role_zh"]: player for player in scenario["before"]["players"]}
        after_players = {player["role_zh"]: player for player in scenario["after"]["players"]}
        before_own = before_players["我方"]
        after_own = after_players["我方"]
        summoned = next(
            minion
            for minion in after_own["zones"]["board"]
            if minion["card_id"] == CARD.card_id
        )

        self.assertEqual(before_own["resources"]["mana"], 6)
        self.assertEqual(after_own["resources"]["mana"], 2)
        self.assertEqual(after_own["zones"]["hand"]["count"], 0)
        self.assertEqual(
            (summoned["attack"], summoned["health"], summoned["max_health"]),
            (3, 5, 5),
        )
        self.assertEqual(summoned["mechanics_zh"], ["嘲讽"])
        self.assertEqual(scenario["special_cases"], [])

    def test_cost_summoning_sickness_and_taunt_are_enforced(self) -> None:
        game = Game(seed=179, card_registry=_registry())
        actor = game.state.active_player
        enemy = 1 - actor
        own = game.state.players[actor]
        opposing = game.state.players[enemy]
        own.mana = 3
        own.hand = [HandCard(17901, CARD.card_id)]
        own.board = [Minion(17902, "CS2_231", 1, 1, 1)]
        opposing.deck = ["CS2_231"]
        opposing.board = [Minion(17903, "CS2_120", 2, 3, 3)]
        play = Action(ActionType.PLAY, source_id=17901)

        self.assertNotIn(play, game.legal_actions())
        own.mana = 4
        self.assertIn(play, game.legal_actions())
        game.apply(play)

        summoned = next(minion for minion in own.board if minion.card_id == CARD.card_id)
        self.assertEqual(own.mana, 0)
        self.assertEqual((summoned.attack, summoned.health, summoned.max_health), (3, 5, 5))
        self.assertTrue(summoned.taunt)
        attack_sources = {
            action.source_id
            for action in game.legal_actions()
            if action.action_type == ActionType.ATTACK
        }
        self.assertNotIn(summoned.entity_id, attack_sources)

        game.apply(Action.end_turn())
        enemy_attacks = [
            action
            for action in game.legal_actions()
            if action.action_type == ActionType.ATTACK
        ]
        self.assertTrue(enemy_attacks)
        self.assertEqual(
            {action.target for action in enemy_attacks},
            {TargetRef.minion(actor, summoned.entity_id)},
        )


if __name__ == "__main__":
    unittest.main()
