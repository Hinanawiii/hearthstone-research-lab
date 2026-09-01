from __future__ import annotations

from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    Effect,
    Minion,
    TargetRef,
    Weapon,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-deathrattle-foundation-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "AV_337t": CardDef(
        "AV_337t",
        "山熊宝宝",
        CardType.MINION,
        3,
        2,
        4,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
    "EX1_110t": CardDef(
        "EX1_110t",
        "贝恩·血蹄",
        CardType.MINION,
        5,
        5,
        5,
        collectible=False,
    ),
    "OG_031a": CardDef(
        "OG_031a",
        "暮光元素",
        CardType.MINION,
        3,
        4,
        2,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "EX1_383t": CardDef(
        "EX1_383t",
        "灰烬使者",
        CardType.WEAPON,
        5,
        attack=5,
        durability=3,
        collectible=False,
    ),
}

CARDS: Dict[str, CardDef] = {
    "CORE_DRG_107": CardDef(
        "CORE_DRG_107",
        "紫罗兰魔翼鸦",
        CardType.MINION,
        1,
        2,
        1,
        races=("ELEMENTAL", "BEAST"),
        deathrattle_effects=(Effect("add_to_hand", 1, target="owner", card_id="EX1_277"),),
    ),
    "CORE_DMF_067": CardDef(
        "CORE_DMF_067",
        "奖品商贩",
        CardType.MINION,
        2,
        2,
        3,
        races=("MURLOC",),
        effects=(Effect("draw_each_player", 1, target="all_players"),),
        deathrattle_effects=(Effect("draw_each_player", 1, target="all_players"),),
    ),
    "CORE_EX1_096": CardDef(
        "CORE_EX1_096",
        "战利品贮藏者",
        CardType.MINION,
        2,
        2,
        1,
        deathrattle_effects=(Effect("draw", 1, target="owner"),),
    ),
    "CORE_LOOT_413": CardDef(
        "CORE_LOOT_413",
        "硬壳甲虫",
        CardType.MINION,
        2,
        2,
        3,
        races=("BEAST",),
        deathrattle_effects=(Effect("armor", 3, target="owner_hero"),),
    ),
    "RLK_708": CardDef(
        "RLK_708",
        "堕寒男爵",
        CardType.MINION,
        3,
        2,
        2,
        races=("UNDEAD", "DRAENEI"),
        effects=(Effect("draw", 1, target="owner"),),
        deathrattle_effects=(Effect("draw", 1, target="owner"),),
    ),
    "CORE_WC_701": CardDef(
        "CORE_WC_701",
        "邪能响尾蛇",
        CardType.MINION,
        3,
        3,
        2,
        rush=True,
        races=("BEAST",),
        deathrattle_effects=(Effect("damage_all", 1, target="enemy_minions"),),
    ),
    "RLK_223": CardDef(
        "RLK_223",
        "萨萨里安",
        CardType.MINION,
        4,
        3,
        3,
        reborn=True,
        races=("UNDEAD",),
        effects=(Effect("random_damage", 2, target="enemy_character", repeats=1),),
        deathrattle_effects=(
            Effect("random_damage", 2, target="enemy_character", repeats=1),
        ),
    ),
    "CORE_SW_068": CardDef(
        "CORE_SW_068",
        "莫尔葛熔魔",
        CardType.MINION,
        8,
        8,
        8,
        taunt=True,
        races=("MECHANICAL", "DEMON"),
        deathrattle_effects=(Effect("armor", 8, target="owner_hero"),),
    ),
    "CORE_BAR_310": CardDef(
        "CORE_BAR_310",
        "光沐元素",
        CardType.MINION,
        6,
        6,
        6,
        taunt=True,
        races=("ELEMENTAL",),
        deathrattle_effects=(
            Effect("heal_all", 8, target="friendly_characters"),
        ),
    ),
    "CORE_AV_337": CardDef(
        "CORE_AV_337",
        "山岭野熊",
        CardType.MINION,
        7,
        5,
        6,
        taunt=True,
        races=("BEAST",),
        deathrattle_effects=(Effect("summon", 2, target="owner", card_id="AV_337t"),),
    ),
    "CORE_RLK_657": CardDef(
        "CORE_RLK_657",
        "地底虫王",
        CardType.MINION,
        7,
        6,
        6,
        rush=True,
        races=("UNDEAD",),
        effects=(Effect("armor", 6, target="owner_hero"),),
        deathrattle_effects=(Effect("armor", 6, target="owner_hero"),),
    ),
    "CORE_EX1_383": CardDef(
        "CORE_EX1_383",
        "提里奥·弗丁",
        CardType.MINION,
        8,
        8,
        8,
        taunt=True,
        divine_shield=True,
        deathrattle_effects=(
            Effect("equip_weapon", 1, target="owner", card_id="EX1_383t"),
        ),
    ),
    "CORE_EX1_110": CardDef(
        "CORE_EX1_110",
        "凯恩·血蹄",
        CardType.MINION,
        6,
        5,
        5,
        taunt=True,
        rarity="LEGENDARY",
        deathrattle_effects=(
            Effect("summon", 1, target="owner", card_id="EX1_110t"),
        ),
    ),
    "CORE_LOOT_368": CardDef(
        "CORE_LOOT_368",
        "虚空领主",
        CardType.MINION,
        9,
        3,
        9,
        taunt=True,
        races=("DEMON",),
        deathrattle_effects=(
            Effect("summon", 3, target="owner", card_id="CS2_065"),
        ),
    ),
    "CORE_OG_031": CardDef(
        "CORE_OG_031",
        "暮光神锤",
        CardType.WEAPON,
        5,
        attack=4,
        durability=2,
        deathrattle_effects=(
            Effect("summon", 1, target="owner", card_id="OG_031a"),
        ),
    ),
}

_SOURCE_TEXTS = {
    "CORE_DRG_107": "亡语：将一张“奥术飞弹”法术牌置入你的 手牌。",
    "CORE_DMF_067": "战吼，亡语：每个玩家抽一张牌。",
    "CORE_EX1_096": "亡语：抽一张牌。",
    "CORE_LOOT_413": "亡语： 获得3点护甲值。",
    "RLK_708": "战吼，亡语：抽一张牌。",
    "CORE_WC_701": "突袭，亡语：对所有敌方随从造成 1点伤害。",
    "RLK_223": "复生。战吼，亡语：随机对一个敌人造成2点伤害。",
    "CORE_SW_068": "嘲讽，亡语：获得8点护甲值。",
    "CORE_BAR_310": "嘲讽，亡语：为所有友方角色恢复8点生命值。",
    "CORE_AV_337": "嘲讽，亡语：召唤两只2/4并具有嘲讽的山熊宝宝。",
    "CORE_RLK_657": "突袭。战吼，亡语：获得6点护甲值。",
    "CORE_EX1_383": "圣盾，嘲讽，亡语：装备一把5/3的 灰烬使者。",
    "CORE_EX1_110": "嘲讽。亡语：召唤一个5/5的贝恩·血蹄。",
    "CORE_LOOT_368": "嘲讽，亡语： 召唤三个1/3并具有嘲讽的恶魔。",
    "CORE_OG_031": "亡语：召唤一个4/2的元素。",
}

AUTHORING_METADATA: Dict[str, Dict[str, Any]] = {
    card_id: {
        "source_version": SOURCE_VERSION,
        "source_text": _SOURCE_TEXTS[card_id],
        "source_text_zh": _SOURCE_TEXTS[card_id],
        "name_zh": card.name,
        "generated_by": GENERATED_BY,
        "review_status": "awaiting_human_scenario_review",
    }
    for card_id, card in CARDS.items()
}

SCENARIO_CARD_NAMES_ZH = {
    **{card_id: card.name for card_id, card in CARDS.items()},
    **{card_id: card.name for card_id, card in TOKEN_CARDS.items()},
    "CS2_065": "虚空行者",
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
    "CS2_182": "冰风雪人",
    "EX1_277": "奥术飞弹",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _board_cards(state: Mapping[str, Any], role_zh: str, card_id: str) -> list[Mapping[str, Any]]:
    return [
        item
        for item in _player(state, role_zh)["zones"]["board"]
        if item["card_id"] == card_id
    ]


def _assertion(
    assertion_id: str,
    subject_zh: str,
    before: Any,
    after: Any,
    expected_zh: str,
) -> Dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "subject_zh": subject_zh,
        "before": before,
        "after": after,
        "expected_zh": expected_zh,
    }


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown deathrattle batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 12
    opposing.hero_health = 25
    own.deck = ["CS2_120", "CS2_172"]
    opposing.deck = ["CS2_182"]
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    if card.card_type == CardType.WEAPON:
        own.weapon = Weapon(105_000, card_id, card.attack, 1)
        own.hero_attack = card.attack
        opposing.board = [Minion(105_010, "CS2_182", 0, 5, 5, summoned_turn=0)]
        action = Action(
            ActionType.HERO_ATTACK,
            105_000,
            TargetRef.minion(enemy, 105_010),
        )
        action_type = "hero_attack_break_weapon"
        description = "我方使用只剩1耐久的《暮光神锤》攻击敌方冰风雪人。"
    else:
        own.board = [
            Minion(
                105_000,
                card_id,
                card.attack,
                1,
                card.health,
                taunt=card.taunt,
                races=card.races,
                reborn=card.reborn,
                rush=card.rush,
                summoned_turn=0,
            ),
            Minion(105_001, "CS2_120", 2, 1, 3, summoned_turn=0),
        ]
        action = Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 105_000))
        action_type = "hero_power_destroy_fixture"
        description = "我方英雄技能对仅剩1点生命的《{}》造成1点伤害。".format(card.name)
        if card_id == "CORE_WC_701":
            opposing.board = [
                Minion(105_010, "CS2_120", 2, 1, 3, summoned_turn=0),
                Minion(105_011, "CS2_182", 4, 5, 5, summoned_turn=0),
            ]

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    opposing_before = _player(before, "敌方")
    opposing_after = _player(after, "敌方")
    assertions = []
    result_card_id: str
    result_entities: list[int]
    explanation: str

    if card_id == "CORE_DRG_107":
        assertions.append(
            _assertion(
                "deathrattle-add-arcane-missiles",
                "我方手牌中的奥术飞弹",
                0,
                sum(
                    1
                    for item in own_after["zones"]["hand"]["cards"]
                    if item["card_id"] == "EX1_277"
                ),
                "亡语将一张奥术飞弹置入我方手牌",
            )
        )
        result_card_id = "EX1_277"
        result_entities = []
        explanation = "置入手牌不从牌库抽取，因此牌库数量不变。"
    elif card_id == "CORE_DMF_067":
        assertions.extend(
            [
                _assertion(
                    "deathrattle-owner-draw",
                    "我方手牌/牌库数量",
                    [
                        own_before["zones"]["hand"]["count"],
                        own_before["zones"]["deck"]["count"],
                    ],
                    [
                        own_after["zones"]["hand"]["count"],
                        own_after["zones"]["deck"]["count"],
                    ],
                    "亡语使我方抽一张牌",
                ),
                _assertion(
                    "deathrattle-opponent-draw",
                    "敌方手牌/牌库数量",
                    [
                        opposing_before["zones"]["hand"]["count"],
                        opposing_before["zones"]["deck"]["count"],
                    ],
                    [
                        opposing_after["zones"]["hand"]["count"],
                        opposing_after["zones"]["deck"]["count"],
                    ],
                    "亡语也使敌方抽一张牌",
                ),
            ]
        )
        result_card_id = card_id
        result_entities = []
        explanation = "战吼和亡语共用同一项双方抽牌原语，本局面只核对亡语阶段。"
    elif card_id in {"CORE_EX1_096", "RLK_708"}:
        assertions.append(
            _assertion(
                "deathrattle-draw",
                "我方手牌/牌库数量",
                [own_before["zones"]["hand"]["count"], own_before["zones"]["deck"]["count"]],
                [own_after["zones"]["hand"]["count"], own_after["zones"]["deck"]["count"]],
                "随从死亡后抽一张牌",
            )
        )
        result_card_id = "CS2_172"
        result_entities = []
        explanation = "抽牌发生在随从离场后的亡语阶段。"
    elif card_id in {"CORE_LOOT_413", "CORE_SW_068", "CORE_RLK_657"}:
        armor = {
            "CORE_LOOT_413": 3,
            "CORE_SW_068": 8,
            "CORE_RLK_657": 6,
        }[card_id]
        assertions.append(
            _assertion(
                "deathrattle-armor",
                "我方英雄护甲",
                own_before["hero"]["armor"],
                own_after["hero"]["armor"],
                "亡语获得{}点护甲".format(armor),
            )
        )
        result_card_id = card_id
        result_entities = []
        explanation = (
            "护甲在死亡实体移出场后结算。地底虫王的战吼与亡语"
            "共用同一项获得6点护甲原语。"
            if card_id == "CORE_RLK_657"
            else "护甲在死亡实体移出场后结算。"
        )
    elif card_id == "CORE_WC_701":
        enemy_yeti_before = _board_cards(before, "敌方", "CS2_182")[0]
        enemy_yeti_after = _board_cards(after, "敌方", "CS2_182")[0]
        assertions.extend(
            [
                _assertion(
                    "deathrattle-remove-lethal-target",
                    "敌方淡水鳄数量",
                    1,
                    len(_board_cards(after, "敌方", "CS2_120")),
                    "1点伤害消灭仅剩1点生命的敌方随从",
                ),
                _assertion(
                    "deathrattle-damage-survivor",
                    "敌方冰风雪人生命值",
                    enemy_yeti_before["health"],
                    enemy_yeti_after["health"],
                    "所有仍在场的敌方随从各受到1点伤害",
                ),
            ]
        )
        result_card_id = card_id
        result_entities = []
        explanation = "亡语的群体伤害在来源离场后结算，并再次执行死亡清理。"
    elif card_id == "RLK_223":
        reborn_copy = _board_cards(after, "我方", "RLK_223")
        assertions.extend(
            [
                _assertion(
                    "deathrattle-random-enemy-damage",
                    "敌方英雄生命值",
                    opposing_before["hero"]["health"],
                    opposing_after["hero"]["health"],
                    "敌方只有英雄可选时，亡语对其造成2点伤害",
                ),
                _assertion(
                    "reborn-after-death",
                    "复生后的萨萨里安",
                    0,
                    len(reborn_copy),
                    "首次死亡后以1点生命复生，且不再具有复生",
                ),
            ]
        )
        result_card_id = card_id
        result_entities = [item["entity_id"] for item in reborn_copy]
        explanation = "战吼和亡语共用随机敌人伤害原语；复生生成新的1血实体。"
    elif card_id == "CORE_BAR_310":
        friendly_before = _board_cards(before, "我方", "CS2_120")[0]
        friendly_after = _board_cards(after, "我方", "CS2_120")[0]
        assertions.extend(
            [
                _assertion(
                    "deathrattle-hero-heal",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "亡语为我方英雄恢复8点生命",
                ),
                _assertion(
                    "deathrattle-minion-heal",
                    "我方淡水鳄生命值",
                    friendly_before["health"],
                    friendly_after["health"],
                    "友方随从也恢复生命，但不超过上限",
                ),
            ]
        )
        result_card_id = card_id
        result_entities = []
        explanation = "已经死亡的光沐元素不再是友方角色，因此不会治疗自身。"
    elif card_id == "CORE_EX1_110":
        summoned = _board_cards(after, "我方", "EX1_110t")
        assertions.append(
            _assertion(
                "deathrattle-baine",
                "贝恩·血蹄数量",
                0,
                len(summoned),
                "凯恩离场后召唤一个独立的5/5贝恩",
            )
        )
        result_card_id = "EX1_110t"
        result_entities = [item["entity_id"] for item in summoned]
        explanation = "贝恩是新的衍生物实体，不继承凯恩受到的伤害。"
    elif card_id == "CORE_AV_337":
        summoned = _board_cards(after, "我方", "AV_337t")
        assertions.append(
            _assertion(
                "deathrattle-bear-cubs",
                "山熊宝宝数量",
                0,
                len(summoned),
                "山岭野熊离场后召唤两只2/4嘲讽野兽",
            )
        )
        result_card_id = "AV_337t"
        result_entities = [item["entity_id"] for item in summoned]
        explanation = "两只山熊宝宝都是新的衍生物实体，且仍受七随从上限约束。"
    elif card_id == "CORE_LOOT_368":
        summoned = _board_cards(after, "我方", "CS2_065")
        assertions.append(
            _assertion(
                "deathrattle-voidwalkers",
                "虚空行者数量",
                0,
                len(summoned),
                "虚空领主离场后召唤三个1/3嘲讽恶魔",
            )
        )
        result_card_id = "CS2_065"
        result_entities = [item["entity_id"] for item in summoned]
        explanation = "召唤数量仍受七个随从的场上上限约束。"
    elif card_id == "CORE_EX1_383":
        assertions.append(
            _assertion(
                "deathrattle-equip-ashbringer",
                "我方武器",
                own_before["zones"]["weapon"],
                own_after["zones"]["weapon"],
                "提里奥离场后装备一把5/3的灰烬使者",
            )
        )
        result_card_id = "EX1_383t"
        result_entities = []
        explanation = "该局面表示提里奥的圣盾已先被消耗，再由致死伤害触发亡语。"
    else:
        summoned = _board_cards(after, "我方", "OG_031a")
        assertions.extend(
            [
                _assertion(
                    "weapon-destroyed",
                    "我方武器",
                    own_before["zones"]["weapon"],
                    own_after["zones"]["weapon"],
                    "攻击消耗最后1点耐久后武器离场",
                ),
                _assertion(
                    "weapon-deathrattle-elemental",
                    "暮光元素数量",
                    0,
                    len(summoned),
                    "武器离场后召唤一个4/2元素",
                ),
            ]
        )
        result_card_id = "OG_031a"
        result_entities = [item["entity_id"] for item in summoned]
        explanation = "武器因耐久耗尽或被替换而离场时都会触发亡语。"

    return {
        "scenario_id": "{}-deathrattle-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：离场后结算亡语".format(card.name),
        "purpose_zh": "核对死亡实体先离场，再按顺序执行一次亡语。",
        "before": before,
        "action": {
            "type": action_type,
            "actor_player_id": actor,
            "source_entity_id": action.source_id or 105_000,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": description,
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "亡语来源与生成实体单独记录。",
                "details": {
                    "entity_id": 105_000,
                    "card_id": card_id,
                    "tags_before": {"deathrattle_pending": False},
                    "tags_after": {
                        "source_removed": True,
                        "result_card_id": result_card_id,
                        "result_entity_ids": result_entities,
                    },
                    "explanation_zh": explanation,
                },
            }
        ],
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "TOKEN_CARDS",
    "build_review_scenario",
]
