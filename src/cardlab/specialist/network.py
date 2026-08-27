from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..cards import CARDS
from ..model import Action
from .features import ACTION_SIZE, STATE_SIZE, encode_action, encode_state

try:
    import torch  # type: ignore[import-not-found]
    from torch import Tensor, nn
except ImportError:  # pragma: no cover - tested in the dependency-free CLI path
    torch = None  # type: ignore
    Tensor = Any  # type: ignore
    nn = None  # type: ignore


def require_torch() -> None:
    if torch is None:
        raise RuntimeError("training requires the optional dependency: pip install -e '.[train]'")


if nn is not None:

    class ActionValueNetwork(nn.Module):
        def __init__(self, hidden_size: int = 128) -> None:
            super().__init__()
            self.state_body = nn.Sequential(
                nn.Linear(STATE_SIZE, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
            )
            self.action_head = nn.Sequential(
                nn.Linear(hidden_size + ACTION_SIZE, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, 1),
            )
            self.value_head = nn.Linear(hidden_size, 1)

        def forward(self, states: Tensor, actions: Tensor) -> Tuple[Tensor, Tensor]:
            state_embedding = self.state_body(states)
            logits = self.action_head(torch.cat([state_embedding, actions], dim=-1)).squeeze(-1)
            values = self.value_head(state_embedding).squeeze(-1)
            return logits, values

else:

    class ActionValueNetwork:  # type: ignore[no-redef]
        def __init__(self, hidden_size: int = 128) -> None:
            del hidden_size
            require_torch()


class NeuralPolicy:
    def __init__(
        self,
        model: ActionValueNetwork,
        seed: int = 0,
        temperature: float = 0.0,
        controls: Optional[Dict[str, Any]] = None,
    ) -> None:
        require_torch()
        self.model = model
        self.rng = random.Random(seed)
        self.temperature = temperature
        self.controls = controls or {}

    def distributions(
        self, observation: Dict[str, Any], legal_actions: List[Action]
    ) -> Tuple[Tensor, Tensor]:
        feature_flags = list(self.controls.get("feature_flags", []))
        states = torch.tensor(
            [encode_state(observation, feature_flags)] * len(legal_actions), dtype=torch.float32
        )
        actions = torch.tensor(
            [encode_action(observation, action) for action in legal_actions], dtype=torch.float32
        )
        logits, values = self.model(states, actions)
        priors = self.controls.get("policy_priors", [])
        if priors:
            offsets = [self._prior_score(observation, action, priors) for action in legal_actions]
            logits = logits + torch.tensor(offsets, dtype=torch.float32)
        return logits, values[0]

    @staticmethod
    def _prior_score(
        observation: Dict[str, Any], action: Action, priors: List[Dict[str, Any]]
    ) -> float:
        total = 0.0
        own_attack = sum(m["attack"] for m in observation["own"]["board"])
        enemy_attack = sum(m["attack"] for m in observation["enemy"]["board"])
        source_card = None
        for card in observation["own"].get("hand", []):
            if card["entity_id"] == action.source_id:
                source_card = CARDS[card["card_id"]]
                break
        target_minion = None
        if action.target and action.target.kind == "minion":
            side = "own" if action.target.player == observation["viewer"] else "enemy"
            target_minion = next(
                (
                    m
                    for m in observation[side]["board"]
                    if m["entity_id"] == action.target.entity_id
                ),
                None,
            )
        for prior in priors:
            name = prior["name"]
            weight = float(prior["weight"])
            signal = 0.0
            if name == "spend_mana":
                if source_card:
                    signal = source_card.cost / 10.0
                elif action.action_type.value == "hero_power":
                    signal = 0.2
                elif action.action_type.value == "end_turn":
                    signal = -(observation["own"]["mana"] / 10.0)
            elif name == "face_damage":
                if action.target and action.target.kind == "hero":
                    signal = -1.0 if action.target.player == observation["viewer"] else 1.0
            elif name == "trade_up" and target_minion:
                signal = (target_minion["attack"] + target_minion["health"]) / 20.0
            elif name == "hold_draw_when_behind":
                if source_card and source_card.card_id == "CS2_023" and own_attack < enemy_attack:
                    signal = -1.0
            total += weight * signal
        return total

    def choose(self, observation: Dict[str, Any], legal_actions: List[Action]) -> Action:
        self.model.eval()
        with torch.no_grad():
            logits, _ = self.distributions(observation, legal_actions)
            if self.temperature <= 0:
                return legal_actions[int(torch.argmax(logits).item())]
            probabilities = torch.softmax(logits / self.temperature, dim=0)
            index = int(torch.multinomial(probabilities, 1).item())
            return legal_actions[index]

    def sample(
        self, observation: Dict[str, Any], legal_actions: List[Action]
    ) -> Tuple[Action, Tensor, Tensor, Tensor]:
        logits, value = self.distributions(observation, legal_actions)
        probabilities = torch.softmax(logits / max(self.temperature, 0.05), dim=0)
        distribution = torch.distributions.Categorical(probabilities)
        index = distribution.sample()
        return legal_actions[int(index.item())], distribution.log_prob(index), value, distribution.entropy()


def save_checkpoint(model: ActionValueNetwork, path: Path, metadata: Dict[str, Any]) -> None:
    require_torch()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "metadata": metadata}, path)


def load_checkpoint(path: Path) -> Tuple[ActionValueNetwork, Dict[str, Any]]:
    require_torch()
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = ActionValueNetwork()
    model.load_state_dict(payload["model"])
    return model, dict(payload.get("metadata", {}))
