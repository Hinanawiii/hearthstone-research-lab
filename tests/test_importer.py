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
