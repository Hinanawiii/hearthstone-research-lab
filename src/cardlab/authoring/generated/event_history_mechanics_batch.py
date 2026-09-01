from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    Effect,
    HandCard,
    Minion,
    TargetRef,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-event-history-mechanics-batch-v1"

SPELL_POOL = ("CS2_029", "CS2_023", "EX1_277")
OTHER_CLASS_POOL = ("CORE_CS2_029", "CORE_EX1_238", "CORE_CS2_093")
MURLOC_POOL = ("CORE_EX1_506", "CORE_DMF_067")

TOKEN_CARDS: Dict[str, CardDef] = {
    "RLK_061t": CardDef(
        "RLK_061t",
        "复活的步兵",
        CardType.MINION,
        1,
        1,
        3,
        taunt=True,
        collectible=False,
        leaves_corpse=False,
    )
}

CARDS: Dict[str, CardDef] = {
    "RLK_061": CardDef(
        "RLK_061",
        "战场通灵师",
        CardType.MINION,
        2,
        2,
        2,
        rarity="COMMON",
        on_owner_turn_end_effects=(
            Effect("spend_corpses_summon", card_id="RLK_061t", corpse_cost=1),
        ),
    ),
    "CORE_RLK_121": CardDef(
        "CORE_RLK_121",
        "死亡侍僧",
        CardType.MINION,
        3,
        2,
        4,
        rarity="COMMON",
        on_friendly_death_race="UNDEAD",
        on_friendly_death_effects=(Effect("draw", 1),),
    ),
    "CORE_RLK_745": CardDef(
        "CORE_RLK_745",
        "恶毒恐魔",
        CardType.MINION,
        4,
        2,
        4,
        reborn=True,
        races=("UNDEAD",),
        rarity="COMMON",
        on_owner_turn_end_effects=(
            Effect("spend_corpses_summon_source_copy", corpse_cost=4),
        ),
    ),
    "RLK_720": CardDef(
        "RLK_720",
        "侏儒嚼嚼怪",
        CardType.MINION,
        6,
        5,
        6,
        taunt=True,
        lifesteal=True,
        races=("UNDEAD",),
        rarity="COMMON",
        on_owner_turn_end_effects=(Effect("source_attacks_lowest_health_enemy"),),
    ),
    "CORE_RLK_706": CardDef(
        "CORE_RLK_706",
        "亚历山德罗斯·莫格莱尼",
        CardType.MINION,
        7,
        7,
        7,
        races=("UNDEAD",),
        rarity="LEGENDARY",
        effects=(Effect("gain_permanent_end_turn_enemy_damage", 3),),
    ),
    "CORE_BT_187": CardDef(
        "CORE_BT_187",
        "凯恩·日怒",
        CardType.MINION,
        4,
        3,
        5,
        charge=True,
        rarity="LEGENDARY",
        ignores_taunt_for_friendly_attacks=True,
    ),
    "CORE_TTN_866": CardDef(
        "CORE_TTN_866",
        "神秘恐魔",
        CardType.MINION,
        7,
        4,
        10,
        lifesteal=True,
        races=("DEMON", "BEAST"),
        rarity="EPIC",
        on_owner_turn_end_effects=(Effect("all_enemy_minions_attack_source"),),
    ),
    "CORE_CATA_006": CardDef(
        "CORE_CATA_006",
        "奥尔法",
        CardType.MINION,
        6,
        4,
        3,
        races=("BEAST",),
        rarity="LEGENDARY",
        effects=(Effect("attach_same_cost_deathrattle_other_friendly"),),
    ),
    "CORE_EX1_012": CardDef(
        "CORE_EX1_012",
        "血法师萨尔诺斯",
        CardType.MINION,
        2,
        1,
        1,
        races=("UNDEAD",),
        rarity="LEGENDARY",
        spell_damage=1,
        deathrattle_effects=(Effect("draw", 1),),
    ),
    "CORE_EX1_100": CardDef(
        "CORE_EX1_100",
        "游学者周卓",
        CardType.MINION,
        2,
        0,
        4,
        rarity="LEGENDARY",
        on_any_spell_cast_effects=(Effect("copy_event_card_to_other_player"),),
    ),
    "CORE_ETC_111": CardDef(
        "CORE_ETC_111",
        "商品卖家",
        CardType.MINION,
        4,
        3,
        5,
        races=("NAGA",),
        rarity="COMMON",
        on_owner_turn_end_effects=(
            Effect("add_random_spell_opponent_deck_top", card_ids=SPELL_POOL),
        ),
    ),
    "CORE_CFM_344": CardDef(
        "CORE_CFM_344",
        "飞火流星·芬杰",
        CardType.MINION,
        5,
        3,
        5,
        stealth=True,
        races=("MURLOC",),
        rarity="LEGENDARY",
        on_attack_kill_effects=(
            Effect("summon_from_deck_race", 2, race="MURLOC", card_ids=MURLOC_POOL),
        ),
    ),
    "CORE_SCH_717": CardDef(
        "CORE_SCH_717",
        "钥匙专家阿拉巴斯特",
        CardType.MINION,
        7,
        6,
        8,
        rarity="LEGENDARY",
        on_opponent_draw_effects=(Effect("copy_event_card_cost_one"),),
    ),
    "CORE_SW_047": CardDef(
        "CORE_SW_047",
        "大领主弗塔根",
        CardType.MINION,
        6,
        5,
        5,
        divine_shield=True,
        rarity="LEGENDARY",
        on_friendly_divine_shield_lost_effects=(
            Effect("random_buff_hand_minion", attack=5, health=5),
        ),
    ),
    "CORE_BAR_313": CardDef(
        "CORE_BAR_313",
        "安瑟祭司",
        CardType.MINION,
        5,
        5,
        5,
        taunt=True,
        rarity="EPIC",
        effects=(Effect("buff_source_if_healed_this_turn", attack=3, health=3),),
    ),
    "CORE_CFM_781": CardDef(
        "CORE_CFM_781",
        "收集者沙库尔",
        CardType.MINION,
        3,
        2,
        4,
        stealth=True,
        rarity="LEGENDARY",
        on_attack_effects=(
            Effect("add_random_from_pool", 1, card_ids=OTHER_CLASS_POOL),
        ),
    ),
    "CORE_RLK_567": CardDef(
        "CORE_RLK_567",
        "殒命暗影",
        CardType.SPELL,
        0,
        rarity="LEGENDARY",
        transforms_in_hand_to_last_spell=True,
    ),
    "CS3_007": CardDef(
        "CS3_007",
        "电击学徒",
        CardType.MINION,
        1,
        3,
        2,
        rarity="COMMON",
        spell_damage=1,
        overload=1,
    ),
}

_SOURCE_TEXTS = {
    "RLK_061": "在你的回合结束时，将一份残骸复活为1/3并具有嘲讽的复活的步兵。",
    "CORE_RLK_121": "在一个友方亡灵死亡后，抽一张牌。",
    "CORE_RLK_745": "复生。 在你的回合结束时，消耗4份残骸，召唤一个本随从的复制。",
    "RLK_720": "嘲讽，吸血。在你的回合结束时，攻击生命值最低的敌人。",
    "CORE_RLK_706": "战吼：在本局对战的剩余时间内，在你的回合结束时，对你的对手造成3点伤害。",
    "CORE_BT_187": "冲锋 所有友方攻击无视 嘲讽。",
    "CORE_TTN_866": "吸血。在你的回合结束时，迫使所有敌方随从攻击本随从。",
    "CORE_CATA_006": "战吼：使你的其他随从获得“亡语：召唤一个法力值消耗与本随从相同的随从”。",
    "CORE_EX1_012": "法术伤害+1，亡语：抽一张牌。",
    "CORE_EX1_100": "每当一个玩家施放一个法术，复制该法术，将其置入另一个玩家的手牌。",
    "CORE_ETC_111": "在你的回合结束时，随机将一张法术牌置于你对手的牌库顶。",
    "CORE_CFM_344": "潜行 每当本随从攻击并消灭一个随从，便从你的牌库中召唤两个鱼人。",
    "CORE_SCH_717": "每当你的对手抽一张牌时，将一张复制置入你的手牌，其法力值消耗变为（1）点。",
    "CORE_SW_047": "圣盾 在一个友方随从失去圣盾后，使你手牌中的一张随从牌获得+5/+5。",
    "CORE_BAR_313": "嘲讽，战吼：如果你在本回合中恢复过生命值，便获得+3/+3。",
    "CORE_CFM_781": "潜行。每当本随从攻击时，将一张另一职业的牌置入你的手牌。",
    "CORE_RLK_567": "每当你施放一个法术，变形成为该法术的复制。",
    "CS3_007": "法术伤害+1 过载：（1）",
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
    "RLK_061t": "复活的步兵",
    "CS2_029": "火球术",
    "CS2_023": "奥术智慧",
    "CS2_120": "淡水鳄",
    "CORE_EX1_506": "鱼人猎潮者",
    "CORE_DMF_067": "奖品商贩",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


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
        raise ValueError("unknown event history mechanics card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]
    source_entity_id = 190_000
    actions: list[Action]

    if card_id in {"RLK_061", "CORE_RLK_745", "RLK_720", "CORE_TTN_866", "CORE_ETC_111"}:
        own.board = [
            Minion(
                source_entity_id,
                card_id,
                card.attack,
                card.health,
                card.health,
                taunt=card.taunt,
                lifesteal=card.lifesteal,
                reborn=card.reborn,
                races=card.races,
                summoned_turn=0,
            )
        ]
        own.corpses = 4
        own.hero_health = 20
        if card_id == "RLK_720":
            opposing.board = [Minion(190_001, "CS2_120", 2, 2, 3, summoned_turn=0)]
        elif card_id == "CORE_TTN_866":
            opposing.board = [
                Minion(190_002, "CS2_120", 1, 1, 1, summoned_turn=0),
                Minion(190_003, "CS2_120", 1, 1, 1, summoned_turn=0),
            ]
        actions = [Action.end_turn()]
        description = "将《{}》置于我方场上并结束回合。".format(card.name)
    elif card_id == "CORE_RLK_121":
        own.board = [
            Minion(source_entity_id, card_id, 2, 4, 4, summoned_turn=0),
            Minion(190_004, "CORE_EX1_012", 1, 1, 1, races=("UNDEAD",), summoned_turn=0),
        ]
        actions = [Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 190_004))]
        description = "英雄技能消灭友方亡灵，观察死亡侍僧的抽牌事件。"
    elif card_id == "CORE_RLK_706":
        own.hand = [HandCard(source_entity_id, card_id)]
        actions = [Action(ActionType.PLAY, source_entity_id), Action.end_turn()]
        description = "打出莫格莱尼并结束回合，检查离场后仍保留的持续伤害标记。"
    elif card_id == "CORE_BT_187":
        own.board = [
            Minion(source_entity_id, card_id, 3, 5, 5, charge=True, summoned_turn=0),
            Minion(190_005, "CS2_120", 2, 3, 3, summoned_turn=0),
        ]
        opposing.board = [
            Minion(190_006, "CS2_120", 2, 3, 3, taunt=True, summoned_turn=0),
            Minion(190_007, "CS2_120", 2, 3, 3, summoned_turn=0),
        ]
        actions = [
            Action(ActionType.ATTACK, 190_005, TargetRef.minion(enemy, 190_007))
        ]
        description = "凯恩在场时，让友方淡水鳄越过嘲讽攻击另一个敌方随从。"
    elif card_id == "CORE_CATA_006":
        own.hand = [HandCard(source_entity_id, card_id)]
        own.board = [Minion(190_008, "CS2_120", 2, 3, 3, summoned_turn=0)]
        actions = [Action(ActionType.PLAY, source_entity_id)]
        description = "友方已有淡水鳄时打出奥尔法，检查实例附加亡语。"
    elif card_id == "CORE_EX1_012":
        own.board = [
            Minion(source_entity_id, card_id, 1, 1, 1, races=("UNDEAD",), summoned_turn=0)
        ]
        actions = [Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, source_entity_id))]
        description = "英雄技能消灭血法师萨尔诺斯，检查亡语抽牌。"
    elif card_id == "CORE_EX1_100":
        own.board = [Minion(source_entity_id, card_id, 0, 4, 4, summoned_turn=0)]
        own.hand = [HandCard(190_009, "CS2_029")]
        actions = [Action(ActionType.PLAY, 190_009, TargetRef.hero(enemy))]
        description = "周卓在场时施放火球术，检查另一方获得复制。"
    elif card_id == "CORE_CFM_344":
        own.board = [
            Minion(source_entity_id, card_id, 3, 5, 5, stealth=True, summoned_turn=0)
        ]
        own.deck = list(MURLOC_POOL)
        opposing.board = [Minion(190_010, "CS2_120", 1, 3, 3, summoned_turn=0)]
        actions = [
            Action(ActionType.ATTACK, source_entity_id, TargetRef.minion(enemy, 190_010))
        ]
        description = "芬杰攻击并消灭3点生命的随从，从牌库召唤两个鱼人。"
    elif card_id == "CORE_SCH_717":
        own.board = [Minion(source_entity_id, card_id, 6, 8, 8, summoned_turn=0)]
        actions = [Action.end_turn()]
        description = "结束我方回合，让对手正常抽牌并触发阿拉巴斯特。"
    elif card_id == "CORE_SW_047":
        own.board = [
            Minion(source_entity_id, card_id, 5, 5, 5, divine_shield=True, summoned_turn=0),
            Minion(190_011, "CS2_120", 2, 3, 3, divine_shield=True, summoned_turn=0),
        ]
        own.hand = [HandCard(190_012, "CS2_120")]
        actions = [Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 190_011))]
        description = "使另一个友方随从失去圣盾，检查手牌随从获得+5/+5。"
    elif card_id == "CORE_BAR_313":
        own.hero_health = 25
        game._heal(TargetRef.hero(actor), 2)
        own.hand = [HandCard(source_entity_id, card_id)]
        actions = [Action(ActionType.PLAY, source_entity_id)]
        description = "本回合已实际恢复2点生命值，随后打出安瑟祭司。"
    elif card_id == "CORE_CFM_781":
        own.board = [
            Minion(source_entity_id, card_id, 2, 4, 4, stealth=True, summoned_turn=0)
        ]
        actions = [Action(ActionType.ATTACK, source_entity_id, TargetRef.hero(enemy))]
        description = "收集者沙库尔攻击敌方英雄，检查攻击声明时生成的手牌。"
    elif card_id == "CORE_RLK_567":
        own.hand = [HandCard(source_entity_id, card_id), HandCard(190_013, "CS2_029")]
        actions = [Action(ActionType.PLAY, 190_013, TargetRef.hero(enemy))]
        description = "殒命暗影留在手牌中，施放火球术后检查其变形结果。"
    else:
        own.hand = [HandCard(source_entity_id, card_id)]
        actions = [Action(ActionType.PLAY, source_entity_id)]
        description = "打出电击学徒，检查法术伤害与过载标签。"

    before = review_state_from_observation(game.observation(actor))
    engine_actions = []
    for action in actions:
        game.apply(action)
        engine_actions.append(action.to_dict())
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")

    summary_before: Any = {
        "hand": own_before["zones"]["hand"]["cards"],
        "board": own_before["zones"]["board"],
        "corpses": own_before["resources"]["corpses"],
        "enemy_health": enemy_before["hero"]["health"],
    }
    summary_after: Any = {
        "hand": own_after["zones"]["hand"]["cards"],
        "board": own_after["zones"]["board"],
        "corpses": own_after["resources"]["corpses"],
        "enemy_health": enemy_after["hero"]["health"],
    }
    assertions = [
        _assertion(
            "event-result",
            "事件结算后的关键状态",
            summary_before,
            summary_after,
            "按卡面事件只结算一次，并将跨回合或实例状态保存在固定字段中",
        )
    ]
    special_cases = [
        {
            "kind": "special_tags",
            "summary_zh": "事件监听范围、来源实例和跨回合状态单独记录。",
            "details": {
                "entity_id": source_entity_id,
                "card_id": card_id,
                "tags_before": {"event_source_active": True},
                "tags_after": {
                    "event_resolved": True,
                    "spells_played_previous_turn": own_after["history"].get(
                        "spells_played_previous_turn", []
                    ),
                },
                "explanation_zh": "人工应核对触发时点、监听者是否仍在场，以及效果是否绑定正确玩家。",
            },
        }
    ]

    return {
        "scenario_id": "{}-event-history-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：事件与历史核验".format(card.name),
        "purpose_zh": "核对回合、死亡、攻击、施法、抽牌和圣盾事件的监听边界。",
        "before": before,
        "action": {
            "type": "trigger_event_fixture",
            "actor_player_id": actor,
            "source_entity_id": actions[0].source_id,
            "card_id": card_id,
            "target": asdict(actions[0].target) if actions[0].target else None,
            "description_zh": description,
            "engine_action": engine_actions,
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }
