import unittest

from cardlab.authoring.importer import (
    STANDARD_SET_IDS,
    build_standard_catalog,
    plain_card_text,
)


class StandardImporterTests(unittest.TestCase):
    def test_plain_card_text_removes_layout_markup_without_losing_words(self) -> None:
        self.assertEqual(
            plain_card_text("[x]<b>战吼：</b>造成$6点\n伤害。"),
            "战吼：造成6点 伤害。",
        )

    def test_catalog_keeps_collectibles_and_noncollectible_dependencies(self) -> None:
        zh_cards = []
        en_cards = []
        for index, card_set in enumerate(STANDARD_SET_IDS):
            card_id = "TEST_{:02d}".format(index)
            collectible = index != 1
            zh_cards.append(
                {
                    "id": card_id,
                    "dbfId": index,
                    "name": "测试牌{}".format(index),
                    "text": "<b>效果：</b>测试。",
                    "set": card_set,
                    "cardClass": "MAGE",
                    "type": "SPELL",
                    "cost": index,
                    "collectible": collectible,
                }
            )
            en_cards.append(
                {
                    "id": card_id,
                    "name": "Test Card {}".format(index),
                    "text": "<b>Effect:</b> Test.",
                }
            )

        catalog = build_standard_catalog(
            zh_cards,
            en_cards,
            build="250339",
            zh_source_url="https://example.test/zhCN/cards.json",
            en_source_url="https://example.test/enUS/cards.json",
        )

        self.assertEqual(len(catalog.records), len(STANDARD_SET_IDS))
        self.assertEqual(sum(card["collectible"] for card in catalog.records), 5)
        first = catalog.records[0]
        self.assertEqual(first["source_text"], "效果：测试。")
        self.assertTrue(first["source_data"]["name_en"].startswith("Test Card"))

    def test_catalog_adds_cross_set_dependencies_without_queueing_old_collectibles(self) -> None:
        zh_cards = [
            {
                "id": "STD_{:03d}".format(index),
                "name": "标准卡",
                "set": card_set,
                "type": "SPELL",
                "collectible": True,
            }
            for index, card_set in enumerate(STANDARD_SET_IDS)
        ]
        zh_cards.extend(
            [
                {
                    "id": "BAR_878",
                    "name": "旧版战地医师老兵",
                    "set": "THE_BARRENS",
                    "type": "MINION",
                    "collectible": True,
                },
                {
                    "id": "BAR_878t",
                    "name": "战地医师",
                    "set": "THE_BARRENS",
                    "type": "MINION",
                },
                {
                    "id": "CS2_101t",
                    "name": "白银之手新兵",
                    "set": "BASIC",
                    "type": "MINION",
                },
                {
                    "id": "BG_ONLY",
                    "name": "酒馆战棋随从",
                    "set": "BATTLEGROUNDS",
                    "type": "MINION",
                },
            ]
        )

        catalog = build_standard_catalog(
            zh_cards,
            [],
            build="250339",
            zh_source_url="https://example.test/zhCN/cards.json",
            en_source_url="https://example.test/enUS/cards.json",
        )

        card_ids = {card["card_id"] for card in catalog.records}
        self.assertIn("BAR_878t", card_ids)
        self.assertIn("CS2_101t", card_ids)
        self.assertIn("BAR_878", card_ids)
        self.assertNotIn("BG_ONLY", card_ids)
        old_parent = next(card for card in catalog.records if card["card_id"] == "BAR_878")
        token = next(card for card in catalog.records if card["card_id"] == "BAR_878t")
        self.assertTrue(old_parent["collectible"])
        self.assertFalse(old_parent["queue_card"])
        self.assertFalse(token["collectible"])
        self.assertFalse(token["queue_card"])

    def test_catalog_rejects_incomplete_standard_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing sets"):
            build_standard_catalog(
                [{"id": "ONLY", "name": "唯一", "set": "CORE"}],
                [],
                build="1",
                zh_source_url="https://example.test/zh",
                en_source_url="https://example.test/en",
            )


if __name__ == "__main__":
    unittest.main()
