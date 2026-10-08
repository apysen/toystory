# Household Object Tactics Game
## Character Abilities and Stats

## 1. Roster Structure

The planned playable roster contains **15 characters**.

The roster is intentionally balanced into:

- **5 Smash**
- **5 Pierce**
- **5 Bind**

The goal is not for every team to include one of each type. The even distribution simply ensures that no section of the triangle is underrepresented across the full roster.

Every character has:

- 1 Basic Attack
- 2 Standard Arts
- 1 Passive
- 1 Signature Art or equivalent paralogue unlock
- 1 item slot

Signature abilities are unlocked through character-specific paralogues.

Noise costs are part of character identity. A character who creates strong effects repeatedly should usually create more Human Attention.

### Distances

There is no grid in play (see gameplay_design.md section 4). Distances in this document are written in **tiles** as authored; one tile is **1 m** on the battlefield floor:

- **Move** is a walking distance in metres.
- **Range r** is an edge-to-edge reach of **r − 0.4 m** (range 1 = 0.6 m, melee; range 2 = 1.6 m; range 3 = 2.6 m). A minimum range of 2 becomes a minimum gap of 0.9 m.
- **Push, pull, dash and reposition** distances are metres.
- **Areas:** a 3x3 area becomes a 1.6 m-radius circle; a "short cone" reaches 1.8 m past the user with a 40° half-angle and can be aimed in any direction; a line of N tiles is a strip N m long.
- **Adjacent** means an edge-to-edge gap of 0.7 m or less.

The slice's values live in `scenes/units/unit_profiles.tscn` and `src/core/models/arts/arts.gd` already converted.

### Action-Economy Timing Rule

A character normally gets **one Movement and one Action per activation**. Ability durations and self-buffs must respect that structure.

As a general design rule, an Art that consumes the character's Action should not grant a short-lived offensive buff that expires before the character can normally attack again. A self-buff should instead do at least one of the following:

- affect the upcoming Enemy Phase;
- persist through the character's next activation;
- empower the character's next deliberate Action;
- include an attack as part of the Art itself.

This rule is used throughout the kits below.

### Scaling Value Guideline

Because characters level across the campaign, effects that are meant to stay proportionally useful should scale with the value they affect rather than relying on small flat bonuses. Prototype percentage values can still be tuned during playtesting.

As a general rule:

- healing based on a character's HP uses a percentage of maximum HP;
- defining damage bonuses use percentage damage modifiers;
- broad damage-reduction effects use percentage reduction;
- Hit, Crit, Move, Defense/Power stat buffs, displacement distance, and cover modifiers remain flat values because they are easier to forecast and are intended to interact with specific breakpoints.

Percentage damage and healing values are rounded to the nearest whole point unless an ability explicitly says otherwise. Maximum-HP healing rounds up so that small heals do not lose value at low HP totals.

---

# 2. Roster Overview

| Character | Type | Size | Move | Basic Range | Core Role | Main Reason to Deploy |
|---|---|---|---:|---:|---|---|
| Desk Lamp Warden | Smash | Normal | 5 | 1 | Protector | Keeps specific allies alive |
| Alarm Clock Chronomancer | Bind | Normal | 5 | 2 | Tempo support | Repositions allies and delays threats |
| Stapler Rogue | Pierce | Normal | 6 | 2 | Mobile control/DPS | Pins and punishes movement-restricted enemies |
| Toaster Pyromancer | Smash | Normal | 5 | 2 | AoE burst | Loud, high-output area damage |
| Teacup Cleric | Bind | Normal | 5 | 2 | Healer | Reliable sustain and cleansing |
| Umbrella Lancer | Pierce | Normal | 6 | 1 | Mobile defender | Protects moving formations |
| Toolbox Artificer | Smash | Normal | 4 | 1 | Terrain engineer | Creates, removes, and exploits cover |
| Vacuum Juggernaut | Bind | Large | 4 | 3 | Displacement tank | Strongest raw push/pull control |
| Refrigerator Bastion | Smash | Large | 3 | 1 | Area tank | Controls territory and protects groups |
| Typewriter Scribe | Bind | Normal | 5 | 3 | Tactical support | Improves plans and corrects movement mistakes |
| Cast-Iron Brawler | Smash | Normal | 5 | 1 | Bruiser | Straightforward durable offense |
| Floor Fan Gale Adept | Bind | Normal | 5 | 3 | Ranged displacement | Controls lanes from distance |
| Chef's Knife Duelist | Pierce | Normal | 6 | 1 | Glass cannon | Extreme single-target burst |
| Sewing Needle Ranger | Pierce | Normal | 5 | 4 | Sniper | Long-range precision and cover punishment |
| Mystery Cable | Pierce | Normal | 6 | 2 | Utility/control | Objective interaction, pulling, Gaze exception |

---

# 3. Prototype Level 5 Benchmark Stats

These numbers are for paper testing and early prototyping. They are not final growth targets.

| Character | HP | Pow | Def | Skill | Spd | Move | Basic Might | Range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Desk Lamp Warden | 30 | 8 | 8 | 7 | 6 | 5 | 4 | 1 |
| Alarm Clock Chronomancer | 24 | 6 | 4 | 10 | 9 | 5 | 3 | 2 |
| Stapler Rogue | 25 | 8 | 4 | 10 | 10 | 6 | 4 | 2 |
| Toaster Pyromancer | 28 | 10 | 5 | 7 | 6 | 5 | 5 | 2 |
| Teacup Cleric | 26 | 6 | 5 | 9 | 7 | 5 | 3 | 2 |
| Umbrella Lancer | 29 | 8 | 6 | 8 | 8 | 6 | 4 | 1 |
| Toolbox Artificer | 31 | 8 | 8 | 7 | 4 | 4 | 4 | 1 |
| Vacuum Juggernaut | 42 | 10 | 9 | 6 | 3 | 4 | 4 | 3 |
| Refrigerator Bastion | 48 | 8 | 11 | 5 | 2 | 3 | 5 | 1 |
| Typewriter Scribe | 24 | 6 | 4 | 10 | 7 | 5 | 3 | 3 |
| Cast-Iron Brawler | 35 | 10 | 9 | 6 | 4 | 5 | 5 | 1 |
| Floor Fan Gale Adept | 28 | 7 | 5 | 9 | 9 | 5 | 3 | 3 |
| Chef's Knife Duelist | 23 | 10 | 3 | 11 | 11 | 6 | 5 | 1 |
| Sewing Needle Ranger | 22 | 8 | 3 | 12 | 10 | 5 | 4 | 4 |
| Mystery Cable | 26 | 7 | 5 | 9 | 9 | 6 | 4 | 2 |

---

# 4. Desk Lamp Warden

**Type:** Smash  
**Size:** Normal  
**Role:** Protector / frontline support

Lamp is the protagonist and should be mechanically easy to understand. Lamp protects vulnerable allies rather than simply being the hardest unit to kill.

### Basic Attack: Pole Strike

- Range: 1
- Type: Smash
- Noise: 0
- Reliable moderate damage.

### Passive: Watchful

Once per Enemy Phase, if an adjacent ally is attacked, Lamp may intercept.

Lamp takes the hit instead and receives **20% less damage** from that intercepted hit.

### Art: Guard Beam

- Noise: +1
- Range: 3

Choose one ally.

The next hit against that ally before the next Player Phase deals 50% less damage and cannot displace them.

### Art: Flashbulb

- Noise: +1
- Shape: short cone

Deals light Smash damage and inflicts **Dazzled**.

Dazzled reduces the target's Hit by 20% on its next attack.

### Signature Art: Spotlight

- Unlock: Lamp paralogue
- Noise: +2
- Area: 3x3 within range 3

Allies inside gain:

- +20 evasion;
- immunity to forced movement;
- duration until the next Player Phase.

### Tactical Identity

Lamp is the character to deploy when another unit absolutely cannot be allowed to fall.

Lamp should be strong with fragile characters such as Knife and Needle.

---

# 5. Alarm Clock Chronomancer

**Type:** Bind  
**Size:** Normal  
**Role:** Tempo support

Alarm does not grant full extra turns. Instead, it creates additional movement opportunities and delays dangerous enemy actions.

### Basic Attack: Bellwave

- Range: 2
- Type: Bind
- Noise: 0
- Low damage.

### Passive: First Bell

At the start of Player Phase, choose one ally adjacent to Alarm. That ally gains +1 Move for the current Player Phase.

If no ally is adjacent, the passive has no effect that phase.

### Art: Wake-Up Call

- Noise: +1
- Range: 3

Choose an ally who has not acted.

That ally immediately repositions up to 2 tiles without consuming normal movement.

### Art: Snooze

- Noise: +1
- Range: moderate

Target enemy receives -2 Move during its next phase.

If the enemy is preparing a telegraphed Art, that Art is delayed by one turn.

Bosses may resist the Move penalty, but delaying the telegraph should remain useful unless explicitly immune.

### Signature Art: Second Hand

- Noise: +2

Choose an ally who has already acted.

That ally may immediately reposition up to 3 tiles.

It does not receive another Action.

### Tactical Identity

Alarm manipulates tempo without becoming an action-economy exploit.

---

# 6. Stapler Rogue

**Type:** Pierce  
**Size:** Normal  
**Role:** Mobile control / damage

Stapler excels at punishing enemies whose movement has already been disrupted.

### Basic Attack: Staple Shot

- Range: 2
- Type: Pierce
- Noise: 0

### Passive: Opportunist

Deals **20% more damage** to an enemy that:

- currently has a movement penalty; or
- was displaced earlier in the current Player Phase.

### Art: Pin

- Noise: +1
- Type: Pierce

On hit, target's Move becomes 0 during its next Enemy Phase.

### Art: Staple Burst

- Noise: +2

Make two reduced-Might attacks.

They may target:

- the same enemy; or
- two different enemies.

### Signature Art: Heavy Duty

- Noise: +3
- Shape: 4-tile line

Deals Pierce damage to every enemy in the line and Pins each target hit.

### Tactical Identity

Stapler combines especially well with Vacuum, Fan, Cable, and Alarm.

---

# 7. Toaster Pyromancer

**Type:** Smash  
**Size:** Normal  
**Role:** Loud area damage

Toaster is intentionally one of the noisiest characters in the roster.

### Basic Attack: Toast Pop

- Range: 2
- Type: Smash
- Noise: 0

Launches toast with absurd force.

### Passive: Hot Coils

After Toaster uses a +2 or +3 Noise Art, Toaster becomes **Heated**.

Toaster's next **damaging Action** gains +2 Power. Heated lasts through Toaster's next activation and is consumed when that damaging Action resolves.

Counterattacks do not consume or benefit from Heated.

### Art: Eject

- Noise: +1
- Type: Smash

Deals damage and pushes the target 2 tiles.

### Art: Flash Bake

- Noise: +2
- Shape: short cone

Deals high area damage.

### Signature Art: Overheat

- Noise: +3
- Area: 3x3 centered on Toaster

Deals very high damage to enemies in the area.

Toaster also loses a portion of its own HP.

### Tactical Identity

Toaster trades safety and Noise efficiency for explosive output.

---

# 8. Teacup Cleric

**Type:** Bind  
**Size:** Normal  
**Role:** Healing / stabilization

Teacup is deliberately straightforward. The primary healer should not require a complicated subsystem.

### Basic Attack: Steam Curl

- Range: 2
- Type: Bind
- Noise: 0
- Low damage.

### Passive: Comforting Presence

At the start of Player Phase, choose one injured ally adjacent to Teacup. That ally recovers **10% of maximum HP**, rounded up.

If no injured ally is adjacent, the passive has no effect that phase.

### Art: Warm Pour

- Noise: +1
- Range: 3

Restores **30% of the target's maximum HP**, rounded up.

### Art: Steady Sip

- Noise: 0

Removes one negative status and grants +2 Defense until the next Player Phase.

Because it is a true 0-Noise Art, Teacup can use it while Human Gaze is active, provided Teacup itself is not inside the watched area.

### Signature Art: Tea Break

- Noise: +2
- Area: small radius

Heals all allies in the area for **20% of maximum HP**, rounded up, and removes one negative status from each affected ally.

### Tactical Identity

Teacup makes risky teams more sustainable and becomes particularly valuable during Gaze phases because Steady Sip remains available.

---

# 9. Umbrella Lancer

**Type:** Pierce  
**Size:** Normal  
**Role:** Mobile defender

Umbrella protects a moving formation rather than one specific ally.

### Basic Attack: Tip Thrust

- Range: 1
- Type: Pierce
- Noise: 0

### Passive: Weatherproof

When Umbrella is not benefiting from cover, it still receives +15 ranged evasion.

### Art: Lunge

- Noise: +1

Dash up to 3 tiles in a straight line and attack.

This dash occurs after normal movement.

### Art: Canopy

- Noise: 0

Until the next Player Phase, adjacent allies count as having Half Cover against ranged attacks.

### Signature Art: Raincheck

- Noise: +2

Until the next Player Phase:

- ranged attacks against allies within 2 tiles are redirected to Umbrella when valid;
- Umbrella receives **20% less damage from attacks redirected by Raincheck**.

### Tactical Identity

Umbrella supports aggressive teams that cannot remain behind fixed terrain.

---

# 10. Toolbox Artificer

**Type:** Smash  
**Size:** Normal  
**Role:** Terrain manipulation

Toolbox changes the battlefield itself.

### Basic Attack: Hammer

- Range: 1
- Type: Smash
- Noise: 0

### Passive: Sure Footing

Toolbox ignores movement penalties from rough terrain and simple environmental hazards.

### Art: Deploy Brace

- Noise: +1

Creates temporary Half Cover on an adjacent empty tile.

Only one Brace may exist per Toolbox at a time.

### Art: Dismantle

- Noise: 0

Immediately destroys adjacent destructible cover or disables an adjacent environmental mechanism.

### Signature Art: Masterwork

- Noise: +2

Builds temporary Full Cover on an adjacent tile.

The cover remains until the start of the **second Player Phase after it is created**, unless destroyed earlier.

### Tactical Identity

Toolbox is valuable on maps where controlling line of sight and terrain matters more than raw damage.

---

# 11. Vacuum Juggernaut

**Type:** Bind  
**Size:** Large  
**Role:** Heavy displacement

Vacuum is the roster's strongest geometry-control character.

### Basic Attack: Hose Lash

- Range: 3
- Type: Bind
- Noise: 0

### Passive: Heavy Chassis

Forced movement against Vacuum is reduced by 1 tile.

### Art: Suction

- Noise: +1

Pull one normal enemy toward Vacuum by up to 3 tiles.

Low or no damage.

The pull is guaranteed against normal enemies.

### Art: Blowback

- Noise: +1
- Shape: cone

Pushes targets 2 tiles.

### Signature Art: Full Power

- Noise: +3
- Shape: wide cone

Pulls all enemies in the area toward Vacuum and deals Bind damage.

### Tactical Identity

Vacuum turns enemy formations into setup opportunities for Toaster, Stapler, Knife, or environmental hazards.

---

# 12. Refrigerator Bastion

**Type:** Smash  
**Size:** Large  
**Role:** Area tank

Refrigerator owns territory rather than chasing enemies.

### Basic Attack: Door Slam

- Range: 1
- Type: Smash
- Noise: 0

### Passive: Immovable

Cannot be pushed or pulled by normal effects.

### Art: Hold the Line

- Noise: 0

Refrigerator becomes **Anchored** until the next Player Phase. While Anchored:

- Refrigerator gains +4 Defense;
- Refrigerator cannot be repositioned by allied movement effects;
- adjacent allies gain +2 Defense.

Refrigerator's normal **Immovable** passive still prevents enemy push and pull effects.

### Art: Cold Front

- Noise: +1

Creates a chilled area around Refrigerator.

Enemies beginning movement in the area lose 2 Move for that activation.

### Signature Art: Shelter

- Noise: +2

Adjacent allies:

- become immune to forced movement;
- receive **25% less damage** from incoming attacks;
- duration until the next Player Phase.

### Tactical Identity

Refrigerator is strongest when the player wants to hold a doorway, objective, or defensive cluster.

---

# 13. Typewriter Scribe

**Type:** Bind  
**Size:** Normal  
**Role:** Tactical support

Typewriter improves accuracy and allows the player to correct movement decisions.

### Basic Attack: Ribbon Snap

- Range: 3
- Type: Bind
- Noise: 0

### Passive: Proofread

Allies within 2 tiles gain +5 Hit.

### Art: Underline

- Noise: +1

Marks one enemy.

The next two attacks against that target gain:

- +15 Hit;
- **+15% damage**;
- ignore Half Cover's accuracy bonus.

### Art: Revision

- Noise: +1

Choose an ally who has moved but has not yet acted.

Return that ally to the tile where it began the Player Phase and restore its movement.

This effectively allows the player to reconsider a movement decision before the Action is committed.

### Signature Art: Final Draft

- Noise: +2

All allies within 3 tiles gain:

- +10 Hit;
- triangle disadvantage is treated as neutral;
- duration until the next Player Phase.

### Tactical Identity

Typewriter makes complex plans more reliable without dealing much direct damage.

---

# 14. Cast-Iron Brawler

**Type:** Smash  
**Size:** Normal  
**Role:** Bruiser

Cast Iron is intentionally uncomplicated.

### Basic Attack: Pan Swing

- Range: 1
- Type: Smash
- Noise: 0
- High Might.

### Passive: Seasoned

The first damaging hit Cast Iron receives each Enemy Phase deals **20% less damage**.

### Art: Clang

- Noise: +1

Heavy attack that inflicts -15 Hit on the target's next attack.

### Art: Heat Up

- Noise: +1

Cast Iron gains +3 Defense until the next Player Phase and becomes **Heated**.

Cast Iron's next **damaging Action** gains +3 Power. Heated lasts through Cast Iron's next activation and is consumed when that damaging Action resolves.

Counterattacks do not consume or benefit from Heated.

### Signature Art: Kitchen Crash

- Noise: +3

Charge up to 3 tiles and slam the destination.

Deals Smash damage in a small area.

### Tactical Identity

Cast Iron is for players who want reliable frontline offense without managing a specialized subsystem.

---

# 15. Floor Fan Gale Adept

**Type:** Bind  
**Size:** Normal  
**Role:** Ranged lane control

Fan controls movement and firing lanes from a safe distance.

### Basic Attack: Air Burst

- Range: 3
- Type: Bind
- Noise: 0

### Passive: Tailwind

An ally beginning movement adjacent to Fan gains +1 Move for that activation.

### Art: Gust

- Noise: +1

Push one target up to 3 tiles.

### Art: Crosswind

- Noise: +1

Creates a 3-tile wind lane until the next Player Phase.

Ranged attacks passing through the lane suffer -20 Hit.

### Signature Art: High Setting

- Noise: +3
- Shape: large cone

Damages and pushes every unit in the area up to 3 tiles.

### Tactical Identity

Fan is less committed than Vacuum and can manipulate dangerous lanes from range.

---

# 16. Chef's Knife Duelist

**Type:** Pierce  
**Size:** Normal  
**Role:** High-risk burst damage

Knife should feel dangerous both to the enemy and to itself.

### Basic Attack: Slice

- Range: 1
- Type: Pierce
- Noise: 0
- High damage and strong Crit potential.

### Passive: Duelist

If no other unit is adjacent to Knife's target, Knife gains:

- **+20% damage**;
- +10 Crit.

### Art: Dash Cut

- Noise: +1

Attack an adjacent enemy and move through it to the opposite empty tile if valid.

### Art: Carve

- Noise: +2

Powerful single-target attack with +25 Crit.

Knife suffers -2 Defense until the next Player Phase.

### Signature Art: Finishing Cut

- Noise: +3

Deals substantially increased damage against targets below 40% HP.

### Tactical Identity

Knife wants isolated targets and aggressive positioning. It should produce some of the highest single-target damage in the game while remaining easy to punish.

---

# 17. Sewing Needle Ranger

**Type:** Pierce  
**Size:** Normal  
**Role:** Precision sniper

Needle is the safest dedicated damage dealer but performs poorly when forced into close quarters or against high-Defense Smash units.

### Basic Attack: Needle Shot

- Range: 4
- Type: Pierce
- Noise: 0

### Passive: Fine Point

Half Cover provides only +10 ranged evasion against Needle instead of +25.

### Art: Thread the Gap

- Noise: +1

Precision attack that completely ignores cover bonuses.

### Art: Hemline

- Noise: +1

Attaches thread to the target.

If the target moves more than 2 tiles during its next activation, it takes damage.

### Signature Art: Running Stitch

- Noise: +2
- Shape: 5-tile line

Deals Pierce damage to every enemy along the line.

### Tactical Identity

Needle punishes exposed lanes and enemies that rely on Half Cover.

---

# 18. Mystery Cable

**Type:** Pierce  
**Size:** Normal  
**Role:** Utility / control / Gaze interaction

Cable's connector is used like a spear for its direct attacks, while its body supports pulling and objective interaction.

### Basic Attack: Plug Jab

- Range: 2
- Type: Pierce
- Noise: 0

### Passive: Loose End

Cable may perform noncombat objective interactions from up to 2 tiles away.

Examples:

- pull a switch;
- grab an item;
- activate a mechanism;
- interact with a mission objective.

### Art: Snag

- Noise: +1
- Type: Pierce for triangle calculations

On hit, target suffers -2 Move during its next phase.

### Art: Yank

- Noise: +1

Either:

- pull an enemy 2 tiles toward Cable; or
- pull an ally up to 2 tiles without damage.

Ally movement is guaranteed.

### Paralogue Unlock: Slip the Gaze

Cable's paralogue does not simply grant another damage button.

It upgrades Cable's relationship with Human Gaze.

While watched, Cable may:

- move up to 3 tiles;
- perform noncombat interactions.

Cable may not:

- attack;
- use Noise Arts;
- use overt combat effects while a human is watching.

### Tactical Identity

Cable is the best objective runner in the roster and gains unique late-game value on Gaze-heavy maps.

---

# 19. Roster Overlap Audit

The roster deliberately separates similar roles.

## Lamp vs Umbrella vs Refrigerator

- Lamp protects one critical ally.
- Umbrella protects moving formations, especially against ranged attacks.
- Refrigerator protects a fixed area.

## Vacuum vs Fan

- Vacuum pulls enemies toward itself and creates close-range clusters.
- Fan controls lanes from distance.

## Alarm vs Typewriter

- Alarm creates new movement opportunities.
- Typewriter helps correct or improve a movement decision already made.

## Stapler vs Needle

- Stapler says: **do not move**.
- Needle says: **you may move, but you will pay for it**.

## Knife vs Needle

- Knife wants to be adjacent to an isolated target.
- Needle wants long, clean sightlines.

## Toaster vs Cast Iron

- Toaster is explosive, loud, and area-focused.
- Cast Iron is steady, durable, and reliable.

---

# 20. Example Team Identities

## Defensive Formation

- Lamp
- Teacup
- Refrigerator
- Needle
- Typewriter

Strengths:

- protection;
- healing;
- ranged precision;
- high reliability;
- strong objective defense.

Weaknesses:

- lower mobility;
- less explosive displacement.

## Mobile Control

- Umbrella
- Knife
- Stapler
- Alarm
- Fan

Strengths:

- high movement;
- lane control;
- isolated-target pressure;
- repositioning.

Weaknesses:

- less raw durability;
- positioning mistakes can be punished quickly.

## Controlled Chaos

- Vacuum
- Toaster
- Cable
- Toolbox
- Cast Iron

Strengths:

- displacement;
- terrain manipulation;
- loud burst damage;
- unusual map interaction.

Weaknesses:

- Noise builds quickly;
- some members are slow;
- requires careful setup.

---

# 21. Progression Philosophy

The game deliberately limits progression complexity.

Each character primarily grows through:

1. normal leveling and stat improvement;
2. one character-specific paralogue that unlocks a Signature ability.

The game does not currently use:

- class promotion trees;
- weapon rarity ladders;
- attachment crafting;
- deep skill trees;
- equipment optimization systems.

The object is the character. Progression should reinforce that identity rather than replace it with loot progression.

---

# 22. Growth Rates

Exact numerical growth rates are intentionally **not locked yet**.

Recommended growth identities:

- Lamp: HP, Defense, balanced Skill
- Alarm: Skill, Speed
- Stapler: Skill, Speed, moderate Power
- Toaster: Power, HP
- Teacup: Skill, balanced durability
- Umbrella: Speed, balanced Power/Defense
- Toolbox: HP, Defense
- Vacuum: HP, Power, Defense
- Refrigerator: HP, Defense
- Typewriter: Skill, support-oriented growth
- Cast Iron: HP, Power, Defense
- Fan: Speed, Skill
- Knife: Power, Skill, Speed
- Needle: Skill, Speed, moderate Power
- Cable: Speed, Skill, flexible utility

A semi-deterministic growth system is preferred so characters remain near their intended role over a compact campaign.

---

# 23. Balance Principles

When tuning the roster:

- no character should be mandatory outside story requirements;
- 0-Noise Arts should remain valuable without becoming universally superior during Gaze;
- noisy characters should feel powerful enough to justify accelerating Human Attention;
- Large units should feel strong but never become automatic picks;
- Pierce should not collapse against Smash to the point of dealing functionally zero damage in normal encounters;
- support characters must still contribute when their specialized setup is not needed;
- Signature Arts should deepen a character's identity rather than replace their basic kit.

These kits are intended as the first full-roster prototype, not final balance values.
