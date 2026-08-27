import sqlite3
import tempfile
import unittest
from pathlib import Path

from cardlab.authoring.research_prompt import make_question_research_prompt
from cardlab.authoring.store import (
    AI_CANDIDATE_ANSWER,
    AI_NEEDS_VERIFICATION,
    ANSWERED,
    NEEDS_VERIFICATION,
    ReviewStore,
)


class AuthoringReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temp_dir.name) / "review.db")
        self.store.upsert_card("CAP_805", "灵质处决", "消灭所有随从。")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generation_waits_for_completed_interview_and_all_blocking_answers(self) -> None:
        questions = self.store.add_questions(
            "CAP_805",
            [
                {
                    "question_id": "snapshot",
                    "category": "ownership",
                    "prompt": "被偷取的灵质保留谁的随从快照？",
                },
                {
                    "question_id": "wording",
                    "category": "copy",
                    "prompt": "保存卡牌原文吗？",
                    "blocking": False,
                },
            ],
        )
        self.assertEqual(len(questions), 2)
        self.assertFalse(self.store.get_card("CAP_805")["ready_to_generate"])

        self.store.set_interview_complete("CAP_805", True)
        self.assertFalse(self.store.get_card("CAP_805")["ready_to_generate"])

        self.store.record_answer(
            "snapshot",
            "需要客户端确认",
            resolution=NEEDS_VERIFICATION,
        )
        pending = self.store.get_card("CAP_805")
        self.assertEqual(pending["needs_verification_count"], 1)
        self.assertFalse(pending["ready_to_generate"])

        self.store.record_answer(
            "snapshot",
            "保留原接收者的随从快照",
            respondent="tester",
            resolution=ANSWERED,
        )
        ready = self.store.get_card("CAP_805")
        self.assertTrue(ready["authoring_ready"])
        self.assertFalse(ready["ready_to_generate"])
        self.assertEqual(ready["answered_count"], 1)
        self.assertEqual(len(ready["questions"][0]["answers"]), 2)

        approved = self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertTrue(approved["ready_to_generate"])

        approval_event_count = len(approved["workflow_events"])
        approved_again = self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertEqual(len(approved_again["workflow_events"]), approval_event_count)
        self.assertFalse(approved["ready_for_research"])
        self.store.set_implementation_status("CAP_805", "generated", "generator")
        self.store.set_implementation_status("CAP_805", "under_review", "reviewer")
        with self.assertRaisesRegex(ValueError, "human_scenario_review"):
            self.store.set_implementation_status(
                "CAP_805",
                "implementation_ready",
                "reviewer",
                evidence={"code_review": "approved", "automated_tests": "passed"},
            )
        implemented = self.store.set_implementation_status(
            "CAP_805",
            "implementation_ready",
            "reviewer",
            evidence={
                "code_review": "approved",
                "automated_tests": "passed",
                "human_scenario_review": "approved",
            },
        )
        self.assertTrue(implemented["ready_for_research"])
        self.assertEqual(len(implemented["workflow_events"]), 4)

    def test_new_question_reopens_completed_interview(self) -> None:
        self.store.set_interview_complete("CAP_805", True)
        self.assertTrue(self.store.get_card("CAP_805")["authoring_ready"])
        self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertTrue(self.store.get_card("CAP_805")["ready_to_generate"])

        self.store.add_questions(
            "CAP_805",
            [{"question_id": "full-hand", "prompt": "满手牌时是否生成灵质？"}],
        )
        card = self.store.get_card("CAP_805")
        self.assertFalse(card["interview_complete"])
        self.assertFalse(card["ready_to_generate"])
        self.assertFalse(card["generation_approved"])

    def test_latest_answer_controls_gate_without_losing_history(self) -> None:
        self.store.add_questions(
            "CAP_805",
            [{"question_id": "order", "prompt": "死亡与生成手牌的顺序是什么？"}],
        )
        self.store.record_answer("order", "先完成死亡结算")
        self.store.set_interview_complete("CAP_805", True)
        self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertTrue(self.store.get_card("CAP_805")["ready_to_generate"])

        self.store.record_answer(
            "order",
            "新证据冲突，重新实测",
            resolution=NEEDS_VERIFICATION,
        )
        card = self.store.get_card("CAP_805")
        self.assertFalse(card["ready_to_generate"])
        self.assertEqual(len(card["questions"][0]["answers"]), 2)

    def test_ai_candidate_is_archived_but_cannot_unlock_generation(self) -> None:
        self.store.add_questions(
            "CAP_805",
            [{"question_id": "predamage", "prompt": "预伤害扳机何时结算？"}],
        )
        self.store.set_interview_complete("CAP_805", True)
        question = self.store.record_ai_assessment(
            "predamage",
            "候选结论：先运行预伤害扳机，再扣减生命值。",
            reasoning="进阶规则集把它列在伤害生效之前。",
            confidence="medium",
            disposition=AI_CANDIDATE_ANSWER,
            researched_by="authoring-research-test",
            assessment_key="predamage-research-v1",
            sources=[
                {
                    "url": "https://example.test/advanced-rules",
                    "title": "Advanced rules",
                    "source_type": "maintained_rules",
                    "claim": "Predamage triggers resolve before health changes.",
                    "retrieved_at": "2026-08-27",
                }
            ],
        )

        self.assertEqual(question["answers"], [])
        self.assertEqual(question["current_resolution"], "open")
        self.assertEqual(
            question["current_ai_assessment"]["disposition"], AI_CANDIDATE_ANSWER
        )
        self.assertEqual(
            question["current_ai_assessment"]["sources"][0]["source_type"],
            "maintained_rules",
        )
        self.assertFalse(self.store.get_card("CAP_805")["ready_to_generate"])

        reused = self.store.record_ai_assessment(
            "predamage",
            "候选结论：先运行预伤害扳机，再扣减生命值。",
            reasoning="same evidence",
            confidence="medium",
            assessment_key="predamage-research-v1",
        )
        self.assertTrue(reused["assessment_reused"])
        self.assertEqual(len(reused["ai_assessments"]), 1)

        self.store.record_answer("predamage", "人工确认该结论", resolution=ANSWERED)
        self.assertTrue(self.store.get_card("CAP_805")["authoring_ready"])
        self.assertFalse(self.store.get_card("CAP_805")["ready_to_generate"])
        self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertTrue(self.store.get_card("CAP_805")["ready_to_generate"])

    def test_zero_question_card_requires_explicit_human_generation_approval(self) -> None:
        self.store.set_interview_complete("CAP_805", True)
        card = self.store.get_card("CAP_805")
        self.assertTrue(card["authoring_ready"])
        self.assertFalse(card["ready_to_generate"])

        approved = self.store.approve_generation("CAP_805", "human-reviewer")
        self.assertTrue(approved["ready_to_generate"])

        revoked = self.store.approve_generation(
            "CAP_805", "human-reviewer", approved=False, note="recheck needed"
        )
        self.assertFalse(revoked["ready_to_generate"])

    def test_ai_can_recommend_client_verification_and_prompt_includes_evidence(self) -> None:
        self.store.add_questions(
            "CAP_805",
            [{"question_id": "timing", "prompt": "最后一点耐久何时离场？"}],
        )
        question = self.store.record_ai_assessment(
            "timing",
            "现有资料不足以确定最后一点耐久的精确离场节点。",
            reasoning="卡面和规则集没有直接覆盖该交互。",
            confidence="low",
            disposition=AI_NEEDS_VERIFICATION,
            assessment_key="timing-research-v1",
        )
        card = self.store.get_card("CAP_805")
        prompt = make_question_research_prompt(card, question)

        self.assertIn("Predamage triggers", prompt)
        self.assertIn("最后一点耐久何时离场", prompt)
        self.assertIn("prior_ai_assessments", prompt)
        self.assertEqual(question["current_resolution"], "open")

    def test_ai_assessment_rejects_untrusted_source_protocol(self) -> None:
        self.store.add_questions(
            "CAP_805", [{"question_id": "unsafe-source", "prompt": "来源是什么？"}]
        )
        with self.assertRaisesRegex(ValueError, "http or https"):
            self.store.record_ai_assessment(
                "unsafe-source",
                "候选答案",
                reasoning="",
                confidence="high",
                sources=[
                    {
                        "url": "javascript:alert(1)",
                        "title": "bad source",
                        "source_type": "other",
                    }
                ],
            )

    def test_changing_source_text_reopens_interview(self) -> None:
        self.store.set_interview_complete("CAP_805", True)
        self.store.upsert_card("CAP_805", "灵质处决", "一份经过修订的卡牌文本。")
        card = self.store.get_card("CAP_805")
        self.assertFalse(card["interview_complete"])
        self.assertFalse(card["ready_to_generate"])

    def test_standard_import_queues_collectibles_and_catalogs_tokens(self) -> None:
        records = [
            {
                "card_id": "JAIL_205",
                "name": "蟊贼脏鼠",
                "source_text": "回合结束时偷牌。",
                "collectible": True,
                "card_set": "ESCAPEFROM_VIOLET_HOLD",
                "card_class": "NEUTRAL",
                "card_type": "MINION",
                "cost": 4,
                "source_data": {"dbfId": 131316},
            },
            {
                "card_id": "CAP_805t",
                "name": "灵质",
                "source_text": "重新召唤被本次处决消灭的所有友方随从。",
                "collectible": False,
                "card_set": "ESCAPEFROM_VIOLET_HOLD",
                "card_class": "PRIEST",
                "card_type": "SPELL",
                "cost": 3,
                "source_data": {"dbfId": 127118},
            },
        ]
        report = self.store.import_standard_catalog(
            records,
            source_version="250339",
            format_revision="year-of-the-scarab-2026-08-27",
        )

        self.assertEqual(report["catalog_total"], 2)
        self.assertEqual(report["collectible_total"], 1)
        queued = {card["card_id"] for card in self.store.list_cards()}
        self.assertIn("JAIL_205", queued)
        self.assertNotIn("CAP_805t", queued)
        token = self.store.get_source_card("CAP_805t")
        self.assertFalse(token["collectible"])
        self.assertEqual(token["source_data"]["dbfId"], 127118)

    def test_next_standard_import_hides_rotated_queue_cards_without_deleting_them(self) -> None:
        first = [
            {
                "card_id": "OLD_001",
                "name": "旧牌",
                "collectible": True,
                "source_data": {},
            }
        ]
        second = [
            {
                "card_id": "NEW_001",
                "name": "新牌",
                "collectible": True,
                "source_data": {},
            }
        ]
        self.store.import_standard_catalog(
            first, source_version="1", format_revision="standard-1"
        )
        report = self.store.import_standard_catalog(
            second, source_version="2", format_revision="standard-2"
        )

        self.assertEqual(report["queue_out_of_scope"], 1)
        active = {card["card_id"] for card in self.store.list_cards()}
        self.assertIn("NEW_001", active)
        self.assertNotIn("OLD_001", active)
        self.assertFalse(self.store.get_card("OLD_001")["in_scope"])


class AuthoringMigrationTests(unittest.TestCase):
    def test_legacy_review_database_adds_catalog_columns_before_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy.db"
            connection = sqlite3.connect(str(path))
            connection.execute(
                """
                CREATE TABLE cards (
                    card_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_text TEXT NOT NULL DEFAULT '',
                    interview_complete INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO cards VALUES (
                    'LEGACY_TEST', '旧记录', '旧文本', 0,
                    '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00'
                )
                """
            )
            connection.commit()
            connection.close()

            store = ReviewStore(path)
            card = store.get_card("LEGACY_TEST")
            self.assertTrue(card["in_scope"])
            self.assertEqual(card["source_kind"], "manual")


if __name__ == "__main__":
    unittest.main()
