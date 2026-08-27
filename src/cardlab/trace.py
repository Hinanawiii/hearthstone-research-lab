from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .engine import Game


def game_record(game: Game) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "seed": game.seed,
        "winner": game.state.winner,
        "terminal_reason": game.state.terminal_reason,
        "action_count": len(game.history),
        "history": game.history,
    }


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

