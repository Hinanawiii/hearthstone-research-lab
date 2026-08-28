# Card-pool and rule contract

Version: `legacy-mage-v1`

## Match setup

- symmetric 30-card decks, with two copies of each collectible card below;
- 30 hero health and no armor;
- first player draws three opening cards, second player draws four and receives The Coin;
- no mulligan in version 1;
- one mana crystal is gained at the start of a turn, up to ten;
- ten-card hand limit, seven-minion board limit, and increasing fatigue damage;
- Mage Fireblast costs two mana, deals one damage to any character, and is usable once per turn.

## Collectible cards

| Card ID | Name | Cost | Rules implemented |
| --- | --- | ---: | --- |
| `CS2_231` | Wisp | 0 | 1/1 minion |
| `CS2_189` | Elven Archer | 1 | 1/1; battlecry deals 1 to any character |
| `CS1_042` | Goldshire Footman | 1 | 1/2 Taunt |
| `CS2_172` | Bloodfen Raptor | 2 | 3/2 minion |
| `CS2_120` | River Crocolisk | 2 | 2/3 minion |
| `EX1_015` | Novice Engineer | 2 | 1/1; battlecry draws one |
| `CS2_121` | Frostwolf Grunt | 2 | 2/2 Taunt |
| `CS2_124` | Wolfrider | 3 | 3/1 Charge |
| `CS2_182` | Chillwind Yeti | 4 | 4/5 minion |
| `CS2_179` | Sen'jin Shieldmasta | 4 | 3/5 Taunt |
| `CS2_147` | Gnomish Inventor | 4 | 2/4; battlecry draws one |
| `CS2_200` | Boulderfist Ogre | 6 | 6/7 minion |
| `CS2_029` | Fireball | 4 | deal 6 to any character |
| `CS2_023` | Arcane Intellect | 3 | draw two |
| `EX1_277` | Arcane Missiles | 1 | deal 1 to a random enemy character three times |

The Coin is a non-collectible zero-cost spell that grants one temporary mana for the current turn.

## Resolution details

Minions cannot attack on the turn they are summoned unless they have Charge. A minion attacks once
per turn. Taunt blocks attacks on other enemy targets while a living Taunt minion remains. Minion
combat damage is simultaneous. Dead minions are removed after each damage event; Arcane Missiles
therefore chooses again from the surviving enemy characters for every missile.

## Opt-in authoring mechanics

Generated cards are not added to the `legacy-mage-v1` deck. The authoring workflow loads them
through a separate runtime registry, where the engine currently supports these mechanics:

- Stealth blocks enemy targeting and attacks, then ends when the minion attacks;
- Lifesteal heals the source minion's owner for damage actually dealt in combat, whether the
  minion attacks or defends, up to 30 hero health;
- Reborn replaces the first dead instance with a new one-health entity and removes Reborn from it;
- Elusive blocks spell and hero-power targeting but does not block minion attacks;
- Rush allows attacks against minions on the summoning turn and allows hero attacks on later turns;
- Divine Shield replaces the first positive damage event, then disappears;
- Overload accumulates while cards are played and locks that much mana on the owner's next turn.

These are narrow implementations for the reviewed generated cards. They do not add a general
trigger queue, enchantment layers, Silence interactions, or other undeclared combinations.

## Deliberate omissions

Weapons, hero attacks, armor, secrets, freeze, discover, card generation, enchantment
layers, auras, silence, deathrattles, triggered-effect queues, tribes, and mulligan are outside this
version. No behavior should be inferred for an omitted mechanic. Adding one to the default deck
requires engine tests and a card-pool version change.
