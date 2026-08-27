from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .cards import CARDS
from .model import Action, ActionType


class RandomPolicy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def choose(self, observation: Dict[str, Any], legal_actions: List[Action]) -> Action:
        del observation
        return self.rng.choice(legal_actions)


class GreedyPolicy:
    """A transparent baseline with no search and no privileged information."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def choose(self, observation: Dict[str, Any], legal_actions: List[Action]) -> Action:
        scored = [(self._score(observation, action), action) for action in legal_actions]
        best = max(score for score, _ in scored)
        choices = [action for score, action in scored if score == best]
        return self.rng.choice(choices)

    def _score(self, observation: Dict[str, Any], action: Action) -> float:
        if action.action_type == ActionType.END_TURN:
            return -2.0
        if action.action_type == ActionType.ATTACK:
            if action.target and action.target.kind == "hero":
                return 6.0
            return 3.0
        if action.action_type == ActionType.HERO_POWER:
            if action.target and action.target.player != observation["viewer"]:
                return 2.5
            return -3.0
        if action.action_type == ActionType.PLAY:
            card_id = self._source_card_id(observation, action.source_id)
            card = CARDS[card_id]
            target_bonus = 0.0
            if action.target and action.target.player != observation["viewer"]:
                target_bonus = 2.0
            return 4.0 + card.cost * 0.1 + target_bonus
        return 0.0

    @staticmethod
    def _source_card_id(observation: Dict[str, Any], source_id: Optional[int]) -> str:
        for card in observation["own"].get("hand", []):
            if card["entity_id"] == source_id:
                return str(card["card_id"])
        raise ValueError("source card not visible")

