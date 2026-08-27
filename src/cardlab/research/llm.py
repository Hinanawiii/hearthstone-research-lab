from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Protocol

from .schema import ResearchProposal, proposal_from_dict, proposal_schema_example

SYSTEM_PROMPT = """You are the game-science director of CardLab. Study the supplied finite game,
form a falsifiable theory about strategic play, and design a controlled intervention. Your job is
not to act as a generic neural-network technician. A proposal that only changes an optimizer,
learning rate, layer count, batch size, or training duration is invalid. Connect rules to a game
mechanism, make directional predictions, name evidence that could refute you, and compare real
in-game choices in at least one probe. Return exactly one JSON object matching the schema."""


class ResearchBackend(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class MockResearchBackend:
    """A deterministic proposal for CI and protocol demonstrations; it is not an LLM."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        return json.dumps(
            {
                "proposal_id": "tempo-window-before-draw",
                "hypothesis": {
                    "title": "Board initiative changes the value of unconditional draw",
                    "claim": "Arcane Intellect is usually inferior to developing comparable mana "
                    "when the opponent has more board attack and neither player is near fatigue.",
                    "mechanism": "Draw converts current mana into future options but does not absorb "
                    "or threaten damage; an opposing initiative therefore compounds for one turn.",
                    "scope": "Turns 3-7, health above 12, non-empty decks, enemy board attack at least "
                    "three greater than friendly board attack.",
                    "evidence_needed": [
                        "paired rollouts from matched public positions",
                        "next-two-turn damage and board-value deltas",
                    ],
                    "predictions": [
                        "Developing a minion reduces damage taken over two turns versus immediate draw.",
                        "The relation weakens when friendly board attack is not behind.",
                    ],
                    "falsifiers": [
                        "Matched rollouts show no reduction in damage in the scoped positions.",
                        "The same effect size appears when the player is ahead on board.",
                    ],
                },
                "interventions": [
                    {
                        "kind": "curriculum",
                        "target": "self-play position sampler",
                        "change": "oversample turn 3-7 positions with a negative board-attack gap "
                        "and Arcane Intellect plus a playable minion in hand",
                        "rationale": "forces repeated decisions at the proposed tempo-versus-options boundary",
                    },
                    {
                        "kind": "feature",
                        "target": "specialist state encoder",
                        "change": "add board-attack gap and playable-minion mana utilization features",
                        "rationale": "represents the proposed opportunity cost without hard-coding an answer",
                    },
                    {
                        "kind": "evaluation_probe",
                        "target": "tempo_vs_draw_v1",
                        "change": "evaluate paired seeded continuations after draw-first and develop-first choices",
                        "rationale": "directly tests the directional prediction",
                    },
                ],
                "probes": [
                    {
                        "name": "tempo-vs-draw-when-behind",
                        "question": "Should the player draw now or develop a minion while behind on board?",
                        "position_filter": "turn 3-7; health > 12; enemy board attack gap >= 3; "
                        "Arcane Intellect and an affordable minion in hand",
                        "compared_choices": ["play Arcane Intellect", "play the highest-health affordable minion"],
                        "metric": "paired two-turn damage taken, then terminal win rate",
                        "expected_relation": "develop-first takes less damage; win-rate gain is largest at attack gap >= 5",
                    }
                ],
                "experiment": {
                    "feature_flags": ["board_attack_gap", "playable_minion_mana"],
                    "curriculum": [
                        {"scenario": "normal", "weight": 0.7},
                        {"scenario": "tempo_deficit_draw", "weight": 0.3},
                    ],
                    "policy_priors": [
                        {"name": "hold_draw_when_behind", "weight": 0.15}
                    ],
                },
                "expected_outcomes": [
                    "Lower two-turn damage in the scoped probe without a global ban on drawing.",
                    "No material change in matched positions where the player is ahead on board.",
                ],
                "risks": [
                    "The greedy baseline may create a biased set of behind-on-board positions.",
                    "Two-turn damage can reward survival while missing a later fatigue advantage.",
                ],
            },
            ensure_ascii=False,
        )


class OpenAICompatibleBackend:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> "OpenAICompatibleBackend":
        missing = [
            name
            for name in ("CARDLAB_LLM_BASE_URL", "CARDLAB_LLM_API_KEY", "CARDLAB_LLM_MODEL")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError("missing environment variables: {}".format(", ".join(missing)))
        return cls(
            os.environ["CARDLAB_LLM_BASE_URL"],
            os.environ["CARDLAB_LLM_API_KEY"],
            os.environ["CARDLAB_LLM_MODEL"],
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Authorization": "Bearer {}".format(self.api_key),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError("LLM endpoint returned HTTP {}: {}".format(exc.code, detail)) from exc
        return str(body["choices"][0]["message"]["content"])


def make_user_prompt(packet: Dict[str, Any]) -> str:
    return "RESEARCH PACKET\n{}\n\nREQUIRED JSON SCHEMA EXAMPLE\n{}".format(
        json.dumps(packet, ensure_ascii=False, sort_keys=True),
        json.dumps(proposal_schema_example(), ensure_ascii=False, sort_keys=True),
    )


def run_research(backend: ResearchBackend, packet: Dict[str, Any]) -> ResearchProposal:
    raw = backend.complete(SYSTEM_PROMPT, make_user_prompt(packet))
    data = _parse_json_object(raw)
    return proposal_from_dict(data)


def _parse_json_object(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("research backend did not return valid JSON: {}".format(exc)) from exc
    if not isinstance(parsed, dict):
        raise ValueError("research backend must return one JSON object")
    return parsed
