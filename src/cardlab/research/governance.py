from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from ..authoring.store import ReviewStore

PROPOSAL_TRANSITIONS = {
    "draft": {"critic_reviewed"},
    "critic_reviewed": {"awaiting_human", "revision_requested"},
    "awaiting_human": {"approved", "rejected", "revision_requested"},
    "revision_requested": {"draft"},
    "approved": set(),
    "rejected": set(),
}
EXPERIMENT_TRANSITIONS = {
    "registered": {"frozen"},
    "frozen": {"awaiting_human"},
    "awaiting_human": {"approved", "rejected"},
    "approved": set(),
    "rejected": set(),
}
DEPENDENCY_KINDS = {"primary", "token", "random_pool", "interaction"}
CHAMPION_STATUSES = {"candidate", "current", "retired"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class ResearchGovernanceStore:
    """Human-gated research planning. It never invokes training or probe execution."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # The authoring store owns the card-readiness schema used by capsule gates.
        ReviewStore(self.path)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    question TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    proposed_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    critic_review TEXT NOT NULL DEFAULT '',
                    human_review TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_proposal_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL REFERENCES research_proposals(proposal_id),
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_capsules (
                    capsule_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL REFERENCES research_proposals(proposal_id),
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    dependency_snapshot_json TEXT NOT NULL DEFAULT '[]',
                    dependency_hash TEXT NOT NULL DEFAULT '',
                    frozen_by TEXT NOT NULL DEFAULT '',
                    frozen_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_capsule_cards (
                    capsule_id TEXT NOT NULL REFERENCES research_capsules(capsule_id),
                    card_id TEXT NOT NULL REFERENCES cards(card_id),
                    dependency_kind TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(capsule_id, card_id)
                );

                CREATE TABLE IF NOT EXISTS research_champions (
                    champion_id TEXT PRIMARY KEY,
                    parent_champion_id TEXT REFERENCES research_champions(champion_id),
                    checkpoint_path TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    promoted_by TEXT NOT NULL DEFAULT '',
                    promoted_at TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL REFERENCES research_proposals(proposal_id),
                    capsule_id TEXT NOT NULL REFERENCES research_capsules(capsule_id),
                    base_champion_id TEXT NOT NULL REFERENCES research_champions(champion_id),
                    candidate_champion_id TEXT REFERENCES research_champions(champion_id),
                    probe_spec_json TEXT NOT NULL,
                    experiment_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}',
                    human_review TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_experiment_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL REFERENCES research_experiments(experiment_id),
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_research_proposals_status
                    ON research_proposals(status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_capsule_cards_card
                    ON research_capsule_cards(card_id, capsule_id);
                CREATE INDEX IF NOT EXISTS idx_experiments_status
                    ON research_experiments(status, updated_at);
                """
            )

    def create_proposal(
        self,
        proposal_id: str,
        title: str,
        question: str,
        rationale: str,
        *,
        proposed_by: str,
        evidence: Sequence[Mapping[str, Any]] = (),
    ) -> Dict[str, Any]:
        values = [proposal_id, title, question, rationale, proposed_by]
        if any(not value.strip() for value in values):
            raise ValueError("proposal fields and proposed_by are required")
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO research_proposals(
                    proposal_id, title, question, rationale, evidence_json,
                    proposed_by, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)
                """,
                (
                    proposal_id.strip(),
                    title.strip(),
                    question.strip(),
                    rationale.strip(),
                    _canonical_json([dict(item) for item in evidence]),
                    proposed_by.strip(),
                    timestamp,
                    timestamp,
                ),
            )
            self._proposal_event(
                connection, proposal_id, None, "draft", proposed_by, "proposal created", timestamp
            )
        return self.get_proposal(proposal_id)

    def transition_proposal(
        self,
        proposal_id: str,
        to_status: str,
        *,
        actor: str,
        note: str,
    ) -> Dict[str, Any]:
        actor = actor.strip()
        note = note.strip()
        if not actor or not note:
            raise ValueError("proposal transition requires actor and review note")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM research_proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            if row is None:
                raise KeyError("research proposal not found: {}".format(proposal_id))
            current = str(row["status"])
            if to_status not in PROPOSAL_TRANSITIONS[current]:
                raise ValueError("invalid proposal transition: {} -> {}".format(current, to_status))
            timestamp = _now()
            critic_review = note if to_status == "critic_reviewed" else None
            human_review = (
                note if to_status in {"approved", "rejected", "revision_requested"} else None
            )
            connection.execute(
                """
                UPDATE research_proposals SET status = ?,
                    critic_review = COALESCE(?, critic_review),
                    human_review = COALESCE(?, human_review), updated_at = ?
                WHERE proposal_id = ?
                """,
                (to_status, critic_review, human_review, timestamp, proposal_id),
            )
            self._proposal_event(
                connection, proposal_id, current, to_status, actor, note, timestamp
            )
        return self.get_proposal(proposal_id)

    def list_proposals(self) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM research_proposals ORDER BY updated_at DESC, proposal_id"
            ).fetchall()
        return [self._proposal_from_row(row) for row in rows]

    def get_proposal(self, proposal_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            events = connection.execute(
                """
                SELECT * FROM research_proposal_events
                WHERE proposal_id = ? ORDER BY event_id
                """,
                (proposal_id,),
            ).fetchall()
        if row is None:
            raise KeyError("research proposal not found: {}".format(proposal_id))
        proposal = self._proposal_from_row(row)
        proposal["events"] = [dict(item) for item in events]
        return proposal

    def create_capsule(
        self,
        capsule_id: str,
        proposal_id: str,
        name: str,
        dependencies: Sequence[Mapping[str, str]],
    ) -> Dict[str, Any]:
        if not capsule_id.strip() or not name.strip():
            raise ValueError("capsule_id and name are required")
        if not dependencies:
            raise ValueError("research capsule requires card dependencies")
        proposal = self.get_proposal(proposal_id)
        if proposal["status"] != "approved":
            raise ValueError("research proposal must have human approval")
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO research_capsules(
                    capsule_id, proposal_id, name, status, created_at, updated_at
                ) VALUES (?, ?, ?, 'draft', ?, ?)
                """,
                (capsule_id.strip(), proposal_id, name.strip(), timestamp, timestamp),
            )
            for dependency in dependencies:
                card_id = str(dependency.get("card_id", "")).strip()
                kind = str(dependency.get("dependency_kind", "primary")).strip()
                if not card_id:
                    raise ValueError("capsule dependency card_id is required")
                if kind not in DEPENDENCY_KINDS:
                    raise ValueError("unknown dependency kind: {}".format(kind))
                connection.execute(
                    """
                    INSERT INTO research_capsule_cards(
                        capsule_id, card_id, dependency_kind, note
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (capsule_id, card_id, kind, str(dependency.get("note", "")).strip()),
                )
        return self.get_capsule(capsule_id)

    def get_capsule(self, capsule_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_capsules WHERE capsule_id = ?", (capsule_id,)
            ).fetchone()
            dependencies = connection.execute(
                """
                SELECT rcc.*, c.name, c.source_version, c.interview_complete,
                    c.generation_approved, c.implementation_status
                FROM research_capsule_cards rcc
                JOIN cards c ON c.card_id = rcc.card_id
                WHERE rcc.capsule_id = ? ORDER BY rcc.dependency_kind, rcc.card_id
                """,
                (capsule_id,),
            ).fetchall()
        if row is None:
            raise KeyError("research capsule not found: {}".format(capsule_id))
        capsule = dict(row)
        capsule["dependencies"] = [dict(item) for item in dependencies]
        try:
            capsule["dependency_snapshot"] = json.loads(
                capsule.pop("dependency_snapshot_json")
            )
        except json.JSONDecodeError:
            capsule["dependency_snapshot"] = []
        capsule["readiness"] = self.capsule_readiness(capsule_id)
        current_snapshot = self._dependency_snapshot(capsule["dependencies"])
        capsule["snapshot_matches_current"] = (
            capsule["status"] != "frozen"
            or capsule["dependency_hash"] == _hash(current_snapshot)
        )
        return capsule

    def capsule_readiness(self, capsule_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT card_id FROM research_capsule_cards WHERE capsule_id = ? ORDER BY card_id",
                (capsule_id,),
            ).fetchall()
        if not rows:
            raise ValueError("research capsule has no dependencies")
        review_store = ReviewStore(self.path)
        cards = [review_store.get_card(str(row["card_id"])) for row in rows]
        blocked = [
            {
                "card_id": card["card_id"],
                "name": card["name"],
                "authoring_ready": card["authoring_ready"],
                "generation_approved": card["generation_approved"],
                "implementation_status": card["implementation_status"],
            }
            for card in cards
            if not card["ready_for_research"]
        ]
        return {
            "ready_to_freeze": not blocked,
            "dependency_count": len(cards),
            "blocked": blocked,
        }

    def freeze_capsule(self, capsule_id: str, *, reviewer: str) -> Dict[str, Any]:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("capsule freeze requires a reviewer")
        capsule = self.get_capsule(capsule_id)
        if capsule["status"] != "draft":
            raise ValueError("only draft capsules can be frozen")
        if not capsule["readiness"]["ready_to_freeze"]:
            raise ValueError("capsule card dependencies are not implementation_ready")
        review_store = ReviewStore(self.path)
        snapshot = self._dependency_snapshot(capsule["dependencies"], review_store)
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE research_capsules SET status = 'frozen',
                    dependency_snapshot_json = ?, dependency_hash = ?, frozen_by = ?,
                    frozen_at = ?, updated_at = ? WHERE capsule_id = ?
                """,
                (_canonical_json(snapshot), _hash(snapshot), reviewer, timestamp, timestamp, capsule_id),
            )
        return self.get_capsule(capsule_id)

    def register_champion(
        self,
        champion_id: str,
        checkpoint_path: str,
        config: Mapping[str, Any],
        *,
        parent_champion_id: Optional[str] = None,
        status: str = "candidate",
    ) -> Dict[str, Any]:
        if status not in CHAMPION_STATUSES:
            raise ValueError("unknown champion status: {}".format(status))
        if not champion_id.strip() or not checkpoint_path.strip():
            raise ValueError("champion_id and checkpoint_path are required")
        with self._connection() as connection:
            if status == "current" and connection.execute(
                "SELECT 1 FROM research_champions WHERE status = 'current'"
            ).fetchone():
                raise ValueError("a current champion already exists")
            connection.execute(
                """
                INSERT INTO research_champions(
                    champion_id, parent_champion_id, checkpoint_path, config_json,
                    config_hash, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    champion_id.strip(),
                    parent_champion_id,
                    checkpoint_path.strip(),
                    _canonical_json(dict(config)),
                    _hash(dict(config)),
                    status,
                    _now(),
                ),
            )
        return self.get_champion(champion_id)

    def get_champion(self, champion_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_champions WHERE champion_id = ?", (champion_id,)
            ).fetchone()
        if row is None:
            raise KeyError("research champion not found: {}".format(champion_id))
        champion = dict(row)
        champion["config"] = json.loads(champion.pop("config_json"))
        return champion

    def register_experiment(
        self,
        experiment_id: str,
        proposal_id: str,
        capsule_id: str,
        base_champion_id: str,
        probe_spec: Mapping[str, Any],
        *,
        candidate_champion_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        proposal = self.get_proposal(proposal_id)
        capsule = self.get_capsule(capsule_id)
        champion = self.get_champion(base_champion_id)
        if proposal["status"] != "approved":
            raise ValueError("experiment proposal is not approved")
        if capsule["status"] != "frozen":
            raise ValueError("experiment capsule is not frozen")
        if not capsule["snapshot_matches_current"]:
            raise ValueError("experiment capsule is stale and must be rebuilt")
        if champion["status"] != "current":
            raise ValueError("experiment baseline must be the current champion")
        required_ids = {str(value) for value in probe_spec.get("required_card_ids", [])}
        capsule_ids = {str(item["card_id"]) for item in capsule["dependencies"]}
        if not required_ids or not required_ids.issubset(capsule_ids):
            raise ValueError("probe required_card_ids must be a non-empty capsule subset")
        frozen = {
            "proposal_id": proposal_id,
            "capsule_id": capsule_id,
            "capsule_dependency_hash": capsule["dependency_hash"],
            "base_champion_id": base_champion_id,
            "base_champion_config_hash": champion["config_hash"],
            "candidate_champion_id": candidate_champion_id,
            "probe_spec": dict(probe_spec),
        }
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO research_experiments(
                    experiment_id, proposal_id, capsule_id, base_champion_id,
                    candidate_champion_id, probe_spec_json, experiment_hash,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'registered', ?, ?)
                """,
                (
                    experiment_id,
                    proposal_id,
                    capsule_id,
                    base_champion_id,
                    candidate_champion_id,
                    _canonical_json(dict(probe_spec)),
                    _hash(frozen),
                    timestamp,
                    timestamp,
                ),
            )
            self._experiment_event(
                connection,
                experiment_id,
                None,
                "registered",
                "governance-store",
                "experiment registered without execution",
                timestamp,
            )
        return self.get_experiment(experiment_id)

    def transition_experiment(
        self,
        experiment_id: str,
        to_status: str,
        *,
        actor: str,
        note: str,
        result: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not actor.strip() or not note.strip():
            raise ValueError("experiment transition requires actor and review note")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM research_experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if row is None:
                raise KeyError("research experiment not found: {}".format(experiment_id))
            current = str(row["status"])
            if to_status not in EXPERIMENT_TRANSITIONS[current]:
                raise ValueError(
                    "invalid experiment transition: {} -> {}".format(current, to_status)
                )
            if to_status == "awaiting_human" and not result:
                raise ValueError("completed experiment evidence is required before human review")
            timestamp = _now()
            human_review = note if to_status in {"approved", "rejected"} else None
            connection.execute(
                """
                UPDATE research_experiments SET status = ?,
                    result_json = COALESCE(?, result_json),
                    human_review = COALESCE(?, human_review), updated_at = ?
                WHERE experiment_id = ?
                """,
                (
                    to_status,
                    _canonical_json(dict(result)) if result is not None else None,
                    human_review,
                    timestamp,
                    experiment_id,
                ),
            )
            self._experiment_event(
                connection, experiment_id, current, to_status, actor, note, timestamp
            )
        return self.get_experiment(experiment_id)

    def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_experiments WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
            events = connection.execute(
                """
                SELECT * FROM research_experiment_events
                WHERE experiment_id = ? ORDER BY event_id
                """,
                (experiment_id,),
            ).fetchall()
        if row is None:
            raise KeyError("research experiment not found: {}".format(experiment_id))
        experiment = dict(row)
        experiment["probe_spec"] = json.loads(experiment.pop("probe_spec_json"))
        experiment["result"] = json.loads(experiment.pop("result_json"))
        experiment["events"] = [dict(item) for item in events]
        return experiment

    def promote_champion(
        self,
        candidate_champion_id: str,
        experiment_id: str,
        *,
        reviewer: str,
    ) -> Dict[str, Any]:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("champion promotion requires a reviewer")
        experiment = self.get_experiment(experiment_id)
        candidate = self.get_champion(candidate_champion_id)
        if experiment["status"] != "approved":
            raise ValueError("experiment requires human approval before promotion")
        if experiment["candidate_champion_id"] != candidate_champion_id:
            raise ValueError("candidate champion does not belong to experiment")
        if candidate["status"] != "candidate":
            raise ValueError("only candidate champions can be promoted")
        if candidate["parent_champion_id"] != experiment["base_champion_id"]:
            raise ValueError("candidate champion parent must match experiment baseline")
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                "UPDATE research_champions SET status = 'retired' WHERE status = 'current'"
            )
            connection.execute(
                """
                UPDATE research_champions SET status = 'current', promoted_by = ?,
                    promoted_at = ? WHERE champion_id = ?
                """,
                (reviewer, timestamp, candidate_champion_id),
            )
        return self.get_champion(candidate_champion_id)

    def _dependency_snapshot(
        self,
        dependencies: Sequence[Mapping[str, Any]],
        review_store: Optional[ReviewStore] = None,
    ) -> List[Dict[str, Any]]:
        store = review_store or ReviewStore(self.path)
        snapshot = []
        for dependency in dependencies:
            card = store.get_card(str(dependency["card_id"]))
            source_fingerprint = _hash(
                {
                    "name": card["name"],
                    "source_text": card["source_text"],
                    "card_set": card["card_set"],
                    "card_class": card["card_class"],
                    "card_type": card["card_type"],
                    "cost": card["cost"],
                    "source_version": card["source_version"],
                    "source_data": card["source_data"],
                }
            )
            snapshot.append(
                {
                    "card_id": card["card_id"],
                    "source_fingerprint": source_fingerprint,
                    "generation_approved_at": card["generation_approved_at"],
                    "implementation_status": card["implementation_status"],
                    "implementation_reviewed_at": card["implementation_reviewed_at"],
                    "implementation_evidence_hash": _hash(card["implementation_evidence"]),
                    "dependency_kind": dependency["dependency_kind"],
                }
            )
        return snapshot

    @staticmethod
    def _proposal_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        proposal = dict(row)
        try:
            proposal["evidence"] = json.loads(proposal.pop("evidence_json"))
        except json.JSONDecodeError:
            proposal["evidence"] = []
        return proposal

    @staticmethod
    def _proposal_event(
        connection: sqlite3.Connection,
        proposal_id: str,
        from_status: Optional[str],
        to_status: str,
        actor: str,
        note: str,
        timestamp: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO research_proposal_events(
                proposal_id, from_status, to_status, actor, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (proposal_id, from_status, to_status, actor, note, timestamp),
        )

    @staticmethod
    def _experiment_event(
        connection: sqlite3.Connection,
        experiment_id: str,
        from_status: Optional[str],
        to_status: str,
        actor: str,
        note: str,
        timestamp: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO research_experiment_events(
                experiment_id, from_status, to_status, actor, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (experiment_id, from_status, to_status, actor, note, timestamp),
        )
