from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from urllib.request import Request, urlopen

from .store import ReviewStore

HEARTHSTONEJSON_API = "https://api.hearthstonejson.com/v1"
FORMAT_REVISION = "year-of-the-scarab-2026-08-27"
STANDARD_SET_IDS = (
    "CORE",
    "EMERALD_DREAM",
    "THE_LOST_CITY",
    "TIME_TRAVEL",
    "CATACLYSM",
    "ESCAPEFROM_VIOLET_HOLD",
)
STANDARD_SET_NAMES_ZH = {
    "CORE": "核心",
    "EMERALD_DREAM": "漫游翡翠梦境",
    "THE_LOST_CITY": "安戈洛龟途",
    "TIME_TRAVEL": "穿越时间流",
    "CATACLYSM": "大灾变",
    "ESCAPEFROM_VIOLET_HOLD": "逃离紫罗兰监狱",
}
SCOPE_SOURCES = (
    "https://hearthstone.blizzard.com/en-us/expansions-adventures",
    "https://hearthstone.blizzard.com/en-us/news/24267727",
    "https://hearthstone.blizzard.com/en-us/news/24293283/364-patch-notes",
)

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_BUILD = re.compile(r"/v1/([^/]+)/")
_SEMANTIC_KEYS = (
    "id",
    "dbfId",
    "name",
    "text",
    "collectionText",
    "targetingArrowText",
    "type",
    "set",
    "cardClass",
    "classes",
    "multiClassGroup",
    "cost",
    "attack",
    "health",
    "durability",
    "armor",
    "rarity",
    "race",
    "races",
    "spellSchool",
    "mechanics",
    "referencedTags",
    "runes",
    "elite",
    "isMiniSet",
)


@dataclass(frozen=True)
class StandardCatalog:
    build: str
    records: List[Dict[str, Any]]
    zh_source_url: str
    en_source_url: str


def plain_card_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = text.replace("[x]", "")
    text = _TAG.sub("", text)
    text = text.replace("$", "").replace("#", "")
    return _SPACE.sub(" ", text).strip()


def _download_cards(locale: str, build: str) -> Tuple[List[Dict[str, Any]], str, str]:
    url = "{}/{}/{}/cards.json".format(HEARTHSTONEJSON_API, build, locale)
    request = Request(url, headers={"User-Agent": "CardLab/0.1 standard-card importer"})
    with urlopen(request, timeout=90) as response:
        payload = json.load(response)
        resolved_url = response.geturl()
    if not isinstance(payload, list):
        raise ValueError("HearthstoneJSON response must be a card list")
    match = _BUILD.search(resolved_url)
    if match is None:
        raise ValueError("could not resolve HearthstoneJSON build from {}".format(resolved_url))
    return payload, match.group(1), resolved_url


def _semantic_data(card: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: card[key] for key in _SEMANTIC_KEYS if key in card}


def build_standard_catalog(
    zh_cards: Sequence[Mapping[str, Any]],
    en_cards: Sequence[Mapping[str, Any]],
    *,
    build: str,
    zh_source_url: str,
    en_source_url: str,
) -> StandardCatalog:
    selected = [card for card in zh_cards if card.get("set") in STANDARD_SET_IDS]
    present_sets = {str(card.get("set")) for card in selected}
    missing_sets = set(STANDARD_SET_IDS) - present_sets
    if missing_sets:
        raise ValueError("standard source is missing sets: {}".format(sorted(missing_sets)))
    english = {str(card.get("id")): card for card in en_cards}
    records: List[Dict[str, Any]] = []
    for card in selected:
        card_id = str(card.get("id", ""))
        if not card_id or not card.get("name"):
            raise ValueError("standard card is missing id or name")
        en_card = english.get(card_id, {})
        classes = card.get("classes") or []
        card_class = str(card.get("cardClass") or "/".join(classes) or "UNKNOWN")
        source_data = _semantic_data(card)
        source_data.update(
            {
                "name_en": str(en_card.get("name", "")),
                "text_en": plain_card_text(en_card.get("text", "")),
                "set_name_zh": STANDARD_SET_NAMES_ZH[str(card["set"])],
                "format_revision": FORMAT_REVISION,
                "scope_sources": list(SCOPE_SOURCES),
                "zh_source_url": zh_source_url,
                "en_source_url": en_source_url,
            }
        )
        records.append(
            {
                "card_id": card_id,
                "name": str(card["name"]),
                "source_text": plain_card_text(card.get("text", "")),
                "collectible": bool(card.get("collectible")),
                "card_set": str(card["set"]),
                "card_class": card_class,
                "card_type": str(card.get("type", "UNKNOWN")),
                "cost": card.get("cost"),
                "source_data": source_data,
            }
        )
    records.sort(key=lambda item: str(item["card_id"]))
    return StandardCatalog(
        build=build,
        records=records,
        zh_source_url=zh_source_url,
        en_source_url=en_source_url,
    )


def fetch_standard_catalog(build: str = "latest") -> StandardCatalog:
    zh_cards, resolved_build, zh_url = _download_cards("zhCN", build)
    en_cards, en_build, en_url = _download_cards("enUS", resolved_build)
    if resolved_build != en_build:
        raise ValueError(
            "locale builds do not match: zhCN={} enUS={}".format(resolved_build, en_build)
        )
    return build_standard_catalog(
        zh_cards,
        en_cards,
        build=resolved_build,
        zh_source_url=zh_url,
        en_source_url=en_url,
    )


def import_current_standard(
    store: ReviewStore,
    build: str = "latest",
) -> Dict[str, Any]:
    catalog = fetch_standard_catalog(build)
    stats = store.import_standard_catalog(
        catalog.records,
        source_version=catalog.build,
        format_revision=FORMAT_REVISION,
    )
    return {
        "build": catalog.build,
        "format_revision": FORMAT_REVISION,
        "set_ids": list(STANDARD_SET_IDS),
        "zh_source_url": catalog.zh_source_url,
        "en_source_url": catalog.en_source_url,
        **stats,
    }
