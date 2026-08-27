from __future__ import annotations

from typing import Any, Dict

PROBE_CATALOG: Dict[str, Dict[str, Any]] = {
    "tempo_vs_draw_v1": {
        "description": (
            "Turn 3-7 tempo-deficit position with Arcane Intellect and an affordable minion."
        ),
        "choice_a": {
            "key": "draw_now",
            "description": "play Arcane Intellect",
        },
        "choice_b": {
            "key": "develop_minion",
            "description": "play Chillwind Yeti",
        },
        "comparison": "choice_b_minus_choice_a",
        "metrics": [
            "terminal_score",
            "two_turn_damage_taken",
            "two_turn_board_value_gap",
        ],
    }
}
