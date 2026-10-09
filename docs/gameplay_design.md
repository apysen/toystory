# Household Object Tactics Game
## Gameplay Design Document

## 1. High-Level Combat Identity

The game is a compact turn-based tactics RPG about ordinary household objects that become fantasy-like warriors whenever humans are not watching.

The combat direction combines three major influences:

- **Fire Emblem** for player-phase and enemy-phase structure, combat forecasts, counterattacks, character recruitment, leveling, and a simple type triangle.
- **Mario + Rabbids: Sparks of Hope** for compact battlefields, free movement inside a movement radius (no grid), a free camera centred on the character being moved, cover, destructible terrain, and highly positional ability use.
- **XCOM** for ranges measured as a set radius per attack and ability, with a hit chance that cover lowers.
- **Into the Breach-style clarity** for telegraphed high-impact enemy actions and a strong emphasis on understanding danger before committing to a move.

The unique mechanic is **Human Gaze**. Player Arts can create Noise. When enough Noise is generated, a human looks toward the battlefield. Objects caught in that gaze revert to mundane object form and stop fighting temporarily. While any Gaze is active, all player Noise-generating Arts are disabled across the entire battlefield. Regular enemies do not use the player Noise/Art economy.

Presentation is **HD-2D** (Square Enix's Octopath / Triangle Strategy look, and the Kowloon project's diorama): lit, modelled 3D environments with 2D pixel-art characters on cards that turn to face the camera. See section 4.5.

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

1. **Movement** — free movement anywhere inside the character's movement radius
2. **One Action**

The Action can be:

- Basic Attack
- Art
- Item
- Interaction
- Recruitment conversation
- Mission objective action

A character normally moves first, then acts. Until it acts, its move can be undone (it returns to where its activation began), and the player can switch to another character and come back; a character left without acting stays where it was left.

Once the Action is committed, that character's activation ends. There is no dash, team jump, or movement after acting.

## Enemy Phase

All enemies activate according to their AI priorities.

High-impact enemy **Techniques** are often telegraphed during the preceding Player Phase so the player has an opportunity to respond. Regular enemies do not use player-style Art menus or the shared Noise economy.

## No Universal Action Points

The game does not use a generic AP system.

The simple movement-plus-action structure should remain the baseline unless a specific character ability deliberately breaks it.

---

# 4. Movement and Tactical Preview

## 4.1 Movement Area

There is no grid. Selecting a character takes control of it: the camera centres on it and it can be steered freely (stick, keys, or a click on the floor) anywhere inside its movement area.

The area is drawn on the floor. It is measured as a walking distance from where the activation began (Move, in metres), so it bends around furniture, shrinks through spilled liquid, and is blocked by enemies; allies can be walked past but not stood on. A marker shows where the move began, so undoing it is always obvious.

The player should never need to measure distances by eye: the area shows where the character can go, and each action's reach is drawn as a ring when it is chosen.

## 4.2 Dynamic Threat Arcs

While the player moves a character, the game continuously evaluates where it stands (Fire Emblem Fortune's Weave style).

Every enemy capable of threatening that character there draws a thin pulsing arc from itself to the character. Colour says what kind of hit it is (normal, high crit, type advantage, push or pull); brightness follows the hit chance; pulses travel toward the target.

Threat lines should distinguish between:

- possible Basic Attacks;
- known ranged threats;
- telegraphed Arts;
- displacement attacks;
- committed boss attacks.

The game should never hide a valid threat simply because the attack has low Hit probability.

Lower-risk attacks can be displayed less prominently, but they remain visible.

## 4.3 Predicted HP

As the character moves, the HP bar above it shows the projected result of stopping where it currently is: the HP it would lose pulses, and a red X appears when it could be Broken.

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

Inspecting a specific threat (clicking the enemy) can show exact details such as:

- enemy name;
- damage;
- Hit chance;
- Crit chance;
- type advantage;
- displacement path.

## 4.4 Displacement Preview

If a threatened attack could push or pull the selected unit, the projected movement is shown with an arrow on the floor.

If collision damage would occur, the preview should state it explicitly.

Example for a unit with 30 Max HP:

**8 Damage + 3 Collision**

The preview should always show the actual integer HP loss, even when the underlying effect is percentage-based.

## 4.5 Presentation, Camera, and Choosing an Action

- **Environment:** a modelled 3D room at toy scale, lit and shaded; furniture placed exactly where the rules put it, so what blocks a character is what the player sees.
- **Characters:** 2D pixel art on cards that face the camera. Side views only; a card mirrors to show which way the character is heading relative to the camera. Cards stay whole in front of or behind furniture, and show as a silhouette when hidden.
- **Camera:** a free perspective orbit (rotate, tilt within limits, zoom, pan). It centres on the character being controlled and glides to each enemy as it acts.
- **Interface:** just the game, a minimap (bottom right, click to move the camera), the objective (top left), and the turn number and Noise meter (bottom left). Units carry small HP bars.
- **Action ring:** when the player is ready to act, a ring of every available action appears above the character (Paper Mario: The Thousand-Year Door). The hovered action's description sits in a box above the ring; arrows either side, left/right or the D-pad turn it one action at a time.
- **Battle preview:** after an action and target are chosen, a head-to-head preview appears at the bottom of the screen with Fire Emblem's information — both sides' HP before and after, damage, hit and crit for each strike in order including counters — and a red X beside any strike that would Break its target. It is styled in the game's own toy-box personality.

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

Units are circles on the floor; ranges are measured edge to edge.

## Normal

- Body radius 0.3 m.
- Covers the majority of playable and enemy units.

## Large

- Body radius 0.75 m (the old 2x2 footprint).
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

**Base Damage = Power + Attack Might - Defense**

Minimum normal damage is 1 unless an ability explicitly prevents damage.

Percentage-based damage modifiers are applied to the post-Defense result. The prototype calculation order is:

1. Calculate Base Damage from Power, Might, and Defense.
2. Apply the Smash/Pierce/Bind damage modifier.
3. Apply any other damage-dealt or damage-taken modifiers.
4. Round once to the nearest whole number.
5. Enforce the normal minimum of 1 damage unless an effect explicitly reduces damage to 0.

This allows offensive identities and defensive effects to remain relevant as stats increase later in the campaign.

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

## 8.4 Scaling Value Convention

Values should scale according to what they represent.

### Usually Percentage-Based

Use percentages for outcomes that are intended to remain proportionally meaningful throughout the campaign, including:

- damage bonuses and penalties;
- damage reduction;
- healing based on Max HP;
- passive effects whose identity should remain relevant at low and high levels.

### Usually Flat or Percentage-Point Based

Use flat values for structural tactical quantities that should remain easy to reason about, including:

- Move;
- range;
- push and pull distance;
- Noise;
- Gaze size and duration;
- Hit, Crit, and evasion modifiers, expressed as percentage-point changes;
- terrain movement costs.

Short-lived Power or Defense buffs may remain flat only while the game's stat curve stays compressed. They should be rechecked against late-game values during balance testing.

The goal is to avoid early-game flat bonuses becoming irrelevant later without turning every mechanic into percentage math.

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
| Advantage | +15 percentage points | +20% |
| Neutral | 0 | 0 |
| Disadvantage | -15 percentage points | -20% |

The damage modifier is applied to post-Defense damage before final rounding. This keeps the triangle meaningful as Power, Might, Defense, and HP increase later in the campaign.

**Neutral-type attacks** ignore the triangle entirely. A neutral matchup between typed attacks simply receives no advantage or disadvantage modifier.

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

**+25 percentage points ranged evasion**

It applies to a ranged attack when the half-cover object stands close to the target (within about 1.2 m), between it and the shot. Half cover blocks movement but not line of sight. Large units are too big to hide behind it.

Often destructible.

Examples:

- boxes;
- book stacks;
- cushions;
- small appliances.

## Full Cover

Blocks direct line of sight: any shot whose line crosses it is impossible.

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

If a unit is pushed into solid terrain, it takes collision damage that scales with the unit rather than becoming irrelevant later in the campaign.

Push and pull distances are in metres (one old tile = 1 m). A pushed unit slides in a straight line and stops at whatever it hits; a pulled unit stops when it touches the puller or something is in the way.

Prototype value:

**10% of the affected unit's Max HP, rounded up**

Collision damage ignores Defense.

If a unit is pushed into another unit, both units take collision damage based on their own Max HP. A single forced-movement effect can cause at most one collision-damage instance per affected unit.

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

Then the acting character's position becomes the default **Attention Point**.

Prototype Gaze area:

**A circle of 1.6 m radius around the Attention Point** (the old 3x3 tiles)

## Watched Units

Ordinary awakened objects caught in Gaze:

- revert to mundane object form;
- cannot move;
- cannot act;
- cannot attack;
- cannot counterattack;
- cannot be attacked;
- still physically occupy their space.

The watched circle itself is closed off: its edge stands as a wall of light that no unit outside it may walk, be pushed or pulled across until the Gaze ends.

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

While **any Human Gaze is active anywhere on the battlefield**, no player Noise-generating Art may be used.

This applies even to playable units outside the watched area. Regular enemies do not have Noise Arts, so they do not interact with this restriction through the Noise system.

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

- move up to 3 m while watched;
- perform noncombat interactions while watched.

Cable still cannot:

- attack;
- use Noise Arts;
- perform overt fantasy combat while observed.

---

# 20. Enemy Telegraphing

Routine enemy Basic Attacks are chosen during Enemy Phase.

High-impact enemy **Techniques** should often be telegraphed in advance. Enemy Techniques are not player Arts and do not use Noise. They exist to create clear tactical problems rather than to give enemies full player-style movesets.

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

**15 m x 11 m** (authored on a 1 m layout grid; play itself has no grid)

---

# 28. Enemy Design and Prototype Archetypes

## 28.1 Enemy Design Philosophy

Enemies should **not** use the same full moveset structure as playable characters.

Playable characters are designed to create combinations. Enemies are designed to create clear tactical problems.

The average enemy should be understandable almost immediately from its silhouette, type, Basic Attack, and one defining behavior. The player should not need to open several ability pages to understand what a normal enemy can do.

Regular enemies also do **not** use the shared Noise meter and do not have player-style Noise Arts. Human Attention caused by enemies should come from explicit, telegraphed encounter mechanics such as an alarm, ringing object, squeaky mechanism, or boss-specific effect rather than hidden Noise generation.

### Regular Enemies

A normal enemy has:

- **1 Basic Attack**
- **1 defining Trait or built-in attack effect**

The defining mechanic may be something like pulling, charging, resisting displacement, or creating terrain. It should usually be part of the enemy's normal behavior rather than a menu containing several choices.

### Specialist Enemies

A less-common specialist may have:

- **1 Basic Attack**
- **1 Technique**

The Technique should be the primary reason that enemy matters. It may be telegraphed when appropriate.

### Elite or Named Enemies

An elite or recurring rival may have:

- **1 Basic Attack**
- **1 Technique**
- **1 Passive or faction-specific Trait**

This is enough to make an elite distinctive without giving it a playable-character-sized kit.

### Bosses

Bosses may have:

- **1 Basic Attack**
- **2 to 3 encounter mechanics or Techniques**
- **1 Passive or phase change when needed**

Boss complexity should come primarily from the encounter, map, telegraphs, Human Gaze interactions, reinforcements, and objectives rather than from a large ability bar.

## 28.2 Prototype Enemy Archetypes

| Enemy | Type | Basic Attack | Defining Mechanic |
|---|---|---|---|
| **Bookend Guard** | Smash | **Bash** | Difficult to displace and holds/protects a lane |
| **Pencil Lancer** | Pierce | **Thrust** | Gains value from straight-line approach or charge movement |
| **Rubber Band Snarer** | Bind | **Snap** | Successful attacks pull the target 1 m |
| **Battery Cell** | Neutral | **Zap** | Specialist Technique: temporarily powers up one nearby ally |
| **Wind-Up Toy** | Smash | **Ram** | Ram becomes stronger or pushes farther after a long approach |
| **Paper Cutter** | Pierce | **Cut** | Specialist Technique: telegraphed **Cutting Line** attack |
| **Tape Dispenser** | Bind | **Tape Lash** | Creates sticky terrain as part of its attack pattern |
| **Robot Vacuum** | Bind | **Bump** | **Expected Behavior:** may move during Human Gaze, but cannot attack while watched |

Faction identity should modify how these archetypes behave rather than requiring a completely new enemy roster for every faction.

## 28.3 Readability Rule

When the player inspects a regular enemy, the UI should normally need to communicate only:

- type;
- movement and attack range;
- Basic Attack;
- defining Trait or Technique;
- current telegraph, if any.

If a normal enemy requires the player to memorize several cooldowns or conditional abilities, the enemy is probably too complicated.

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
- +15 percentage-point Hit / +20% damage type advantage
- -15 percentage-point Hit / -20% damage type disadvantage
- +25 percentage-point ranged evasion from Half Cover
- 2x critical damage
- 10% Max HP collision damage
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
