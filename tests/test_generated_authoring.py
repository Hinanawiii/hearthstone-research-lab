import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from cardlab.authoring.generated import (
    GENERATED_CARDS,
    GENERATED_TOKEN_CARDS,
    generated_dependencies,
    runtime_registry,
)
from cardlab.authoring.generated.rlk_709 import (
    AUTHORING_METADATA,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.generated.runner import (
    build_review_artifact,
    stage_generated_card_for_review,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.authoring.store import ReviewStore


class GeneratedAuthoringTests(unittest.TestCase):
    def test_remorseless_winter_matches_the_approved_card_contract(self) -> None:
        card = GENERATED_CARDS["RLK_709"]
        self.assertEqual(card.cost, 4)
        self.assertEqual(
            [(effect.kind, effect.amount, effect.target) for effect in card.effects],
            [
                ("damage_all", 2, "enemy_characters"),
                ("draw", 1, "owner"),
            ],
        )
        self.assertEqual(AUTHORING_METADATA["source_version"], "250339")

    def test_remorseless_winter_review_scenario(self) -> None:
        scenario = build_review_scenario(runtime_registry(["RLK_709"]))
        before = scenario["before"]
        after = scenario["after"]
        before_players = {player["role_zh"]: player for player in before["players"]}
        after_players = {player["role_zh"]: player for player in after["players"]}
        before_enemy = before_players["敌方"]
        after_enemy = after_players["敌方"]
        after_own = after_players["我方"]

        self.assertEqual(before_enemy["hero"]["health"], 30)
        self.assertEqual(after_enemy["hero"]["health"], 28)
        self.assertEqual(len(before_enemy["zones"]["board"]), 2)
        self.assertEqual(len(after_enemy["zones"]["board"]), 1)
        self.assertEqual(after_enemy["zones"]["board"][0]["health"], 1)
        self.assertEqual(len(after_own["zones"]["board"]), 1)
        self.assertEqual(after_own["zones"]["board"][0]["health"], 1)
        self.assertEqual(after_own["resources"]["mana"], 6)
        self.assertEqual(after_own["zones"]["hand"]["count"], 1)
        self.assertEqual(after_own["zones"]["hand"]["cards"][0]["card_id"], "CS2_231")
        self.assertEqual(after["active_player_id"], before["viewer_player_id"])
        self.assertEqual(scenario["special_cases"][0]["kind"], "deck_change")
        self.assertEqual(scenario["special_cases"][0]["details"]["shuffled_count"], 0)

    def test_generated_cards_do_not_change_the_reference_deck(self) -> None:
        generated_ids = {
            "RLK_709",
            "CORE_DS1_185",
            "CORE_CS2_023",
            "CORE_CS2_179",
        }
        generated_ids.update(
            {
                "Core_CS2_200",
                "CORE_BT_701",
                "CORE_EX1_010",
                "CORE_GIL_558",
                "CORE_ULD_723",
                "CORE_NEW1_023",
                "CS3_038",
                "CORE_EX1_028",
                "CORE_LOOT_137",
                "CORE_ICC_038",
                "CORE_GVG_085",
                "CORE_AT_052",
                "CORE_DRG_079",
                "CORE_EX1_250",
            }
        )
        registry = runtime_registry(generated_ids)
        self.assertTrue(generated_ids <= set(registry))
        from cardlab.cards import DECK_CARD_IDS

        self.assertTrue(generated_ids.isdisjoint(DECK_CARD_IDS))

    def test_every_generated_dependency_has_a_runtime_definition(self) -> None:
        dependency_ids = set()
        for card_id in GENERATED_CARDS:
            dependency_ids.update(generated_dependencies(card_id))

        self.assertTrue(dependency_ids)
        self.assertTrue(set(GENERATED_TOKEN_CARDS) <= dependency_ids)
        self.assertEqual(generated_dependencies("CORE_BAR_878")["BAR_878t"].name, "战地医师")

    def test_parent_review_embeds_the_imported_derivative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "review.db")
            store.import_standard_catalog(
                [
                    {
                        "card_id": "CORE_BAR_878",
                        "name": "战地医师老兵",
                        "source_text": "在你施放一个神圣法术后，召唤一个2/2并具有吸血的医师。",
                        "collectible": True,
                    },
                    {
                        "card_id": "BAR_878t",
                        "name": "战地医师",
                        "source_text": "吸血",
                        "collectible": False,
                    },
                ],
                source_version="250339",
                format_revision="test",
            )
            store.set_interview_complete("CORE_BAR_878", True)
            store.approve_generation("CORE_BAR_878", "human-reviewer")

            artifact = build_review_artifact(store, "CORE_BAR_878")
            dependencies = artifact["implementation"]["dependencies"]

            self.assertEqual(len(dependencies), 1)
            self.assertEqual(dependencies[0]["card_id"], "BAR_878t")
            self.assertEqual(dependencies[0]["name_zh"], "战地医师")
            self.assertIn("战地医师（BAR_878t）", render_review_document_zh(artifact))

    def test_reused_legacy_card_uses_the_source_catalog_chinese_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "review.db")
            store.import_standard_catalog(
                [
                    {
                        "card_id": "CORE_EX1_559",
                        "name": "大法师安东尼达斯",
                        "source_text": "每当你施放一个法术，将一张“火球术”法术牌置入你的手牌。",
                        "collectible": True,
                        "queue_card": True,
                    },
                    {
                        "card_id": "CS2_029",
                        "name": "火球术",
                        "source_text": "造成6点伤害。",
                        "collectible": True,
                        "queue_card": False,
                    },
                ],
                source_version="250339",
                format_revision="test",
            )
            store.set_interview_complete("CORE_EX1_559", True)
            store.approve_generation("CORE_EX1_559", "human-reviewer")

            artifact = build_review_artifact(store, "CORE_EX1_559")

            self.assertEqual(artifact["implementation"]["dependencies"][0]["name_zh"], "火球术")

    def test_staging_requires_approval_and_stops_at_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = ReviewStore(root / "review.db")
            store.upsert_card(
                "RLK_709",
                "冷酷严冬",
                "对所有敌人造成2点伤害。抽一张牌。",
                source_version="250339",
            )
            store.set_interview_complete("RLK_709", True)
            with self.assertRaisesRegex(ValueError, "generation approval"):
                stage_generated_card_for_review(
                    store,
                    "RLK_709",
                    root / "artifact.json",
                    automated_tests="passed",
                )

            store.approve_generation("RLK_709", "human-reviewer")
            artifact = build_review_artifact(store, "RLK_709")
            self.assertEqual(artifact["schema_version"], REVIEW_SCHEMA_VERSION)
            self.assertEqual(artifact["locale"], "zh-CN")
            self.assertEqual(
                set(artifact),
                {"schema_version", "locale", "card", "implementation", "scenario"},
            )
            validate_review_document(artifact)
            rendered = render_review_document_zh(artifact, SCENARIO_CARD_NAMES_ZH)
            self.assertIn("冷酷严冬：群体伤害后抽牌", rendered)
            self.assertIn("操作前", rendered)
            self.assertIn("操作后", rendered)
            self.assertIn("特殊情况", rendered)
            self.assertIn("洗入数量=0", rendered)
            self.assertIn("小精灵（CS2_231）", rendered)
            self.assertIn("淡水鳄（CS2_120）", rendered)

            staged = stage_generated_card_for_review(
                store,
                "RLK_709",
                root / "artifact.json",
                automated_tests="passed",
                generation_usage={"model": "test-model", "total_tokens": 123},
            )

            self.assertEqual(staged["implementation_status"], "under_review")
            self.assertFalse(staged["ready_for_research"])
            self.assertEqual(staged["implementation_evidence"]["automated_tests"], "passed")
            self.assertEqual(
                staged["implementation_evidence"]["generation_usage"],
                {"model": "test-model", "total_tokens": 123},
            )
            self.assertEqual(
                staged["implementation_evidence"]["scenario_document"]["schema_version"],
                REVIEW_SCHEMA_VERSION,
            )
            self.assertEqual(staged["implementation_evidence"]["review_text_zh"], rendered)
            self.assertEqual(store.card_names_zh()["CS2_231"], "小精灵")
            self.assertEqual(len(store.list_cards()), 1)
            self.assertTrue((root / "artifact.json").is_file())
            self.assertEqual(
                (root / "review-summary.zh-CN.txt").read_text(encoding="utf-8"), rendered
            )
            self.assertEqual(
                [event["event_type"] for event in staged["workflow_events"][-2:]],
                ["implementation_status_changed", "implementation_status_changed"],
            )

    def test_review_schema_rejects_unknown_special_case_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "review.db")
            store.upsert_card(
                "RLK_709",
                "冷酷严冬",
                "对所有敌人造成2点伤害。抽一张牌。",
                source_version="250339",
            )
            store.set_interview_complete("RLK_709", True)
            store.approve_generation("RLK_709", "human-reviewer")
            artifact = deepcopy(build_review_artifact(store, "RLK_709"))
            artifact["scenario"]["special_cases"][0]["kind"] = "unknown_rule"

            with self.assertRaisesRegex(ValueError, "unknown special case kind"):
                validate_review_document(artifact)


if __name__ == "__main__":
    unittest.main()
