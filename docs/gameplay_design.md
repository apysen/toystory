# Household Object Tactics Game
## Gameplay Design Document

## 1. High-Level Combat Identity

The game is a compact turn-based tactics RPG about ordinary household objects that become fantasy-like warriors whenever humans are not watching.

The combat direction combines three major influences:

- **Fire Emblem** for player-phase and enemy-phase structure, combat forecasts, counterattacks, character recruitment, leveling, and a simple type triangle.
- **Mario + Rabbids: Sparks of Hope** for compact battlefields, readable movement zones, cover, destructible terrain, and highly positional ability use.
- **Into the Breach-style clarity** for telegraphed high-impact enemy actions and a strong emphasis on understanding danger before committing to a move.

The unique mechanic is **Human Gaze**. Powerful abilities create Noise. When enough Noise is generated, a human looks toward the battlefield. Objects caught in that gaze revert to mundane object form and stop fighting temporarily. While any Gaze is active, all Noise-generating Arts are disabled across the entire battlefield.

The goal is not to make the game mechanically dense. The goal is to create a small number of systems that interact cleanly and produce interesting positioning decisions.

---

## 2. Core Design Pillars

### 2.1 Readability First

A player should be able to understand most of a battlefield by looking at it.

The game should clearly communicate:

- where a character can move;
- which enemies can threaten a proposed destination;
- how much damage a character is expected to take if they end movement there;
- which enemy attacks are already committed or telegraphed;
- what cover is protecting;
- what areas will be affected by Human Gaze;
- when an Art will trigger Gaze;
- which abilities are disabled while Gaze is active.

The interface should remove bookkeeping without making decisions for the player.

### 2.2 Positioning Over Build Complexity

The player should win by:

- choosing strong matchups;
- using cover;
- controlling lanes;
- pushing and pulling units;
- manipulating Gaze timing;
- protecting vulnerable characters;
- setting up team combinations.

The game should not rely on large skill trees, crafting, equipment optimization, or huge stat systems.

### 2.3 Abilities Should Be Fun to Use

Arts do not use cooldowns or a traditional mana system.

Instead, powerful actions create **Noise**.

The player may use the same Art repeatedly if desired, but doing so brings Human Attention closer. Noise is therefore a tactical cost rather than a hard lockout.

### 2.4 Small Squad, Strong Character Identity

The standard deployment size is **5 characters**.

Five units is large enough to create meaningful team combinations and small enough to keep turns readable and quick.

Each playable character has a clearly differentiated battlefield role.

---

# 3. Turn Structure

Combat uses a classic two-phase structure.

## Player Phase

The player activates deployed characters in any order.

Each character receives:

1. **Movement**
2. **One Action**

The Action can be:

- Basic Attack
- Art
- Item
- Interaction
- Recruitment conversation
- Mission objective action

A character normally moves first, then acts.

Once the Action is committed, that character's activation ends.

## Enemy Phase

All enemies activate according to their AI priorities.

High-impact enemy Arts are often telegraphed during the preceding Player Phase so the player has an opportunity to respond.

## No Universal Action Points

The game does not use a generic AP system.

The simple movement-plus-action structure should remain the baseline unless a specific character ability deliberately breaks it.

---

# 4. Movement and Tactical Preview

## 4.1 Movement Zone

Selecting a character displays the full set of reachable tiles as a clear movement region.

The player should not need to manually count tiles.

## 4.2 Dynamic Threat Lines

While the player moves the cursor through reachable tiles, the game dynamically evaluates the proposed destination.

Every enemy capable of threatening that character from that tile displays a line toward the destination.

Threat lines should distinguish between:

- possible Basic Attacks;
- known ranged threats;
- telegraphed Arts;
- displacement attacks;
- committed boss attacks.

The game should never hide a valid threat simply because the attack has low Hit probability.

Lower-risk attacks can be displayed less prominently, but they remain visible.

## 4.3 Predicted HP

While hovering a destination, the selected character's HP bar displays a ghosted projected result.

Example:

**23 HP -> ~12 HP**

This forecast represents:

> If Enemy Phase began with the battlefield exactly as it is now, what damage is this character expected to take?

The forecast updates whenever the player changes the board state.

Because attacks can miss or crit, this is an expected outcome rather than an absolute guarantee.

The interface can also show a simple warning such as:

- **Safe**
- **Exposed**
- **High Risk**
- **Broken Risk**

Hovering a specific threat line can show exact details such as:

- enemy name;
- damage;
- Hit chance;
- Crit chance;
- type advantage;
- displacement path.

## 4.4 Displacement Preview

If a threatened attack could push or pull the selected unit, the projected movement should be shown with an arrow.

If collision damage would occur, the preview should state it explicitly.

Example:

**8 Damage + 3 Collision**

---

# 5. Deployment

## Standard Squad Size

**5 playable characters** are deployed in a normal mission.

Story-required characters count toward the five.

## Large Characters

Large characters still count as one deployment slot.

Their physical footprint is already a substantial tactical cost.

---

# 6. Unit Sizes

There are only two gameplay size categories.

## Normal

- Occupies 1 tile.
- Covers the majority of playable and enemy units.

## Large

- Occupies a 2x2 footprint.
- Usually has higher HP and Defense.
- Often has lower Move.
- Requires wider routes.
- Cannot use some small pieces of cover effectively.
- Is easier to surround and block.

Large does not automatically mean Smash type or superior combat strength.

Examples:

- Vacuum Juggernaut: Large Bind displacement unit.
- Refrigerator Bastion: Large Smash defensive unit.

---

# 7. Core Stats

The game uses six visible combat stats.

| Stat | Purpose |
|---|---|
| HP | Total damage the character can take before becoming Broken |
| Power | Offensive strength used in damaging attacks and Arts |
| Defense | Reduces incoming direct damage |
| Skill | Improves Hit and Crit |
| Speed | Improves evasion and supports certain character abilities |
| Move | Maximum normal movement distance |

The game does not currently use separate Strength, Magic, Resistance, Luck, or Dexterity stats.

---

# 8. Damage, Hit, and Crit

## 8.1 Damage

Prototype baseline:

**Damage = Power + Attack Might - Defense**

Minimum normal damage is 1 unless an ability explicitly prevents damage.

Type advantage or disadvantage modifies the result after this baseline.

## 8.2 Hit

Prototype baseline:

**Hit = Attack Accuracy + (Skill x 2) - (Target Speed x 2) + Type Modifier + Cover Modifier**

Most Basic Attacks should begin around **85 base accuracy** before stats and modifiers.

The game should generally avoid making routine actions depend on extremely low-probability attacks.

## 8.3 Critical Hits

Prototype baseline:

**Crit % = Skill + ability/passive modifiers**

Critical hits deal **2x damage**.

The game deliberately avoids 3x crit damage because positioning and ability combinations already create large tactical swings.

---

# 9. Smash, Pierce, Bind Triangle

The core type relationship is:

**Smash > Pierce > Bind > Smash**

### Smash

Represents:

- blunt impact;
- weight;
- crushing;
- ramming;
- heavy force.

### Pierce

Represents:

- blades;
- points;
- staples;
- needles;
- concentrated precision.

### Bind

Represents:

- cords;
- hoses;
- cloth;
- suction;
- grappling;
- entangling;
- redirection.

## Prototype Advantage Values

| Matchup | Hit | Damage |
|---|---:|---:|
| Advantage | +15% | +2 |
| Neutral | 0 | 0 |
| Disadvantage | -15% | -2 |

Neutral attacks ignore the triangle.

Individual Arts may have a different type from a character's primary identity when thematically appropriate.

---

# 10. Counterattacks

Characters automatically counter with their **Basic Attack** when attacked if:

- the attacker is within Basic Attack range;
- line of sight is valid;
- the defender is able to act;
- the defender is not transformed by Human Gaze.

Arts do not trigger as automatic counters.

The combat forecast displays counter damage before the player commits.

There is no universal Fire Emblem-style Speed doubling system.

Extra attacks should come from specific abilities and character identities rather than a global Speed threshold.

---

# 11. Cover

The game uses only two primary cover levels.

## Half Cover

Prototype effect:

**+25% ranged evasion**

Often destructible.

Examples:

- boxes;
- book stacks;
- cushions;
- small appliances.

## Full Cover

Blocks direct line of sight.

Usually indestructible or much harder to destroy.

Examples:

- furniture legs;
- cabinets;
- walls;
- large fixed household structures.

The game does not currently use facing, flanking bonuses, prone states, or complex elevation rules.

---

# 12. Environmental Interaction

Maps should usually contain one major environmental idea, occasionally two.

Possible examples:

- spilled liquid that increases movement cost;
- hot stove tiles;
- fragile cover;
- sticky surfaces;
- switches;
- moving furniture;
- narrow passages;
- activatable household hazards.

The environment should improve tactical decisions without becoming a puzzle game separate from combat.

---

# 13. Push, Pull, and Collision

Forced movement is a major combat tool.

Characters such as Vacuum, Fan, Cable, and Smash-focused units rely on displacement.

## Collision

If a unit is pushed into solid terrain, it takes a small amount of collision damage.

Prototype value:

**2 to 3 collision damage**

If a unit is pushed into another unit, both may take collision damage.

Forced movement should be reliable enough to support planned combos.

---

# 14. Art Reliability

The game distinguishes between combat uncertainty and tactical reliability.

## Uses Hit Chance

- damaging Basic Attacks;
- damaging Arts;
- status effects attached to attacks, if the attack must hit first.

## Guaranteed

- pure ally repositioning;
- pure enemy displacement against normal enemies;
- healing;
- terrain creation;
- terrain destruction;
- objective interaction;
- support effects that do not require an attack.

Bosses and certain heavy enemies may reduce forced movement distance or display explicit immunity.

The player should not lose a carefully constructed positional plan because a non-damaging utility move randomly failed.

---

# 15. Character Kit Structure

Every playable character is built around:

- **1 Basic Attack**
- **2 Standard Arts**
- **1 Passive**
- **1 Signature Art or equivalent paralogue unlock**
- **1 Item slot**

Signature Arts are unlocked through character-specific paralogues.

There are no traditional cooldowns.

---

# 16. Noise

Noise is a shared party meter.

## Prototype Threshold

**0 / 6 Noise**

## Typical Costs

| Action | Typical Noise |
|---|---:|
| Basic Attack | 0 |
| Quiet utility Art | 0 to 1 |
| Standard Art | 1 to 2 |
| Strong Art | 2 |
| Very loud Signature Art | 3 |

## Overflow

Noise overflow is retained.

Example:

- Current Noise: 5/6
- Art produces +3
- Gaze triggers at 6
- Remaining Noise after trigger: 2/6

This prevents the player from exploiting the threshold by intentionally using the loudest possible Art at 5/6.

Noise resets between battles.

---

# 17. Human Gaze

Human Gaze is the signature battlefield mechanic.

## Trigger

When Noise reaches the threshold, the action that crossed the threshold resolves first.

Then the acting character's tile becomes the default **Attention Point**.

Prototype Gaze area:

**3x3 tiles centered around the Attention Point**

## Watched Units

Ordinary awakened objects caught in Gaze:

- revert to mundane object form;
- cannot move;
- cannot act;
- cannot attack;
- cannot counterattack;
- cannot be attacked;
- still physically occupy their tiles.

This means transformed units can temporarily become physical obstacles.

## Gaze Duration

Prototype duration:

**Until the start of the next Player Phase**

Example:

- Player triggers Gaze during Player Phase.
- Unacted friendly units caught inside lose the remainder of that phase.
- Enemies caught inside skip the upcoming Enemy Phase.
- Gaze ends at the start of the next Player Phase.

## Global Quiet Rule

While **any Human Gaze is active anywhere on the battlefield**, no Noise-generating Art may be used by anyone on the field.

This applies even to units outside the watched area.

Allowed actions outside the watched area include:

- movement;
- Basic Attacks;
- items;
- objective interactions;
- true 0-Noise Arts.

Noise remains at its current value during Gaze.

This creates a deliberate rhythm between loud combat and quiet tactical phases.

## Gaze Is Not a Free Stun Combo

Characters outside the watched zone cannot attack units inside it.

The watched area is temporarily neutral to fantasy combat.

This preserves the fiction that a human is actively observing that space.

---

# 18. Expected Behavior

Some modern autonomous objects may perform limited actions under Human Gaze if those actions are consistent with what humans already expect them to do.

Examples:

### Robot Vacuum

May move while watched.

Cannot make combat attacks while watched.

### Printer

May print paper while watched.

Printed paper could change terrain after Gaze ends.

### Automatic Blinds

May open or close while watched.

### Smart Speaker

May speak or make normal device sounds while watched.

Expected Behavior should change positioning or terrain rather than letting these enemies freely attack frozen player units.

---

# 19. Cable's Gaze Exception

Cable has a story-specific interaction with Human Gaze.

Early in the story, Cable can partially resist Gaze because humans no longer remember what it originally is.

After Cable's original Function is rediscovered, this resistance is temporarily lost.

Cable's paralogue later unlocks **Slip the Gaze**.

Slip the Gaze allows Cable to:

- move up to 3 tiles while watched;
- perform noncombat interactions while watched.

Cable still cannot:

- attack;
- use Noise Arts;
- perform overt fantasy combat while observed.

---

# 20. Enemy Telegraphing

Routine enemy Basic Attacks are chosen during Enemy Phase.

High-impact enemy Arts should often be telegraphed in advance.

Examples:

- Paper Cutter shows a red line before a heavy strike.
- Herald marks a future Gaze area.
- Wind-Up Toy shows its charge path.
- Bosses mark dangerous zones before large attacks.

Telegraphed threats are stronger and more certain than ordinary threat predictions.

---

# 21. Items

Each deployed character carries **one consumable item**.

Possible categories:

- healing;
- temporary Power increase;
- temporary Defense increase;
- status cleansing;
- simple throwable effects.

Using an item consumes the character's Action.

The game does not use:

- crafting;
- weapon durability;
- large personal inventories;
- complex equipment grids.

---

# 22. Broken Characters and Difficulty Modes

At 0 HP, a character becomes **Broken**.

The character:

- reverts to mundane object form;
- is removed from the current battle.

## Casual

Broken characters are available again in the next mission.

## Standard

A Broken character must miss the **next main-story mission**.

Optional missions and paralogues do not advance repair time.

This prevents players from clearing the penalty by running an easy side mission.

## Hardcore

Broken non-essential characters become permanently unavailable.

If a story-critical character such as Lamp becomes Broken in a context where permanent loss would make the narrative impossible, the mission fails rather than rewriting the campaign.

---

# 23. Leveling

Characters gain XP from:

- dealing damage;
- defeating enemies;
- healing and support;
- objective actions;
- recruitment interactions;
- mission completion.

Level-ups increase stats in a Fire Emblem-like presentation.

The recommended implementation is **semi-deterministic growth**.

The player still sees satisfying stat increases, but the game quietly prevents characters from drifting too far from their intended growth curve.

This makes balancing a compact campaign much easier than fully random growths.

---

# 24. Recruitment

Recruitment can occur during battle.

Typical recruitment methods include:

- Talk with a specific character;
- protect a neutral unit;
- rescue a trapped object;
- satisfy a clearly communicated battle condition;
- defeat without destroying, then speak;
- reach a recruit before an enemy does.

Recruitment conditions should never be cryptic.

When a neutral character joins during battle, they normally become controllable on the **next Player Phase**, not immediately.

---

# 25. Mission Structure

The campaign uses a mission-select structure.

Content categories include:

- Main Story
- Recruitment Missions
- Paralogues
- Optional Leveling/Reward Missions

There is no mandatory explorable hub.

Between missions, the player uses a menu-driven structure such as:

- Missions
- Roster
- Shop
- Conversations

---

# 26. Challenge Objectives

Missions may include up to three optional challenge objectives.

Examples:

- Recruit the optional character.
- Finish within a turn target.
- No character becomes Broken.
- Freeze multiple enemies in one Gaze.
- Preserve a piece of cover.
- Complete a side objective.

These should provide optional rewards without gating essential playable characters or required story content behind perfect performance.

The exact reward structure remains to be finalized.

---

# 27. Map Philosophy

Maps should be compact and tactically dense rather than enormous traditional Fire Emblem battlefields.

The ideal map:

- creates meaningful contact by turn 1 or 2;
- contains multiple viable approaches;
- gives cover real value;
- includes enough open space for displacement;
- supports Large-unit movement;
- contains one clear environmental idea;
- offers opportunities to intentionally manipulate Human Gaze.

Map size should be determined by tactical pacing rather than a fixed universal dimension.

Prototype reference map:

**15 x 11 tiles**

---

# 28. Prototype Enemy Archetypes

The reusable enemy vocabulary currently includes:

| Enemy | Type | Role |
|---|---|---|
| Bookend Guard | Smash | Defensive blocker |
| Pencil Lancer | Pierce | Mobile attacker |
| Rubber Band Snarer | Bind | Pull/control |
| Battery Cell | Neutral | Support |
| Wind-Up Toy | Smash | Charging aggressor |
| Paper Cutter | Pierce | Slow telegraphed heavy striker |
| Tape Dispenser | Bind | Terrain control |
| Robot Vacuum | Bind | Expected Behavior positioning unit |

Faction identity should often modify behavior rather than requiring a completely new enemy roster.

---

# 29. Faction Combat Identities

## Keepers

- organized formations;
- defensive positioning;
- protection and containment;
- predictable, disciplined AI.

## Unbound

- aggressive spacing;
- risk-taking;
- deliberate interaction with Human Attention;
- environmental attention hazards.

## Expected

- modern devices;
- limited legal behavior under Gaze;
- terrain and positioning manipulation during quiet phases.

## Forgotten

Not a conventional army.

Encounters are often rescue or pattern-solving battles involving weak Anchors and fragmented behavior.

---

# 30. Explicit Scope Exclusions

The base combat system should not add the following unless playtesting proves they are necessary:

- elevation systems;
- facing bonuses;
- flanking bonuses;
- weapon durability;
- crafting;
- class changes;
- generic AP;
- traditional mana;
- universal overwatch;
- elemental resistance charts;
- large status-effect stacks;
- individual initiative timelines;
- separate physical and magical defenses;
- complex equipment progression.

The game's depth should come from interactions between a small set of understandable mechanics.

---

# 31. Prototype Values That Are Not Yet Final

The following are intentionally provisional and should remain configurable during development:

- 5-character deployment
- 6 Noise threshold
- 3x3 Gaze area
- Gaze duration until next Player Phase
- +15 Hit / +2 damage type advantage
- -15 Hit / -2 damage type disadvantage
- +25 ranged evasion from Half Cover
- 2x critical damage
- 2 to 3 collision damage
- exact Hit formula coefficients
- exact XP curve
- mission turn targets

These are starting points for playtesting, not immutable rules.

---

# 32. Target Combat Feel

A good turn should involve decisions like:

- Do I use a quiet Basic Attack or spend Noise on a stronger Art?
- Can Vacuum pull this enemy out of cover so Needle can finish it?
- If I end movement here, which enemies threaten me?
- Can I intentionally trigger Gaze late in the phase to freeze several enemies?
- Is it worth freezing my own loud character to deny the enemy's next turn?
- Can I use a 0-Noise Art during Gaze to stabilize my formation?
- Should I recruit this neutral character now or spend Lamp's Action protecting the frontline?

The game succeeds when those decisions are clear, frequent, and meaningfully different from one another.
