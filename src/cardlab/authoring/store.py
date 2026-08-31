from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

ANSWERED = "answered"
NEEDS_VERIFICATION = "needs_verification"
ANSWER_STATES = {ANSWERED, NEEDS_VERIFICATION}
AI_CANDIDATE_ANSWER = "candidate_answer"
AI_NEEDS_VERIFICATION = "needs_verification"
AI_DISPOSITIONS = {AI_CANDIDATE_ANSWER, AI_NEEDS_VERIFICATION}
AI_CONFIDENCE = {"low", "medium", "high"}
AI_SOURCE_TYPES = {
    "official",
    "maintained_rules",
    "source_code",
    "client_test",
    "community",
    "other",
}
IMPLEMENTATION_STATUSES = {
    "not_started",
    "generated",
    "under_review",
    "implementation_ready",
    "rejected",
}
IMPLEMENTATION_TRANSITIONS = {
    "not_started": {"generated"},
    "generated": {"under_review", "rejected"},
    "under_review": {"generated", "implementation_ready", "rejected"},
    "implementation_ready": {"under_review", "rejected"},
    "rejected": {"generated"},
}
IMPLEMENTATION_READY_EVIDENCE_FIELDS = {
    "code_review",
    "automated_tests",
    "human_scenario_review",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewStore:
    """SQLite-backed, append-only decisions for card-authoring questions."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_text TEXT NOT NULL DEFAULT '',
                    card_set TEXT NOT NULL DEFAULT '',
                    card_class TEXT NOT NULL DEFAULT '',
                    card_type TEXT NOT NULL DEFAULT '',
                    cost INTEGER,
                    source_version TEXT NOT NULL DEFAULT '',
                    source_data_json TEXT NOT NULL DEFAULT '{}',
                    source_kind TEXT NOT NULL DEFAULT 'manual',
                    in_scope INTEGER NOT NULL DEFAULT 1,
                    interview_complete INTEGER NOT NULL DEFAULT 0,
                    generation_approved INTEGER NOT NULL DEFAULT 0,
                    generation_approved_by TEXT NOT NULL DEFAULT '',
                    generation_approved_at TEXT,
                    implementation_status TEXT NOT NULL DEFAULT 'not_started',
                    implementation_reviewed_by TEXT NOT NULL DEFAULT '',
                    implementation_reviewed_at TEXT,
                    implementation_evidence_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_cards (
                    card_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_text TEXT NOT NULL DEFAULT '',
                    collectible INTEGER NOT NULL DEFAULT 0,
                    card_set TEXT NOT NULL DEFAULT '',
                    card_class TEXT NOT NULL DEFAULT '',
                    card_type TEXT NOT NULL DEFAULT '',
                    source_version TEXT NOT NULL,
                    format_revision TEXT NOT NULL,
                    source_data_json TEXT NOT NULL,
                    in_scope INTEGER NOT NULL DEFAULT 1,
                    imported_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS card_name_catalog (
                    card_id TEXT PRIMARY KEY,
                    name_zh TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_version TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questions (
                    question_id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL REFERENCES cards(card_id),
                    category TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    blocking INTEGER NOT NULL DEFAULT 1,
                    asked_by TEXT NOT NULL DEFAULT 'llm',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS answers (
                    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT NOT NULL REFERENCES questions(question_id),
                    resolution TEXT NOT NULL CHECK (
                        resolution IN ('answered', 'needs_verification')
                    ),
                    answer TEXT NOT NULL,
                    respondent TEXT NOT NULL DEFAULT 'human',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_assessments (
                    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_key TEXT NOT NULL UNIQUE,
                    question_id TEXT NOT NULL REFERENCES questions(question_id),
                    disposition TEXT NOT NULL CHECK (
                        disposition IN ('candidate_answer', 'needs_verification')
                    ),
                    answer TEXT NOT NULL,
                    reasoning TEXT NOT NULL DEFAULT '',
                    confidence TEXT NOT NULL CHECK (
                        confidence IN ('low', 'medium', 'high')
                    ),
                    researched_by TEXT NOT NULL DEFAULT 'authoring-ai',
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS card_workflow_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL REFERENCES cards(card_id),
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_questions_card
                    ON questions(card_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_answers_question
                    ON answers(question_id, answer_id);
                CREATE INDEX IF NOT EXISTS idx_ai_assessments_question
                    ON ai_assessments(question_id, assessment_id);
                CREATE INDEX IF NOT EXISTS idx_card_workflow_events_card
                    ON card_workflow_events(card_id, event_id);
                """
            )
            self._migrate_cards(connection)
            connection.execute(
                """
                INSERT OR IGNORE INTO card_name_catalog(
                    card_id, name_zh, source_kind, source_version, updated_at
                )
                SELECT card_id, name, 'standard-source', source_version, imported_at
                FROM source_cards
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO card_name_catalog(
                    card_id, name_zh, source_kind, source_version, updated_at
                )
                SELECT card_id, name, 'review-queue', source_version, updated_at
                FROM cards
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_cards_scope ON cards(in_scope, updated_at)"
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_cards_scope
                ON source_cards(in_scope, collectible, card_set)
                """
            )

    @staticmethod
    def _migrate_cards(connection: sqlite3.Connection) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(cards)").fetchall()
        }
        additions = {
            "card_set": "TEXT NOT NULL DEFAULT ''",
            "card_class": "TEXT NOT NULL DEFAULT ''",
            "card_type": "TEXT NOT NULL DEFAULT ''",
            "cost": "INTEGER",
            "source_version": "TEXT NOT NULL DEFAULT ''",
            "source_data_json": "TEXT NOT NULL DEFAULT '{}'",
            "source_kind": "TEXT NOT NULL DEFAULT 'manual'",
            "in_scope": "INTEGER NOT NULL DEFAULT 1",
            "generation_approved": "INTEGER NOT NULL DEFAULT 0",
            "generation_approved_by": "TEXT NOT NULL DEFAULT ''",
            "generation_approved_at": "TEXT",
            "implementation_status": "TEXT NOT NULL DEFAULT 'not_started'",
            "implementation_reviewed_by": "TEXT NOT NULL DEFAULT ''",
            "implementation_reviewed_at": "TEXT",
            "implementation_evidence_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, declaration in additions.items():
            if name not in existing:
                connection.execute(
                    "ALTER TABLE cards ADD COLUMN {} {}".format(name, declaration)
                )

    def upsert_card(
        self,
        card_id: str,
        name: str,
        source_text: str = "",
        *,
        card_set: str = "",
        card_class: str = "",
        card_type: str = "",
        cost: Optional[int] = None,
        source_version: str = "",
        source_data: Optional[Mapping[str, Any]] = None,
        source_kind: str = "manual",
    ) -> Dict[str, Any]:
        record = self._normalize_card_record(
            {
                "card_id": card_id,
                "name": name,
                "source_text": source_text,
                "card_set": card_set,
                "card_class": card_class,
                "card_type": card_type,
                "cost": cost,
                "source_version": source_version,
                "source_data": source_data or {},
                "source_kind": source_kind,
            }
        )
        timestamp = _now()
        with self._connection() as connection:
            self._write_card(connection, record, timestamp)
        return self.get_card(str(record["card_id"]))

    def upsert_card_names(
        self,
        names_zh: Mapping[str, str],
        *,
        source_kind: str,
        source_version: str = "",
    ) -> None:
        normalized_kind = source_kind.strip()
        if not normalized_kind:
            raise ValueError("card name source kind is required")
        prepared = []
        for raw_card_id, raw_name in names_zh.items():
            card_id = str(raw_card_id).strip()
            name_zh = str(raw_name).strip()
            if not card_id or not name_zh:
                raise ValueError("card name catalog entries require card_id and name_zh")
            prepared.append((card_id, name_zh))
        timestamp = _now()
        with self._connection() as connection:
            for card_id, name_zh in prepared:
                self._write_card_name(
                    connection,
                    card_id,
                    name_zh,
                    normalized_kind,
                    source_version,
                    timestamp,
                )

    def card_names_zh(self) -> Dict[str, str]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT card_id, name_zh FROM card_name_catalog ORDER BY card_id"
            ).fetchall()
        return {str(row["card_id"]): str(row["name_zh"]) for row in rows}

    @staticmethod
    def _write_card_name(
        connection: sqlite3.Connection,
        card_id: str,
        name_zh: str,
        source_kind: str,
        source_version: str,
        timestamp: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO card_name_catalog(
                card_id, name_zh, source_kind, source_version, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(card_id) DO UPDATE SET
                name_zh = excluded.name_zh,
                source_kind = excluded.source_kind,
                source_version = excluded.source_version,
                updated_at = excluded.updated_at
            """,
            (card_id, name_zh, source_kind, source_version, timestamp),
        )

    @staticmethod
    def _normalize_card_record(record: Mapping[str, Any]) -> Dict[str, Any]:
        card_id = str(record.get("card_id", "")).strip()
        name = str(record.get("name", "")).strip()
        if not card_id or not name:
            raise ValueError("card_id and name are required")
        cost_value = record.get("cost")
        cost = int(cost_value) if cost_value is not None else None
        source_data = record.get("source_data") or {}
        if not isinstance(source_data, Mapping):
            raise ValueError("source_data must be an object")
        return {
            "card_id": card_id,
            "name": name,
            "source_text": str(record.get("source_text", "")).strip(),
            "card_set": str(record.get("card_set", "")).strip(),
            "card_class": str(record.get("card_class", "")).strip(),
            "card_type": str(record.get("card_type", "")).strip(),
            "cost": cost,
            "source_version": str(record.get("source_version", "")).strip(),
            "source_data_json": json.dumps(
                dict(source_data), ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
            "source_kind": str(record.get("source_kind", "manual")).strip() or "manual",
        }

    @staticmethod
    def _write_card(
        connection: sqlite3.Connection,
        record: Mapping[str, Any],
        timestamp: str,
    ) -> Tuple[str, bool]:
        existing = connection.execute(
            "SELECT * FROM cards WHERE card_id = ?", (record["card_id"],)
        ).fetchone()
        semantic_fields = (
            "name",
            "source_text",
            "card_set",
            "card_class",
            "card_type",
            "cost",
            "source_data_json",
        )
        changed = existing is None or any(
            existing[field] != record[field] for field in semantic_fields
        )
        ReviewStore._write_card_name(
            connection,
            str(record["card_id"]),
            str(record["name"]),
            str(record["source_kind"]),
            str(record["source_version"]),
            timestamp,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO cards(
                    card_id, name, source_text, card_set, card_class, card_type, cost,
                    source_version, source_data_json, source_kind, in_scope,
                    interview_complete, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
                """,
                (
                    record["card_id"],
                    record["name"],
                    record["source_text"],
                    record["card_set"],
                    record["card_class"],
                    record["card_type"],
                    record["cost"],
                    record["source_version"],
                    record["source_data_json"],
                    record["source_kind"],
                    timestamp,
                    timestamp,
                ),
            )
            return "created", False

        reopened = changed and bool(existing["interview_complete"])
        connection.execute(
            """
            UPDATE cards SET
                name = ?, source_text = ?, card_set = ?, card_class = ?,
                card_type = ?, cost = ?, source_version = ?, source_data_json = ?,
                source_kind = ?, in_scope = 1, interview_complete = ?, updated_at = ?,
                generation_approved = ?, generation_approved_by = ?,
                generation_approved_at = ?, implementation_status = ?,
                implementation_reviewed_by = ?, implementation_reviewed_at = ?,
                implementation_evidence_json = ?
            WHERE card_id = ?
            """,
            (
                record["name"],
                record["source_text"],
                record["card_set"],
                record["card_class"],
                record["card_type"],
                record["cost"],
                record["source_version"],
                record["source_data_json"],
                record["source_kind"],
                0 if changed else existing["interview_complete"],
                timestamp,
                0 if changed else existing["generation_approved"],
                "" if changed else existing["generation_approved_by"],
                None if changed else existing["generation_approved_at"],
                "not_started" if changed else existing["implementation_status"],
                "" if changed else existing["implementation_reviewed_by"],
                None if changed else existing["implementation_reviewed_at"],
                "{}" if changed else existing["implementation_evidence_json"],
                record["card_id"],
            ),
        )
        return ("updated" if changed else "unchanged"), reopened

    def import_standard_catalog(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        source_version: str,
        format_revision: str,
    ) -> Dict[str, int]:
        if not records:
            raise ValueError("standard catalog cannot be empty")
        prepared: List[Tuple[Dict[str, Any], bool]] = []
        for item in records:
            merged = dict(item)
            merged["source_version"] = source_version
            merged["source_kind"] = "hearthstone-standard"
            prepared.append((self._normalize_card_record(merged), bool(item.get("collectible"))))

        timestamp = _now()
        stats = {
            "catalog_total": len(prepared),
            "collectible_total": sum(collectible for _, collectible in prepared),
            "queue_created": 0,
            "queue_updated": 0,
            "queue_unchanged": 0,
            "queue_reopened": 0,
            "queue_out_of_scope": 0,
        }
        current_ids = {str(record["card_id"]) for record, collectible in prepared if collectible}
        with self._connection() as connection:
            previous_ids = {
                str(row["card_id"])
                for row in connection.execute(
                    """
                    SELECT card_id FROM cards
                    WHERE source_kind = 'hearthstone-standard' AND in_scope = 1
                    """
                ).fetchall()
            }
            stats["queue_out_of_scope"] = len(previous_ids - current_ids)
            connection.execute(
                "UPDATE cards SET in_scope = 0 WHERE source_kind = 'hearthstone-standard'"
            )
            connection.execute("UPDATE source_cards SET in_scope = 0")

            for record, collectible in prepared:
                self._write_card_name(
                    connection,
                    str(record["card_id"]),
                    str(record["name"]),
                    "standard-source",
                    source_version,
                    timestamp,
                )
                connection.execute(
                    """
                    INSERT INTO source_cards(
                        card_id, name, source_text, collectible, card_set, card_class,
                        card_type, source_version, format_revision, source_data_json,
                        in_scope, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(card_id) DO UPDATE SET
                        name = excluded.name,
                        source_text = excluded.source_text,
                        collectible = excluded.collectible,
                        card_set = excluded.card_set,
                        card_class = excluded.card_class,
                        card_type = excluded.card_type,
                        source_version = excluded.source_version,
                        format_revision = excluded.format_revision,
                        source_data_json = excluded.source_data_json,
                        in_scope = 1,
                        imported_at = excluded.imported_at
                    """,
                    (
                        record["card_id"],
                        record["name"],
                        record["source_text"],
                        int(collectible),
                        record["card_set"],
                        record["card_class"],
                        record["card_type"],
                        source_version,
                        format_revision,
                        record["source_data_json"],
                        timestamp,
                    ),
                )
                if not collectible:
                    continue
                outcome, reopened = self._write_card(connection, record, timestamp)
                stats["queue_{}".format(outcome)] += 1
                stats["queue_reopened"] += int(reopened)
        return stats

    def set_interview_complete(self, card_id: str, complete: bool) -> Dict[str, Any]:
        with self._connection() as connection:
            if complete:
                cursor = connection.execute(
                    "UPDATE cards SET interview_complete = 1, updated_at = ? WHERE card_id = ?",
                    (_now(), card_id),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE cards SET interview_complete = 0, generation_approved = 0,
                        generation_approved_by = '', generation_approved_at = NULL,
                        implementation_status = 'not_started',
                        implementation_reviewed_by = '', implementation_reviewed_at = NULL,
                        implementation_evidence_json = '{}', updated_at = ?
                    WHERE card_id = ?
                    """,
                    (_now(), card_id),
                )
            if cursor.rowcount != 1:
                raise KeyError("card not found: {}".format(card_id))
        return self.get_card(card_id)

    def add_questions(
        self,
        card_id: str,
        questions: Sequence[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not questions:
            raise ValueError("at least one question is required")
        timestamp = _now()
        inserted: List[str] = []
        with self._connection() as connection:
            if connection.execute(
                "SELECT 1 FROM cards WHERE card_id = ?", (card_id,)
            ).fetchone() is None:
                raise KeyError("card not found: {}".format(card_id))
            for item in questions:
                prompt = str(item.get("prompt", "")).strip()
                category = str(item.get("category", "general")).strip() or "general"
                if not prompt:
                    raise ValueError("question prompt is required")
                question_id = str(item.get("question_id") or uuid.uuid4().hex).strip()
                if not question_id:
                    raise ValueError("question_id is required")
                connection.execute(
                    """
                    INSERT INTO questions(
                        question_id, card_id, category, prompt, rationale,
                        blocking, asked_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question_id,
                        card_id,
                        category,
                        prompt,
                        str(item.get("rationale", "")).strip(),
                        int(bool(item.get("blocking", True))),
                        str(item.get("asked_by", "llm")).strip() or "llm",
                        timestamp,
                    ),
                )
                inserted.append(question_id)
            # A newly discovered question invalidates a previously completed interview.
            connection.execute(
                """
                UPDATE cards SET interview_complete = 0, generation_approved = 0,
                    generation_approved_by = '', generation_approved_at = NULL,
                    implementation_status = 'not_started',
                    implementation_reviewed_by = '', implementation_reviewed_at = NULL,
                    implementation_evidence_json = '{}', updated_at = ?
                WHERE card_id = ?
                """,
                (timestamp, card_id),
            )
        detail = self.get_card(card_id)
        return [item for item in detail["questions"] if item["question_id"] in inserted]

    def add_implementation_test_request(
        self,
        card_id: str,
        prompt: str,
        *,
        requested_by: str = "human",
    ) -> Dict[str, Any]:
        prompt = prompt.strip()
        requested_by = requested_by.strip() or "human"
        if not prompt:
            raise ValueError("implementation test prompt is required")
        card = self.get_card(card_id)
        current_status = str(card["implementation_status"])
        if current_status not in {"under_review", "implementation_ready"}:
            raise ValueError("implementation tests require a generated implementation")

        timestamp = _now()
        question_id = uuid.uuid4().hex
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO questions(
                    question_id, card_id, category, prompt, rationale,
                    blocking, asked_by, created_at
                ) VALUES (?, ?, 'implementation_test', ?, ?, 0, ?, ?)
                """,
                (
                    question_id,
                    card_id,
                    prompt,
                    "由内部测评人员在首版实现核验阶段留给制卡 AI。",
                    "{} -> authoring-llm".format(requested_by),
                    timestamp,
                ),
            )
            if current_status == "implementation_ready":
                connection.execute(
                    """
                    UPDATE cards SET implementation_status = 'under_review',
                        implementation_reviewed_by = ?, implementation_reviewed_at = ?,
                        updated_at = ? WHERE card_id = ?
                    """,
                    (requested_by, timestamp, timestamp, card_id),
                )
            self._record_workflow_event(
                connection,
                card_id,
                "implementation_test_requested",
                requested_by,
                prompt,
                {
                    "question_id": question_id,
                    "from": current_status,
                    "to": "under_review",
                },
                timestamp,
            )

        detail = self.get_card(card_id)
        return next(
            item for item in detail["questions"] if item["question_id"] == question_id
        )

    def record_answer(
        self,
        question_id: str,
        answer: str,
        respondent: str = "human",
        resolution: str = ANSWERED,
    ) -> Dict[str, Any]:
        if resolution not in ANSWER_STATES:
            raise ValueError("unknown resolution: {}".format(resolution))
        answer = answer.strip()
        if not answer:
            raise ValueError("answer is required")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT card_id, category FROM questions WHERE question_id = ?",
                (question_id,),
            ).fetchone()
            if row is None:
                raise KeyError("question not found: {}".format(question_id))
            cursor = connection.execute(
                """
                INSERT INTO answers(question_id, resolution, answer, respondent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    resolution,
                    answer,
                    respondent.strip() or "human",
                    _now(),
                ),
            )
            answer_id = cursor.lastrowid
            card_id = str(row["card_id"])
            if str(row["category"]) == "implementation_test":
                connection.execute(
                    "UPDATE cards SET updated_at = ? WHERE card_id = ?",
                    (_now(), card_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE cards SET generation_approved = 0, generation_approved_by = '',
                        generation_approved_at = NULL, implementation_status = 'not_started',
                        implementation_reviewed_by = '', implementation_reviewed_at = NULL,
                        implementation_evidence_json = '{}', updated_at = ?
                    WHERE card_id = ?
                    """,
                    (_now(), card_id),
                )
        questions: List[Dict[str, Any]] = self.get_card(card_id)["questions"]
        question = next(
            item
            for item in questions
            if item["question_id"] == question_id
        )
        question["recorded_answer_id"] = answer_id
        return question

    def approve_generation(
        self,
        card_id: str,
        reviewer: str,
        *,
        approved: bool = True,
        note: str = "",
    ) -> Dict[str, Any]:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("generation approval requires a reviewer")
        card = self.get_card(card_id)
        if approved and not card["authoring_ready"]:
            raise ValueError("card authoring questions are not ready for approval")
        if bool(card["generation_approved"]) == approved:
            return card
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE cards SET generation_approved = ?, generation_approved_by = ?,
                    generation_approved_at = ?, implementation_status = 'not_started',
                    implementation_reviewed_by = '', implementation_reviewed_at = NULL,
                    implementation_evidence_json = '{}', updated_at = ?
                WHERE card_id = ?
                """,
                (
                    int(approved),
                    reviewer if approved else "",
                    timestamp if approved else None,
                    timestamp,
                    card_id,
                ),
            )
            self._record_workflow_event(
                connection,
                card_id,
                "generation_approved" if approved else "generation_approval_revoked",
                reviewer,
                note,
                {"approved": approved},
                timestamp,
            )
        return self.get_card(card_id)

    def approve_zero_question_cards(
        self,
        reviewer: str,
        *,
        note: str = "",
    ) -> Dict[str, Any]:
        """Approve every in-scope, completed card that has never raised a question."""
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("generation approval requires a reviewer")
        timestamp = _now()
        approved_card_ids: List[str] = []
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT c.card_id
                FROM cards c
                WHERE c.in_scope = 1
                  AND c.interview_complete = 1
                  AND c.generation_approved = 0
                  AND NOT EXISTS (
                      SELECT 1 FROM questions q WHERE q.card_id = c.card_id
                  )
                ORDER BY c.card_id
                """
            ).fetchall()
            for row in rows:
                card_id = str(row["card_id"])
                cursor = connection.execute(
                    """
                    UPDATE cards
                    SET generation_approved = 1, generation_approved_by = ?,
                        generation_approved_at = ?, implementation_status = 'not_started',
                        implementation_reviewed_by = '', implementation_reviewed_at = NULL,
                        implementation_evidence_json = '{}', updated_at = ?
                    WHERE card_id = ?
                      AND in_scope = 1
                      AND interview_complete = 1
                      AND generation_approved = 0
                      AND NOT EXISTS (
                          SELECT 1 FROM questions q WHERE q.card_id = cards.card_id
                      )
                    """,
                    (reviewer, timestamp, timestamp, card_id),
                )
                if cursor.rowcount != 1:
                    continue
                approved_card_ids.append(card_id)
                self._record_workflow_event(
                    connection,
                    card_id,
                    "generation_approved",
                    reviewer,
                    note,
                    {
                        "approved": True,
                        "bulk": True,
                        "eligibility": "interview_complete_and_zero_questions",
                    },
                    timestamp,
                )
        return {
            "approved_count": len(approved_card_ids),
            "card_ids": approved_card_ids,
        }

    def set_implementation_status(
        self,
        card_id: str,
        status: str,
        reviewer: str,
        *,
        evidence: Optional[Mapping[str, Any]] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        if status not in IMPLEMENTATION_STATUSES:
            raise ValueError("unknown implementation status: {}".format(status))
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("implementation transition requires a reviewer")
        card = self.get_card(card_id)
        current = str(card["implementation_status"])
        if status == current:
            return card
        if status not in IMPLEMENTATION_TRANSITIONS[current]:
            raise ValueError(
                "invalid implementation transition: {} -> {}".format(current, status)
            )
        if not card["ready_to_generate"]:
            raise ValueError("card must have human generation approval first")
        normalized_evidence = dict(evidence or {})
        if status == "implementation_ready":
            missing_evidence = sorted(
                field
                for field in IMPLEMENTATION_READY_EVIDENCE_FIELDS
                if not normalized_evidence.get(field)
            )
            if missing_evidence:
                raise ValueError(
                    "implementation_ready requires evidence fields: {}".format(
                        ", ".join(missing_evidence)
                    )
                )
        timestamp = _now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE cards SET implementation_status = ?, implementation_reviewed_by = ?,
                    implementation_reviewed_at = ?, implementation_evidence_json = ?,
                    updated_at = ? WHERE card_id = ?
                """,
                (
                    status,
                    reviewer,
                    timestamp,
                    json.dumps(
                        normalized_evidence,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    timestamp,
                    card_id,
                ),
            )
            self._record_workflow_event(
                connection,
                card_id,
                "implementation_status_changed",
                reviewer,
                note,
                {"from": current, "to": status, "evidence": normalized_evidence},
                timestamp,
            )
        return self.get_card(card_id)

    def list_workflow_events(self, card_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM card_workflow_events WHERE card_id = ? ORDER BY event_id",
                (card_id,),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            try:
                event["metadata"] = json.loads(event.pop("metadata_json"))
            except json.JSONDecodeError:
                event["metadata"] = {}
            events.append(event)
        return events

    @staticmethod
    def _record_workflow_event(
        connection: sqlite3.Connection,
        card_id: str,
        event_type: str,
        actor: str,
        note: str,
        metadata: Mapping[str, Any],
        timestamp: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO card_workflow_events(
                card_id, event_type, actor, note, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                event_type,
                actor,
                note.strip(),
                json.dumps(
                    dict(metadata),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                timestamp,
            ),
        )

    def record_ai_assessment(
        self,
        question_id: str,
        answer: str,
        *,
        reasoning: str,
        confidence: str,
        disposition: str = AI_CANDIDATE_ANSWER,
        researched_by: str = "authoring-ai",
        sources: Sequence[Mapping[str, Any]] = (),
        assessment_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if disposition not in AI_DISPOSITIONS:
            raise ValueError("unknown AI disposition: {}".format(disposition))
        if confidence not in AI_CONFIDENCE:
            raise ValueError("unknown AI confidence: {}".format(confidence))
        answer = answer.strip()
        if not answer:
            raise ValueError("AI candidate answer is required")
        normalized_sources = self._normalize_ai_sources(sources)
        key = (assessment_key or uuid.uuid4().hex).strip()
        if not key:
            raise ValueError("assessment_key is required")
        timestamp = _now()
        reused = False
        with self._connection() as connection:
            question_row = connection.execute(
                "SELECT card_id FROM questions WHERE question_id = ?", (question_id,)
            ).fetchone()
            if question_row is None:
                raise KeyError("question not found: {}".format(question_id))
            existing = connection.execute(
                "SELECT question_id FROM ai_assessments WHERE assessment_key = ?", (key,)
            ).fetchone()
            if existing is not None:
                if str(existing["question_id"]) != question_id:
                    raise ValueError("assessment_key already belongs to another question")
                card_id = str(question_row["card_id"])
                assessment_id = None
                reused = True
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO ai_assessments(
                        assessment_key, question_id, disposition, answer, reasoning,
                        confidence, researched_by, sources_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        question_id,
                        disposition,
                        answer,
                        reasoning.strip(),
                        confidence,
                        researched_by.strip() or "authoring-ai",
                        json.dumps(
                            normalized_sources,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        timestamp,
                    ),
                )
                assessment_id = cursor.lastrowid
                card_id = str(question_row["card_id"])
                connection.execute(
                    "UPDATE cards SET updated_at = ? WHERE card_id = ?", (timestamp, card_id)
                )
        questions: List[Dict[str, Any]] = self.get_card(card_id)["questions"]
        question: Dict[str, Any] = next(
            item
            for item in questions
            if item["question_id"] == question_id
        )
        if reused:
            question["assessment_reused"] = True
        else:
            question["recorded_assessment_id"] = assessment_id
        return question

    @staticmethod
    def _normalize_ai_sources(
        sources: Sequence[Mapping[str, Any]],
    ) -> List[Dict[str, str]]:
        normalized = []
        for source in sources:
            if not isinstance(source, Mapping):
                raise ValueError("AI sources must be objects")
            url = str(source.get("url", "")).strip()
            title = str(source.get("title", "")).strip()
            source_type = str(source.get("source_type", "other")).strip() or "other"
            if not url.startswith(("https://", "http://")):
                raise ValueError("AI source URL must use http or https")
            if not title:
                raise ValueError("AI source title is required")
            if source_type not in AI_SOURCE_TYPES:
                raise ValueError("unknown AI source type: {}".format(source_type))
            normalized.append(
                {
                    "url": url,
                    "title": title,
                    "source_type": source_type,
                    "claim": str(source.get("claim", "")).strip(),
                    "retrieved_at": str(source.get("retrieved_at", "")).strip(),
                }
            )
        return normalized

    def list_cards(self) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                WITH latest_answers AS (
                    SELECT a.question_id, a.resolution
                    FROM answers a
                    JOIN (
                        SELECT question_id, MAX(answer_id) AS answer_id
                        FROM answers
                        GROUP BY question_id
                    ) latest ON latest.answer_id = a.answer_id
                )
                SELECT
                    c.*,
                    COUNT(q.question_id) AS question_count,
                    COALESCE(SUM(CASE
                        WHEN latest_answers.resolution = 'answered' THEN 1 ELSE 0
                    END), 0) AS answered_count,
                    COALESCE(SUM(CASE
                        WHEN q.blocking = 1
                         AND COALESCE(latest_answers.resolution, 'open') != 'answered'
                        THEN 1 ELSE 0
                    END), 0) AS unresolved_blocking_count,
                    COALESCE(SUM(CASE
                        WHEN q.blocking = 1
                         AND latest_answers.resolution = 'needs_verification'
                        THEN 1 ELSE 0
                    END), 0) AS needs_verification_count
                FROM cards c
                LEFT JOIN questions q ON q.card_id = c.card_id
                LEFT JOIN latest_answers ON latest_answers.question_id = q.question_id
                WHERE c.in_scope = 1
                GROUP BY c.card_id
                ORDER BY c.updated_at DESC, c.card_id
                """
            ).fetchall()
        cards: List[Dict[str, Any]] = []
        for row in rows:
            card = dict(row)
            card["interview_complete"] = bool(card["interview_complete"])
            card["in_scope"] = bool(card["in_scope"])
            card["generation_approved"] = bool(card["generation_approved"])
            card["authoring_ready"] = bool(card["interview_complete"]) and not int(
                card["unresolved_blocking_count"]
            )
            card["ready_to_generate"] = bool(card["authoring_ready"]) and bool(
                card["generation_approved"]
            )
            card["ready_for_research"] = bool(card["ready_to_generate"]) and (
                card["implementation_status"] == "implementation_ready"
            )
            cards.append(self._card_summary(card))
        return cards

    def get_card(self, card_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            card_row = connection.execute(
                "SELECT * FROM cards WHERE card_id = ?", (card_id,)
            ).fetchone()
            if card_row is None:
                raise KeyError("card not found: {}".format(card_id))
            question_rows = connection.execute(
                "SELECT * FROM questions WHERE card_id = ? ORDER BY created_at, question_id",
                (card_id,),
            ).fetchall()
            answer_rows = connection.execute(
                """
                SELECT a.*
                FROM answers a
                JOIN questions q ON q.question_id = a.question_id
                WHERE q.card_id = ?
                ORDER BY a.answer_id
                """,
                (card_id,),
            ).fetchall()
            assessment_rows = connection.execute(
                """
                SELECT a.*
                FROM ai_assessments a
                JOIN questions q ON q.question_id = a.question_id
                WHERE q.card_id = ?
                ORDER BY a.assessment_id
                """,
                (card_id,),
            ).fetchall()

        histories: Dict[str, List[Dict[str, Any]]] = {}
        for row in answer_rows:
            item = dict(row)
            histories.setdefault(str(row["question_id"]), []).append(item)

        assessment_histories: Dict[str, List[Dict[str, Any]]] = {}
        for row in assessment_rows:
            item = dict(row)
            try:
                item["sources"] = json.loads(item.pop("sources_json"))
            except json.JSONDecodeError:
                item["sources"] = []
            assessment_histories.setdefault(str(row["question_id"]), []).append(item)

        questions: List[Dict[str, Any]] = []
        for row in question_rows:
            item = dict(row)
            item["blocking"] = bool(item["blocking"])
            history = histories.get(str(item["question_id"]), [])
            item["answers"] = history
            item["current_resolution"] = history[-1]["resolution"] if history else "open"
            item["current_answer"] = history[-1]["answer"] if history else None
            assessments = assessment_histories.get(str(item["question_id"]), [])
            item["ai_assessments"] = assessments
            item["current_ai_assessment"] = assessments[-1] if assessments else None
            questions.append(item)

        card = dict(card_row)
        card["interview_complete"] = bool(card["interview_complete"])
        card["in_scope"] = bool(card["in_scope"])
        card["generation_approved"] = bool(card["generation_approved"])
        try:
            card["source_data"] = json.loads(card.pop("source_data_json"))
        except json.JSONDecodeError:
            card["source_data"] = {}
        try:
            card["implementation_evidence"] = json.loads(
                card.pop("implementation_evidence_json")
            )
        except json.JSONDecodeError:
            card["implementation_evidence"] = {}
        card["questions"] = questions
        card["workflow_events"] = self.list_workflow_events(card_id)
        card.update(
            self._gate(
                questions,
                bool(card["interview_complete"]),
                bool(card["generation_approved"]),
                str(card["implementation_status"]),
            )
        )
        return card

    def get_source_card(self, card_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM source_cards WHERE card_id = ?", (card_id,)
            ).fetchone()
        if row is None:
            raise KeyError("source card not found: {}".format(card_id))
        card = dict(row)
        card["collectible"] = bool(card["collectible"])
        card["in_scope"] = bool(card["in_scope"])
        try:
            card["source_data"] = json.loads(card.pop("source_data_json"))
        except json.JSONDecodeError:
            card["source_data"] = {}
        return card

    @staticmethod
    def _gate(
        questions: Sequence[Mapping[str, Any]],
        interview_complete: bool,
        generation_approved: bool = False,
        implementation_status: str = "not_started",
    ) -> Dict[str, Any]:
        unresolved = [
            item
            for item in questions
            if bool(item["blocking"]) and item["current_resolution"] != ANSWERED
        ]
        needs_verification = [
            item for item in unresolved if item["current_resolution"] == NEEDS_VERIFICATION
        ]
        authoring_ready = interview_complete and not unresolved
        ready_to_generate = authoring_ready and generation_approved
        return {
            "authoring_ready": authoring_ready,
            "ready_to_generate": ready_to_generate,
            "ready_for_research": ready_to_generate
            and implementation_status == "implementation_ready",
            "unresolved_blocking_count": len(unresolved),
            "needs_verification_count": len(needs_verification),
            "question_count": len(questions),
            "answered_count": sum(
                item["current_resolution"] == ANSWERED for item in questions
            ),
        }

    @staticmethod
    def _card_summary(card: Mapping[str, Any]) -> Dict[str, Any]:
        keys = (
            "card_id",
            "name",
            "source_text",
            "card_set",
            "card_class",
            "card_type",
            "cost",
            "source_version",
            "source_kind",
            "in_scope",
            "interview_complete",
            "generation_approved",
            "generation_approved_by",
            "generation_approved_at",
            "implementation_status",
            "implementation_reviewed_by",
            "implementation_reviewed_at",
            "created_at",
            "updated_at",
            "authoring_ready",
            "ready_to_generate",
            "ready_for_research",
            "unresolved_blocking_count",
            "needs_verification_count",
            "question_count",
            "answered_count",
        )
        return {key: card[key] for key in keys}
