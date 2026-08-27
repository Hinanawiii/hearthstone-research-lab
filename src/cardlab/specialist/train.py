from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..engine import Game, play_game
from ..model import HandCard, Minion
from ..policy import GreedyPolicy, RandomPolicy
from .network import ActionValueNetwork, NeuralPolicy, require_torch, save_checkpoint, torch


@dataclass
class TrainingConfig:
    episodes: int = 100
    seed: int = 7
    learning_rate: float = 3e-4
    entropy_weight: float = 0.01
    value_weight: float = 0.5
    max_actions: int = 400
    temperature: float = 1.0
    research_controls: Dict[str, Any] = field(default_factory=dict)


def train_self_play(config: TrainingConfig, output: Path) -> Dict[str, Any]:
    require_torch()
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    model = ActionValueNetwork()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    wins = [0, 0]
    draws = 0
    losses: List[float] = []
    curriculum_rng = random.Random(config.seed + 7919)

    for episode in range(config.episodes):
        game = Game(seed=config.seed + episode, starting_player=episode % 2)
        scenario = _sample_scenario(config.research_controls, curriculum_rng)
        _apply_scenario(game, scenario)
        policy = NeuralPolicy(
            model,
            seed=config.seed + episode,
            temperature=config.temperature,
            controls=config.research_controls,
        )
        trajectories: List[List[Tuple[Any, Any, Any]]] = [[], []]
        model.train()
        for _ in range(config.max_actions):
            if game.state.terminal:
                break
            actor = game.state.active_player
            observation = game.observation(actor)
            action, log_prob, value, entropy = policy.sample(observation, game.legal_actions())
            trajectories[actor].append((log_prob, value, entropy))
            game.apply(action)
        if not game.state.terminal:
            game.state.terminal_reason = "draw"
        if game.state.winner is None:
            draws += 1
        else:
            wins[game.state.winner] += 1

        terms = []
        for player, trajectory in enumerate(trajectories):
            reward = 0.0 if game.state.winner is None else (1.0 if game.state.winner == player else -1.0)
            for log_prob, value, entropy in trajectory:
                reward_tensor = torch.tensor(reward, dtype=torch.float32)
                advantage = reward_tensor - value.detach()
                policy_loss = -log_prob * advantage
                value_loss = (value - reward_tensor).pow(2)
                terms.append(policy_loss + config.value_weight * value_loss - config.entropy_weight * entropy)
        if terms:
            loss = torch.stack(terms).mean()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.item()))

    metadata = {
        "schema_version": 1,
        "config": asdict(config),
        "training_wins_by_seat": wins,
        "training_draws": draws,
        "mean_loss": sum(losses) / max(1, len(losses)),
    }
    save_checkpoint(model, output, metadata)
    return metadata


def _sample_scenario(controls: Dict[str, Any], rng: random.Random) -> str:
    curriculum = controls.get("curriculum") or [{"scenario": "normal", "weight": 1.0}]
    names = [str(item["scenario"]) for item in curriculum]
    weights = [float(item["weight"]) for item in curriculum]
    return str(rng.choices(names, weights=weights, k=1)[0])


def _apply_scenario(game: Game, scenario: str) -> None:
    if scenario == "normal":
        return
    if scenario != "tempo_deficit_draw":
        raise ValueError("unsupported training scenario: {}".format(scenario))
    actor = game.state.active_player
    enemy = 1 - actor
    game.state.turn = 7
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.max_mana = own.mana = 4
    opposing.max_mana = opposing.mana = 4
    own.hand = [
        HandCard(800001, "CS2_023"),
        HandCard(800002, "CS2_182"),
        HandCard(800003, "CS2_120"),
    ]
    own.board = [Minion(800004, "CS2_120", 2, 3, 3, summoned_turn=5)]
    opposing.board = [Minion(800005, "CS2_182", 4, 5, 5, summoned_turn=5)]



def evaluate_policy(policy: Any, games: int = 40, seed: int = 1000) -> Dict[str, Any]:
    opponents = {
        "random": lambda game_seed: RandomPolicy(game_seed),
        "greedy": lambda game_seed: GreedyPolicy(game_seed),
    }
    report: Dict[str, Any] = {"games_per_opponent": games, "seed": seed, "opponents": {}}
    for name, factory in opponents.items():
        wins = losses = draws = 0
        action_counts: List[int] = []
        for index in range(games):
            game_seed = seed + index
            if index % 2 == 0:
                game = play_game(policy, factory(game_seed), seed=game_seed)
                learned_seat = 0
            else:
                game = play_game(factory(game_seed), policy, seed=game_seed)
                learned_seat = 1
            action_counts.append(len(game.history))
            if game.state.winner is None:
                draws += 1
            elif game.state.winner == learned_seat:
                wins += 1
            else:
                losses += 1
        report["opponents"][name] = {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate_excluding_draws": wins / max(1, wins + losses),
            "mean_actions": sum(action_counts) / max(1, len(action_counts)),
        }
    return report


def write_report(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
