from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Sequence

REVIEW_SCHEMA_VERSION = "cardlab.authoring-review.v1"
SPECIAL_CASE_KINDS = {
    "secret_zone",
    "deck_change",
    "cost_modification",
    "forge",
    "corrupt",
    "location_cooldown",
    "special_tags",
    "titan_abilities",
}

SPECIAL_CASE_DETAIL_FIELDS = {
    "secret_zone": (
        "player_id",
        "before_count",
        "after_count",
        "added_card_ids",
        "removed_card_ids",
        "visibility_zh",
    ),
    "deck_change": (
        "player_id",
        "before_count",
        "after_count",
        "drawn_count",
        "added_count",
        "shuffled_count",
        "order_changed",
        "known_top_before",
        "known_top_after",
    ),
    "cost_modification": (
        "entity_id",
        "card_id",
        "printed_cost",
        "effective_cost_before",
        "effective_cost_after",
        "reason_zh",
        "duration_zh",
    ),
    "forge": (
        "entity_id",
        "card_id_before",
        "card_id_after",
        "mana_spent",
        "result_zh",
    ),
    "corrupt": (
        "entity_id",
        "card_id_before",
        "card_id_after",
        "triggering_card_cost",
        "result_zh",
    ),
    "location_cooldown": (
        "entity_id",
        "card_id",
        "cooldown_before",
        "cooldown_after",
        "durability_before",
        "durability_after",
        "usable_after",
    ),
    "special_tags": (
        "entity_id",
        "card_id",
        "tags_before",
        "tags_after",
        "explanation_zh",
    ),
    "titan_abilities": (
        "entity_id",
        "card_id",
        "used_ability_id",
        "used_ability_ids_before",
        "used_ability_ids_after",
        "remaining_ability_ids",
        "can_attack_after",
    ),
}

DETAIL_LABELS_ZH = {
    "player_id": "玩家",
    "before_count": "变更前数量",
    "after_count": "变更后数量",
    "added_card_ids": "加入的卡牌",
    "removed_card_ids": "移除的卡牌",
    "visibility_zh": "可见性",
    "drawn_count": "抽取数量",
    "added_count": "加入数量",
    "shuffled_count": "洗入数量",
    "order_changed": "牌序是否改变",
    "known_top_before": "变更前已知牌库顶",
    "known_top_after": "变更后已知牌库顶",
    "entity_id": "实体编号",
    "card_id": "卡牌编号",
    "printed_cost": "原始费用",
    "effective_cost_before": "变更前实际费用",
    "effective_cost_after": "变更后实际费用",
    "reason_zh": "变更原因",
    "duration_zh": "持续时间",
    "card_id_before": "变更前卡牌编号",
    "card_id_after": "变更后卡牌编号",
    "mana_spent": "消耗法力",
    "result_zh": "结果",
    "triggering_card_cost": "触发卡牌费用",
    "cooldown_before": "变更前冷却",
    "cooldown_after": "变更后冷却",
    "durability_before": "变更前耐久度",
    "durability_after": "变更后耐久度",
    "usable_after": "结算后是否可用",
    "tags_before": "变更前标签",
    "tags_after": "变更后标签",
    "explanation_zh": "说明",
    "used_ability_id": "本次使用的技能",
    "used_ability_ids_before": "变更前已用技能",
    "used_ability_ids_after": "变更后已用技能",
    "remaining_ability_ids": "剩余技能",
    "can_attack_after": "结算后能否攻击",
}


def review_state_from_observation(
    observation: Mapping[str, Any],
    *,
    own_known_deck_top: Sequence[str] = (),
    enemy_known_deck_top: Sequence[str] = (),
) -> Dict[str, Any]:
    viewer = int(observation["viewer"])
    return {
        "turn": int(observation["turn"]),
        "active_player_id": int(observation["active_player"]),
        "viewer_player_id": viewer,
        "players": [
            _review_player(
                viewer,
                "我方",
                observation["own"],
                hand_hidden=False,
                known_deck_top=own_known_deck_top,
            ),
            _review_player(
                1 - viewer,
                "敌方",
                observation["enemy"],
                hand_hidden=True,
                known_deck_top=enemy_known_deck_top,
            ),
        ],
        "terminal": bool(observation["terminal"]),
        "winner_player_id": observation["winner"],
    }


def _review_player(
    player_id: int,
    role_zh: str,
    player: Mapping[str, Any],
    *,
    hand_hidden: bool,
    known_deck_top: Sequence[str],
) -> Dict[str, Any]:
    hand_cards = [] if hand_hidden else list(player.get("hand", []))
    hero_tags = list(player.get("hero_tags", []))
    if player.get("hero_frozen"):
        hero_tags.append("冻结")
    return {
        "player_id": player_id,
        "role_zh": role_zh,
        "hero": {
            "health": int(player["hero_health"]),
            "armor": int(player.get("hero_armor", 0)),
            "attack": int(player.get("hero_attack", 0)),
            "tags": hero_tags,
        },
        "resources": {
            "mana": int(player["mana"]),
            "max_mana": int(player["max_mana"]),
            "temporary_mana": int(player["temporary_mana"]),
            "overload_pending": int(player.get("overload_pending", 0)),
            "overloaded_mana": int(player.get("overloaded_mana", 0)),
            "corpses": int(player.get("corpses", 0)),
            "fatigue": int(player["fatigue"]),
        },
        "zones": {
            "hand": {
                "count": int(player["hand_count"]),
                "hidden": hand_hidden,
                "cards": hand_cards,
            },
            "deck": {
                "count": int(player["deck_count"]),
                "order_known": bool(known_deck_top),
                "known_top_card_ids": list(known_deck_top),
            },
            "board": [_review_minion(item) for item in player["board"]],
            "graveyard": list(player.get("graveyard", [])),
            "secrets": list(player.get("secrets", [])),
            "locations": list(player.get("locations", [])),
            "weapon": _review_weapon(player.get("weapon")),
        },
    }


def _review_weapon(weapon: Any) -> Optional[Dict[str, Any]]:
    if weapon is None:
        return None
    item = _mapping(weapon, "weapon")
    mechanics = []
    if item.get("lifesteal"):
        mechanics.append("吸血")
    return {
        "entity_id": int(item["entity_id"]),
        "card_id": str(item["card_id"]),
        "attack": int(item["attack"]),
        "durability": int(item["durability"]),
        "mechanics_zh": mechanics,
    }


def _review_minion(minion: Mapping[str, Any]) -> Dict[str, Any]:
    mechanics = []
    if minion.get("taunt"):
        mechanics.append("嘲讽")
    if minion.get("charge"):
        mechanics.append("冲锋")
    for field, label in (
        ("stealth", "潜行"),
        ("lifesteal", "吸血"),
        ("reborn", "复生"),
        ("elusive", "扰魔"),
        ("rush", "突袭"),
        ("divine_shield", "圣盾"),
        ("poisonous", "剧毒"),
        ("frozen", "冻结"),
    ):
        if minion.get(field):
            mechanics.append(label)
    tags = dict(minion.get("tags", {}))
    if minion.get("races"):
        tags["races"] = list(minion["races"])
    if minion.get("temporary_attack"):
        tags["temporary_attack"] = int(minion["temporary_attack"])
        tags["temporary_attack_expires_turn"] = minion.get(
            "temporary_attack_expires_turn"
        )
    if minion.get("attached_deathrattle_effects"):
        tags["attached_deathrattle_effects"] = list(
            minion["attached_deathrattle_effects"]
        )
    return {
        "entity_id": int(minion["entity_id"]),
        "card_id": str(minion["card_id"]),
        "attack": int(minion["attack"]),
        "health": int(minion["health"]),
        "max_health": int(minion["max_health"]),
        "mechanics_zh": mechanics,
        "tags": tags,
    }


def validate_review_document(document: Mapping[str, Any]) -> None:
    _require_keys(
        document,
        {"schema_version", "locale", "card", "implementation", "scenario"},
        "document",
    )
    if document["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ValueError("unsupported authoring review schema")
    if document["locale"] != "zh-CN":
        raise ValueError("authoring review locale must be zh-CN")
    _require_keys(
        _mapping(document["card"], "card"),
        {"card_id", "name_zh", "source_text_zh", "source_version"},
        "card",
    )
    _require_keys(
        _mapping(document["implementation"], "implementation"),
        {"card_module", "generator", "definition"},
        "implementation",
    )
    dependencies = _mapping(document["implementation"], "implementation").get(
        "dependencies", []
    )
    if not isinstance(dependencies, list):
        raise ValueError("implementation dependencies must be a list")
    for dependency in dependencies:
        _require_keys(
            _mapping(dependency, "implementation dependency"),
            {"card_id", "name_zh", "source_text_zh", "source_version", "definition"},
            "implementation dependency",
        )
    scenario = _mapping(document["scenario"], "scenario")
    _require_keys(
        scenario,
        {
            "scenario_id",
            "title_zh",
            "purpose_zh",
            "before",
            "action",
            "after",
            "assertions",
            "special_cases",
        },
        "scenario",
    )
    _require_keys(
        _mapping(scenario["action"], "action"),
        {
            "type",
            "actor_player_id",
            "source_entity_id",
            "card_id",
            "target",
            "description_zh",
            "engine_action",
        },
        "action",
    )
    for state_name in ("before", "after"):
        state = _mapping(scenario[state_name], state_name)
        _require_keys(
            state,
            {
                "turn",
                "active_player_id",
                "viewer_player_id",
                "players",
                "terminal",
                "winner_player_id",
            },
            state_name,
        )
        players = state["players"]
        if not isinstance(players, list) or len(players) != 2:
            raise ValueError("{} must contain exactly two players".format(state_name))
        for player in players:
            _validate_player(_mapping(player, "player"))
    assertions = scenario["assertions"]
    if not isinstance(assertions, list) or not assertions:
        raise ValueError("scenario assertions must be a non-empty list")
    for assertion in assertions:
        _require_keys(
            _mapping(assertion, "assertion"),
            {"assertion_id", "subject_zh", "before", "after", "expected_zh"},
            "assertion",
        )
    special_cases = scenario["special_cases"]
    if not isinstance(special_cases, list):
        raise ValueError("scenario special_cases must be a list")
    for special_case in special_cases:
        item = _mapping(special_case, "special_case")
        _require_keys(item, {"kind", "summary_zh", "details"}, "special_case")
        if item["kind"] not in SPECIAL_CASE_KINDS:
            raise ValueError("unknown special case kind: {}".format(item["kind"]))
        details = _mapping(item["details"], "special_case.details")
        _require_keys(
            details,
            set(SPECIAL_CASE_DETAIL_FIELDS[str(item["kind"])]),
            "special_case.details",
        )


def _validate_player(player: Mapping[str, Any]) -> None:
    _require_keys(player, {"player_id", "role_zh", "hero", "resources", "zones"}, "player")
    _require_keys(_mapping(player["hero"], "hero"), {"health", "armor", "attack", "tags"}, "hero")
    _require_keys(
        _mapping(player["resources"], "resources"),
        {"mana", "max_mana", "temporary_mana", "fatigue"},
        "resources",
    )
    zones = _mapping(player["zones"], "zones")
    _require_keys(zones, {"hand", "deck", "board", "secrets", "locations", "weapon"}, "zones")
    _require_keys(_mapping(zones["hand"], "hand"), {"count", "hidden", "cards"}, "hand")
    _require_keys(
        _mapping(zones["deck"], "deck"),
        {"count", "order_known", "known_top_card_ids"},
        "deck",
    )


def render_review_document_zh(
    document: Mapping[str, Any],
    card_names_zh: Optional[Mapping[str, str]] = None,
) -> str:
    validate_review_document(document)
    names = card_names_zh or {}
    card = _mapping(document["card"], "card")
    scenario = _mapping(document["scenario"], "scenario")
    lines = [
        str(scenario["title_zh"]),
        "",
        "卡牌：{}（{}）".format(card["name_zh"], card["card_id"]),
        "卡面：{}".format(card["source_text_zh"]),
        "核验目的：{}".format(scenario["purpose_zh"]),
        "执行动作：{}".format(_mapping(scenario["action"], "action")["description_zh"]),
    ]
    dependencies = _mapping(document["implementation"], "implementation").get(
        "dependencies", []
    )
    if dependencies:
        lines.extend(["", "随母卡实现的衍生牌"])
        for dependency in dependencies:
            item = _mapping(dependency, "implementation dependency")
            lines.append(
                "- {}（{}）：{}".format(
                    item["name_zh"], item["card_id"], item["source_text_zh"] or "无卡面文字"
                )
            )
    lines.extend(["", "操作前"])
    lines.extend(_render_state(_mapping(scenario["before"], "before"), names))
    lines.extend(["", "操作后"])
    lines.extend(_render_state(_mapping(scenario["after"], "after"), names))
    lines.extend(["", "逐项核对"])
    for assertion in scenario["assertions"]:
        item = _mapping(assertion, "assertion")
        lines.append(
            "- {}：{}（{} → {}）".format(
                item["subject_zh"],
                item["expected_zh"],
                _render_value_zh(item["before"], names),
                _render_value_zh(item["after"], names),
            )
        )
    special_cases = scenario["special_cases"]
    if special_cases:
        lines.extend(["", "特殊情况"])
        for special_case in special_cases:
            item = _mapping(special_case, "special_case")
            lines.append("- {}".format(_replace_card_ids(str(item["summary_zh"]), names)))
            lines.append(
                "  明细：{}".format(
                    _render_details_zh(str(item["kind"]), item["details"], names)
                )
            )
    return "\n".join(lines) + "\n"


def _render_state(
    state: Mapping[str, Any], card_names_zh: Mapping[str, str]
) -> Sequence[str]:
    lines = [
        "- 回合 {}，当前行动玩家为玩家 {}。".format(
            state["turn"], state["active_player_id"]
        )
    ]
    for player in state["players"]:
        item = _mapping(player, "player")
        hero = _mapping(item["hero"], "hero")
        resources = _mapping(item["resources"], "resources")
        zones = _mapping(item["zones"], "zones")
        hand = _mapping(zones["hand"], "hand")
        deck = _mapping(zones["deck"], "deck")
        hand_text = (
            "{} 张（内容隐藏）".format(hand["count"])
            if hand["hidden"]
            else _cards_text(hand, card_names_zh)
        )
        board_text = _board_text(zones["board"], card_names_zh)
        graveyard = list(zones.get("graveyard", []))
        lines.append(
            "- {}：英雄 {} 点生命、{} 点护甲{}；法力 {}/{}，临时法力 {}；"
            "残骸 {}；手牌 {}；牌库 {} 张；墓地 {}；武器 {}；场上 {}。".format(
                item["role_zh"],
                hero["health"],
                hero["armor"],
                " [{}]".format("、".join(hero["tags"])) if hero["tags"] else "",
                resources["mana"],
                resources["max_mana"],
                resources["temporary_mana"],
                resources.get("corpses", 0),
                hand_text,
                deck["count"],
                _render_value_zh(graveyard, card_names_zh),
                _weapon_text(zones["weapon"], card_names_zh),
                board_text,
            )
        )
        if resources.get("overload_pending") or resources.get("overloaded_mana"):
            lines.append(
                "  过载：待锁定 {}，本回合已锁定 {}。".format(
                    resources.get("overload_pending", 0),
                    resources.get("overloaded_mana", 0),
                )
            )
    return lines


def _cards_text(hand: Mapping[str, Any], card_names_zh: Mapping[str, str]) -> str:
    cards = hand["cards"]
    if not cards:
        return "0 张"
    card_ids = [
        _card_reference(str(_mapping(card, "hand card")["card_id"]), card_names_zh)
        for card in cards
    ]
    return "{} 张：{}".format(hand["count"], "、".join(card_ids))


def _weapon_text(weapon: Any, card_names_zh: Mapping[str, str]) -> str:
    if weapon is None:
        return "无"
    item = _mapping(weapon, "weapon")
    mechanics = item.get("mechanics_zh", [])
    return "{} {}/{}{}".format(
        _card_reference(str(item["card_id"]), card_names_zh),
        item["attack"],
        item["durability"],
        " [{}]".format("、".join(mechanics)) if mechanics else "",
    )


def _board_text(board: Any, card_names_zh: Mapping[str, str]) -> str:
    if not isinstance(board, list) or not board:
        return "为空"
    rendered = []
    for minion in board:
        item = _mapping(minion, "minion")
        annotations = list(item["mechanics_zh"])
        races = _mapping(item.get("tags", {}), "minion tags").get("races", [])
        race_labels = {
            "BEAST": "野兽",
            "DEMON": "恶魔",
            "DRAGON": "龙",
            "ELEMENTAL": "元素",
            "MECHANICAL": "机械",
            "MURLOC": "鱼人",
            "PIRATE": "海盗",
            "QUILBOAR": "野猪人",
            "TOTEM": "图腾",
            "UNDEAD": "亡灵",
        }
        if races:
            annotations.append(
                "种族：{}".format(
                    "/".join(race_labels.get(str(race), str(race)) for race in races)
                )
            )
        rendered.append(
            "{} {}/{}{}".format(
                _card_reference(str(item["card_id"]), card_names_zh),
                item["attack"],
                item["health"],
                " [{}]".format("、".join(annotations))
                if annotations
                else "",
            )
        )
    return "、".join(rendered)


def _render_details_zh(
    kind: str,
    details: Any,
    card_names_zh: Mapping[str, str],
) -> str:
    item = _mapping(details, "special_case.details")
    values = []
    for key in SPECIAL_CASE_DETAIL_FIELDS[kind]:
        value = item[key]
        label = DETAIL_LABELS_ZH.get(str(key), str(key))
        values.append("{}={}".format(label, _render_value_zh(value, card_names_zh)))
    return "；".join(values)


def _render_value_zh(value: Any, card_names_zh: Mapping[str, str]) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if value is None:
        return "无"
    if isinstance(value, list):
        return (
            "、".join(_render_value_zh(item, card_names_zh) for item in value)
            if value
            else "无"
        )
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return _replace_card_ids(str(value), card_names_zh)


def _card_reference(card_id: str, card_names_zh: Mapping[str, str]) -> str:
    name = str(card_names_zh.get(card_id, "")).strip()
    return "{}（{}）".format(name, card_id) if name else card_id


def _replace_card_ids(text: str, card_names_zh: Mapping[str, str]) -> str:
    rendered = text
    for card_id in sorted(card_names_zh, key=len, reverse=True):
        if card_id in rendered:
            rendered = rendered.replace(card_id, _card_reference(card_id, card_names_zh))
    return rendered


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("{} must be an object".format(label))
    return value


def _require_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ValueError("{} is missing fields: {}".format(label, ", ".join(missing)))
