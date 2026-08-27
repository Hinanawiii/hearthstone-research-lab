from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .schema import ResearchProposal

VALID_RESULTS = {"proposed", "accepted", "rejected", "inconclusive"}


def append_ledger(
    path: Path,
    proposal: ResearchProposal,
    result: str = "proposed",
    evidence: str = "",
) -> Dict[str, Any]:
    if result not in VALID_RESULTS:
        raise ValueError("invalid result: {}".format(result))
    record = {
        "ledger_schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "evidence": evidence,
        "proposal": proposal.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record

