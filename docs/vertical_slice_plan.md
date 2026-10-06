# Household Object Tactics Game
## Vertical Slice Plan

## 1. Purpose

The vertical slice should prove that the game's core idea works before full campaign production begins.

The slice is not intended to demonstrate every character, every faction, every menu, or the full narrative.

It should answer four questions:

1. Is the basic combat loop fun?
2. Is Human Gaze fun to manipulate rather than merely punitive?
3. Is the movement forecast readable and useful?
4. Can the intended 64x64 pixel-art presentation support the game without excessive production cost?

The slice should be production-minded and small enough for two people to complete.

---

# 2. Slice Structure

The recommended vertical slice is built around one polished tactical scenario:

# **Under the Desk**

This can begin as a non-canon systems test and later be adapted into a real optional mission if desired.

The slice includes:

1. Minimal mission-select screen
2. Team preview / deployment
3. Short pre-battle conversation
4. One complete tactical battle
5. Mid-battle recruitment
6. Human Gaze sequence
7. Boss with telegraphed attack
8. Post-battle results screen
9. Short post-battle conversation
10. Return to mission menu

The goal is to prove the complete moment-to-moment loop without building the full campaign framework.

---

# 3. Core Playable Squad

The test squad contains five characters:

| Character | Purpose in Slice |
|---|---|
| Desk Lamp Warden | Protection and Smash matchup |
| Stapler Rogue | Pierce damage and movement control |
| Toaster Pyromancer | Loud AoE and Noise pressure |
| Teacup Cleric | Healing and 0-Noise utility |
| Vacuum Juggernaut | Large-unit pathing and displacement |

This team tests:

- all three triangle types;
- one Large unit;
- melee and ranged combat;
- healing;
- push/pull;
- high Noise generation;
- 0-Noise Art value during Gaze.

---

# 4. Optional Recruit

**Umbrella Lancer** begins as a neutral unit on the map.

Lamp may recruit Umbrella by:

- moving adjacent;
- spending Lamp's Action on **Talk**.

Umbrella becomes controllable on the next Player Phase.

This tests:

- Fire Emblem-style battlefield recruitment;
- whether recruitment is worth giving up an Action;
- optional objective communication;
- whether the UI clearly distinguishes neutral, allied, and hostile units.

---

# 5. Map Size

Prototype map:

**15 x 11 tiles**

Coordinate system:

- bottom-left = (1,1)

The map represents the study floor underneath and around a desk.

The battlefield should feel large from the objects' point of view while still being compact enough for immediate engagement.

---

# 6. Player Deployment

Starting positions:

- Lamp: (3,2)
- Stapler: (4,2)
- Toaster: (3,3)
- Teacup: (4,3)
- Vacuum: occupies (1-2, 2-3)

The squad should have immediate tactical options without beginning already surrounded.

---

# 7. Full Cover

Full cover / impassable furniture:

- Desk leg: (6,3)
- Desk leg: (6,8)
- Chair leg: (10,5)
- Cabinet block: (13,8), (14,8), (13,9), (14,9)

These objects:

- block movement;
- block direct line of sight;
- define major lanes.

Large-unit routes must remain at least two tiles wide where Vacuum is expected to travel.

---

# 8. Half Cover

Half-cover objects:

- Books: (5,5)
- Books: (8,3)
- Cardboard box: (8,7)
- Books: (11,8)
- Small box: (12,4)

Prototype effect:

**+25% ranged evasion**

The cardboard boxes are destructible.

The book stacks are durable.

This tests whether destructible cover produces meaningful tactical decisions.

---

# 9. Environmental Gimmick

A spilled drink occupies:

- (9,6)
- (10,6)
- (11,6)
- (10,7)

Effect:

**Entering a spill tile costs +2 movement.**

No damage.

No electricity interaction.

No status effect.

The slice should test one clear terrain concept rather than stacking multiple systems.

---

# 10. Enemy Placement

## Pencil Lancer A

- Type: Pierce
- Position: (7,3)
- Role: fast attacker
- Purpose: immediately tests Lamp's favorable Smash matchup.

## Rubber Band Snarer

- Type: Bind
- Position: (7,6)
- Role: pull/control
- Purpose: encourages Vacuum to remove it from cover.

## Bookend Guard

- Type: Smash
- Position: (9,4)
- Role: defensive blocker
- Purpose: makes poor Pierce matchups visible.

## Pencil Lancer B

- Type: Pierce
- Position: (11,3)
- Role: lower-lane pressure
- Purpose: threatens the path toward Umbrella.

## Tape Dispenser

- Type: Bind
- Position: (11,7)
- Role: terrain control
- Purpose: combines movement restriction with the spilled-drink area.

## Robot Vacuum

- Type: Bind
- Position: (12,9)
- Role: Expected Behavior test
- Purpose: continues moving during Human Gaze but cannot attack.

## Paper Cutter Captain

- Type: Pierce elite
- Position: (13,10)
- Role: boss / telegraphed heavy attacker
- Purpose: tests boss readability without relying on a giant HP pool.

---

# 11. Umbrella Position

Umbrella begins neutral at:

**(13,4)**

Pencil Lancer B threatens Umbrella's side of the map.

The player must decide whether Lamp should:

- remain near the team and protect allies;
- cross the lower lane to recruit Umbrella.

This creates a meaningful recruitment cost.

---

# 12. Primary Objective

**Defeat the Paper Cutter Captain.**

The battle ends when the Captain is defeated and any required story condition is satisfied.

---

# 13. Optional Objectives

Track three optional stars during the slice:

### Star 1

Recruit Umbrella.

### Star 2

Finish in 7 turns or fewer.

### Star 3

No character becomes Broken.

These rewards do not need permanent campaign consequences in the first slice.

The purpose is to test whether challenge objectives encourage interesting play.

---

# 14. Enemy AI

AI should be intentionally readable.

## Pencil Lancer

Priority:

1. triangle-advantaged targets;
2. exposed targets;
3. low-HP targets.

## Bookend Guard

Holds the central route.

Does not chase distant targets unless the local defense collapses.

## Rubber Band Snarer

Prioritizes pulling player units out of cover.

## Tape Dispenser

Prioritizes movement disruption and lane denial.

## Robot Vacuum

Aggressively repositions.

During Human Gaze, it may continue normal movement but cannot attack.

## Paper Cutter Captain

Uses a telegraphed heavy line attack every other Enemy Phase when possible.

---

# 15. Paper Cutter Boss Kit

The boss should test mechanics rather than simply have inflated stats.

## Heavy Frame

Push/pull distance against the Captain is reduced by 1 tile.

## Cutting Line

Telegraphs a 1x5 attack lane.

The attack resolves on the following Enemy Phase unless:

- the Captain is displaced;
- the Captain is incapacitated;
- the marked lane is abandoned.

## Paper Guard

The Captain begins near destructible cardboard cover.

The player can:

- destroy the cover;
- flank;
- displace the Captain;
- freeze it with Human Gaze;
- exploit Smash advantage.

---

# 16. Noise and Gaze Test

The slice uses:

- Noise threshold: 6
- Gaze area: 3x3
- Overflow enabled
- Gaze duration: until start of next Player Phase

A natural enemy cluster should form around the central map near approximately (9,5).

This should create an opportunity for Toaster to intentionally trigger Gaze while standing near multiple enemies.

When Gaze activates:

- Toaster may freeze;
- nearby enemies may freeze;
- all Noise-generating Arts across the battlefield become disabled;
- Robot Vacuum may continue normal movement;
- Teacup may still use Steady Sip if outside the watched area;
- Umbrella may still use Canopy if recruited and outside the watched area.

This sequence is the most important mechanical test in the slice.

---

# 17. Frozen Units as Terrain

When a unit transforms under Human Gaze:

- it still occupies its tile;
- other units cannot move through it;
- it cannot be attacked;
- it cannot attack.

This should be deliberately tested.

Potential later use:

- freezing a Large unit in a doorway;
- intentionally blocking an enemy route;
- using transformed objects as temporary physical obstacles.

---

# 18. Dynamic Movement Forecast Requirements

When the player selects a character and hovers a destination, the slice must display:

- reachable movement area;
- every enemy that can threaten the proposed tile;
- threat lines from those enemies;
- projected HP after expected enemy damage;
- telegraphed attack zones;
- displacement arrows where relevant;
- cover effect;
- triangle information on individual threat inspection.

The forecast must update continuously as the cursor moves.

The forecast represents:

> What happens if Enemy Phase began with the battlefield in its current state?

It must recalculate after every player action that changes the board.

---

# 19. Minimum Combat UI

The slice needs only the UI required to test the real game.

## Always Visible

- current phase;
- selected character HP;
- Noise meter;
- turn count;
- current objective;
- optional objective summary.

## On Character Selection

- movement area;
- Basic Attack range;
- Arts;
- item;
- character portrait/name;
- current HP and stats.

## On Target Selection

Fire Emblem-style combat forecast:

- damage;
- Hit;
- Crit;
- counter damage;
- type advantage/disadvantage;
- cover influence.

## During Gaze

- watched area clearly highlighted;
- transformed sprite swap;
- Noise Arts grayed out everywhere;
- tooltip: **Unavailable while Human Gaze is active**.

---

# 20. Minimal Narrative Wrapper

The slice does not need the full campaign plot.

A short pre-battle setup is enough:

- Lamp's team is moving through the study;
- Umbrella is trapped on the far side of the room;
- hostile objects are blocking the route;
- the Paper Cutter Captain is directing the opposition.

A short mid-battle Talk recruits Umbrella.

A short post-battle exchange confirms recruitment and returns the player to the mission menu.

The purpose is to test conversation flow, portraits, and recruitment without requiring a full narrative chapter.

---

# 21. Art Requirements

## Battle Sprites

Playable and enemy battle sprites use the agreed low-resolution style.

Target:

**64x64 character sprite scale**

Key rules:

- chunky visible pixels;
- limited palettes;
- strong silhouettes;
- minimal tiny detail;
- side-profile presentation where practical;
- same pixel density across characters, environment, humans, transformation sprites, and VFX.

A larger object or human may occupy more pixels, but should not use a different apparent pixel density.

## Portraits

Portraits may be more detailed than battle sprites.

## Required Slice Characters

At minimum:

- Lamp
- Stapler
- Toaster
- Teacup
- Vacuum
- Umbrella

## Required Enemy Sprites

At minimum:

- Pencil Lancer
- Rubber Band Snarer
- Bookend Guard
- Tape Dispenser
- Robot Vacuum
- Paper Cutter Captain

## Mundane Forms

Every object that can be caught in Gaze needs a mundane object sprite.

The transformation should be quick and readable.

---

# 22. Animation Requirements

Each slice character needs only enough animation to prove the production pipeline.

Minimum recommended set:

- idle;
- move;
- Basic Attack;
- one generic Art animation family;
- damage reaction;
- Broken transition;
- Gaze transformation;
- return-from-Gaze transformation.

Unique Arts can reuse some motion and VFX during the slice.

The final game may add more bespoke animations where value justifies cost.

---

# 23. Audio Requirements

The slice should establish the game's audio language.

Object actions should be derived from recognizable real-world object sounds with a cohesive retro/pixel treatment.

Examples:

- Stapler attack uses a processed staple click;
- Toaster uses spring and heating sounds;
- Vacuum uses motor and suction sounds;
- Umbrella uses fabric snap and metal movement;
- Human Gaze has a distinct attention cue.

Music should match the room rather than individual characters.

The slice needs only one battle theme and a small number of UI sounds.

---

# 24. Minimal Menu Flow

The slice should include a very small version of the eventual menu structure.

Recommended flow:

1. Mission Select
2. Team Preview
3. Start Mission
4. Battle
5. Results
6. Return to Mission Select

Do not build the full Shop, Roster, Conversations, or Paralogue system yet unless implementation is trivial.

---

# 25. What the Slice Must Test

| Question | Slice Test |
|---|---|
| Is 5-character deployment comfortable? | Full battle |
| Does the type triangle matter? | Mixed enemy roster |
| Is cover valuable? | Desk and book lanes |
| Is destructible cover worthwhile? | Boss area |
| Is displacement satisfying? | Vacuum + obstacles + spill |
| Does Large pathing work? | Vacuum movement |
| Is 6 Noise appropriate? | Toaster/Vacuum Art use |
| Is 3x3 Gaze appropriate? | Central cluster |
| Is the global Art lock during Gaze interesting? | Quiet phase |
| Is Expected Behavior fair? | Robot Vacuum |
| Are telegraphed attacks readable? | Paper Cutter |
| Are threat lines useful? | Every movement decision |
| Is predicted HP trustworthy? | Threat clusters |
| Does recruitment feel natural? | Umbrella |
| Do 0-Noise Arts matter? | Gaze phase |
| Is battle length acceptable? | Target 6 to 8 turns |

---

# 26. Playtest Metrics

The first internal tests should record:

- total turns;
- real-world battle duration;
- Noise triggers per battle;
- number of Arts used;
- number of 0-Noise Arts used during Gaze;
- number of enemies intentionally caught in Gaze;
- number of friendly units unintentionally caught in Gaze;
- average predicted HP error;
- number of times players inspect individual enemy threat lines;
- number of times recruitment is skipped;
- how often Vacuum becomes path-blocked;
- how often Half Cover materially changes a decision;
- how often the Paper Cutter telegraph changes player behavior.

Qualitative questions:

- Did Gaze feel like a tool or punishment?
- Did the player understand why Arts were disabled during Gaze?
- Did threat lines reduce tedious range checking?
- Did predicted HP feel trustworthy?
- Did the player feel comfortable intentionally accepting risk?
- Did any character feel useless during the battle?
- Was the map too open, too cramped, or too slow?

---

# 27. Recommended Development Order

## Milestone 1: Graybox Grid

Implement:

- 15x11 grid;
- movement;
- turn phases;
- placeholder units;
- basic pathfinding;
- 1x1 and 2x2 footprints.

No art polish.

## Milestone 2: Combat Math

Implement:

- Basic Attacks;
- HP;
- damage;
- Hit;
- Crit;
- type triangle;
- counters;
- cover.

## Milestone 3: Forecast UI

Implement:

- movement region;
- threat lines;
- projected HP;
- combat forecast;
- telegraph display.

This is a core feature, not late polish.

## Milestone 4: Displacement and Terrain

Implement:

- push;
- pull;
- collision;
- spill movement cost;
- destructible cover;
- Large-unit pathing.

## Milestone 5: Noise and Gaze

Implement:

- Noise meter;
- overflow;
- Attention Point;
- 3x3 Gaze;
- mundane form swap;
- frozen occupancy;
- global Noise-Art lock;
- Robot Vacuum Expected Behavior.

## Milestone 6: Character Kits

Implement only the five starting slice characters first.

Then add Umbrella.

## Milestone 7: Enemy AI and Boss

Implement:

- archetype priorities;
- Paper Cutter telegraph;
- recruit pressure;
- Robot Vacuum Gaze movement.

## Milestone 8: Art Pass

Replace placeholder assets with final-style 64x64 pixel sprites and room assets.

## Milestone 9: Narrative and Menus

Add:

- mission card;
- short pre-battle dialogue;
- Talk recruitment;
- post-battle results;
- short post-battle dialogue.

## Milestone 10: Playtest and Cut

Do not add new systems during this phase.

Only:

- tune;
- simplify;
- fix clarity problems;
- remove weak mechanics.

---

# 28. Scope Guardrails

The slice should not include:

- all 15 playable characters;
- full campaign progression;
- full shop economy;
- all factions;
- all paralogues;
- class systems;
- crafting;
- equipment progression;
- multiple biomes/rooms;
- large cinematic sequences;
- final campaign balancing;
- complex elevation;
- full save-slot infrastructure beyond what is needed to test the loop.

The vertical slice exists to answer whether the core game is worth expanding.

---

# 29. Definition of Done

The vertical slice is successful when a new player can:

1. understand movement without manual tile counting;
2. read threat lines while hovering destinations;
3. understand the predicted HP display;
4. recognize Smash/Pierce/Bind advantage;
5. use cover intentionally;
6. use displacement to improve a plan;
7. generate Noise with Arts;
8. intentionally manipulate Human Gaze at least once;
9. understand that Noise Arts are globally disabled during Gaze;
10. observe Robot Vacuum moving legally while watched;
11. recruit Umbrella during battle;
12. respond to Paper Cutter's telegraphed attack;
13. finish the battle in roughly 6 to 8 turns;
14. understand the results screen without explanation;
15. want to play another mission.

If those conditions are met, the project is ready to move from systems prototyping into campaign production.
