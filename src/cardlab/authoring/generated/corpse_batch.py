from __future__ import annotations

from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard, Minion
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-corpse-foundation-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "RLK_008t": CardDef(
        "RLK_008t",
        "复活的食尸鬼",
        CardType.MINION,
        2,
        2,
        2,
        rush=True,
        races=("UNDEAD",),
        collectible=False,
        leaves_corpse=False,
    ),
    "RLK_061t": CardDef(
        "RLK_061t",
        "复活的步兵",
        CardType.MINION,
        1,
        1,
        3,
        taunt=True,
        races=("UNDEAD",),
        collectible=False,
        leaves_corpse=False,
    ),
    "RLK_118t3": CardDef(
        "RLK_118t3",
        "凶恶僵尸",
        CardType.MINION,
        2,
        2,
        2,
        taunt=True,
        races=("UNDEAD",),
        collectible=False,
    ),
}

CARDS: Dict[str, CardDef] = {
    "RLK_503": CardDef(
        "RLK_503",
        "扛包收尸人",
        CardType.MINION,
        1,
        1,
        3,
        races=("UNDEAD",),
        effects=(Effect("gain_corpses", 1),),
    ),
    "CORE_RLK_712": CardDef(
        "CORE_RLK_712",
        "活力分流",
        CardType.SPELL,
        2,
        runes=("BLOOD",),
        spends_corpses=True,
        effects=(
            Effect("buff_hand_minions", attack=1, health=1),
            Effect("buff_hand_minions", attack=1, health=1, corpse_cost=2),
        ),
    ),
    "RLK_707": CardDef(
        "RLK_707",
        "墓地之力",
        CardType.SPELL,
        4,
        runes=("UNHOLY", "UNHOLY", "UNHOLY"),
        spends_corpses=True,
        effects=(
            Effect("buff_all", attack=1, target="friendly_minions"),
            Effect("buff_all", attack=2, target="friendly_minions", corpse_cost=5),
        ),
    ),
    "RLK_060": CardDef(
        "RLK_060",
        "亡者大军",
        CardType.SPELL,
        5,
        runes=("UNHOLY",),
        spends_corpses=True,
        effects=(Effect("summon_up_to_corpses", 5, card_id="RLK_008t"),),
    ),
    "CORE_RLK_118": CardDef(
        "CORE_RLK_118",
        "坟墓守卫",
        CardType.SPELL,
        4,
        runes=("UNHOLY", "UNHOLY"),
        spends_corpses=True,
        effects=(
            Effect("summon", 2, card_id="RLK_118t3"),
            Effect("grant_keyword_summoned", keyword="reborn", corpse_cost=4),
        ),
    ),
    "CORE_RLK_506": CardDef(
        "CORE_RLK_506",
        "白骨卫士指挥官",
        CardType.MINION,
        8,
        8,
        8,
        taunt=True,
        races=("UNDEAD",),
        runes=("BLOOD",),
        spends_corpses=True,
        effects=(Effect("summon_up_to_corpses", 6, card_id="RLK_061t"),),
    ),
    "CORE_RLK_505": CardDef(
        "CORE_RLK_505",
        "髓骨使御者",
        CardType.MINION,
        6,
        5,
        5,
        races=("UNDEAD",),
        runes=("FROST", "FROST"),
        spends_corpses=True,
        effects=(Effect("random_damage_spend_up_to_corpses", 5, attack=2),),
    ),
}

_SOURCE_TEXTS = {
    "RLK_503": "战吼：获得一份残骸。",
    "CORE_RLK_712": "使你手牌中的所有随从牌获得+1/+1。消耗2份残骸，再获得+1/+1。",
    "RLK_707": "使你的所有随从获得+1攻击力。消耗5份残骸，改为获得+3攻击力。",
    "RLK_060": "将最多5份残骸复活为2/2并具有突袭的复活的食尸鬼。",
    "CORE_RLK_118": "召唤两个2/2并具有嘲讽的僵尸。消耗4份残骸，使其获得复生。",
    "CORE_RLK_506": "嘲讽。战吼：将最多6份残骸复活为1/3并具有嘲讽的复活的步兵。",
    "CORE_RLK_505": "战吼：消耗最多5份残骸。每消耗一份残骸，随机对一个敌人造成2点伤害。",
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
    "CS2_120": "淡水鳄",
    "CS2_182": "冰风雪人",
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
        raise ValueError("unknown corpse batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_182"]
    own.hand = [HandCard(113_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.corpses = 5

    if card_id == "RLK_503":
        own.corpses = 0
    elif card_id == "CORE_RLK_712":
        own.corpses = 2
        own.hand.extend(
            [HandCard(113_001, "CS2_120"), HandCard(113_002, "CS2_182")]
        )
    elif card_id == "RLK_707":
        own.board = [Minion(113_010, "CS2_120", 2, 3, 3, summoned_turn=0)]
    elif card_id == "RLK_060":
        own.corpses = 3
    elif card_id == "CORE_RLK_118":
        own.corpses = 4
    elif card_id == "CORE_RLK_506":
        own.corpses = 6
    else:
        own.corpses = 5

    action = Action(ActionType.PLAY, 113_000)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    opposing_before = _player(before, "敌方")
    opposing_after = _player(after, "敌方")
    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        )
    ]

    result_card_id = card_id
    result_entities: list[int] = []
    explanation: str
    if card_id == "RLK_503":
        assertions.append(
            _assertion(
                "gain-corpse",
                "我方残骸",
                own_before["resources"]["corpses"],
                own_after["resources"]["corpses"],
                "战吼直接获得1份残骸",
            )
        )
        explanation = "这份残骸来自战吼，不要求先有随从死亡。"
    elif card_id == "CORE_RLK_712":
        hand_after = own_after["zones"]["hand"]["cards"]
        bonuses_after = [
            [item["card_id"], item["attack_bonus"], item["health_bonus"]]
            for item in hand_after
        ]
        assertions.extend(
            [
                _assertion(
                    "spend-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "有2份残骸时全部消耗",
                ),
                _assertion(
                    "double-hand-buff",
                    "手牌随从加成",
                    [["CS2_120", 0, 0], ["CS2_182", 0, 0]],
                    bonuses_after,
                    "两张手牌随从各获得+2/+2",
                ),
            ]
        )
        explanation = "第一段+1/+1必定结算；残骸充足时再为同一批手牌随从加+1/+1。"
    elif card_id == "RLK_707":
        minion_before = _board_cards(before, "我方", "CS2_120")[0]
        minion_after = _board_cards(after, "我方", "CS2_120")[0]
        assertions.extend(
            [
                _assertion(
                    "spend-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "有5份残骸时全部消耗",
                ),
                _assertion(
                    "replacement-buff",
                    "淡水鳄攻击力",
                    minion_before["attack"],
                    minion_after["attack"],
                    "最终总计获得+3攻击力，而非额外+3",
                ),
            ]
        )
        explanation = "实现拆成必定+1和支付成功后再+2，因此卡面所说的“改为+3”不会算成+4。"
    elif card_id == "RLK_060":
        summoned = _board_cards(after, "我方", "RLK_008t")
        result_card_id = "RLK_008t"
        result_entities = [item["entity_id"] for item in summoned]
        assertions.extend(
            [
                _assertion(
                    "spend-available-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "只有3份残骸时消耗3份",
                ),
                _assertion(
                    "summon-ghouls",
                    "复活的食尸鬼数量",
                    0,
                    len(summoned),
                    "每份已消耗残骸召唤一个2/2突袭食尸鬼",
                ),
            ]
        )
        explanation = "逐个召唤并逐份支付；衍生食尸鬼死亡时不会生成新的残骸。"
    elif card_id == "CORE_RLK_118":
        summoned = _board_cards(after, "我方", "RLK_118t3")
        result_card_id = "RLK_118t3"
        result_entities = [item["entity_id"] for item in summoned]
        assertions.extend(
            [
                _assertion(
                    "spend-four-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "召唤成功且残骸充足时消耗4份",
                ),
                _assertion(
                    "summon-reborn-zombies",
                    "具有复生的凶恶僵尸",
                    0,
                    sum("复生" in item["mechanics_zh"] for item in summoned),
                    "两个2/2嘲讽僵尸均获得复生",
                ),
            ]
        )
        explanation = "先召唤两个僵尸，再一次性支付4份残骸，将复生赋予成功召唤的僵尸。"
    elif card_id == "CORE_RLK_506":
        summoned = _board_cards(after, "我方", "RLK_061t")
        result_card_id = "RLK_061t"
        result_entities = [item["entity_id"] for item in summoned]
        assertions.extend(
            [
                _assertion(
                    "spend-six-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "最多消耗6份残骸",
                ),
                _assertion(
                    "summon-six-infantry",
                    "复活的步兵数量",
                    0,
                    len(summoned),
                    "主随从占一个位置后，召唤六个1/3嘲讽步兵",
                ),
            ]
        )
        explanation = "每个成功召唤的步兵消耗1份残骸；步兵死亡时不会生成残骸。"
    else:
        assertions.extend(
            [
                _assertion(
                    "spend-five-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "战吼先记录并消耗最多5份残骸",
                ),
                _assertion(
                    "five-damage-hits",
                    "敌方英雄生命值",
                    opposing_before["hero"]["health"],
                    opposing_after["hero"]["health"],
                    "敌方只有英雄时，五次随机伤害共造成10点伤害",
                ),
            ]
        )
        explanation = "本核验局面把随机池缩为敌方英雄；每份已消耗残骸独立产生一次2点伤害。"

    return {
        "scenario_id": "{}-corpse-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：残骸资源与结算核验".format(card.name),
        "purpose_zh": "核对残骸的获得、支付上限、衍生物数量及条件效果。",
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 113_000,
            "card_id": card_id,
            "target": None,
            "description_zh": "我方使用《{}》。".format(card.name),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "残骸资源和衍生实体单独记录。",
                "details": {
                    "entity_id": result_entities[0] if result_entities else 113_000,
                    "card_id": result_card_id,
                    "tags_before": {
                        "corpses": own_before["resources"]["corpses"],
                    },
                    "tags_after": {
                        "corpses": own_after["resources"]["corpses"],
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
