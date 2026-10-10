class_name Defs
extends RefCounted
## Shared enums and tunable prototype values (gameplay_design.md section 31).
## Distances are metres on the floor; the "Under the Desk" layout is authored on a
## 1 m grid, so one old tile is one metre.

enum Faction { PLAYER, ENEMY, NEUTRAL }
enum DmgType { SMASH, PIERCE, BIND, NEUTRAL }
enum Cover { NONE, HALF, FULL }
enum Phase { PLAYER, ENEMY, VICTORY, DEFEAT }

const NOISE_THRESHOLD := 6
## Human Gaze watches a circle this wide around the Attention Point (the old 3x3).
const GAZE_RADIUS := 1.6
const TYPE_HIT_BONUS := 15
const TYPE_DMG_BONUS := 0.20
const HALF_COVER_EVASION := 25
const WEATHERPROOF_EVASION := 15
## Lamp's Spotlight: Evasion for allies standing in its light.
const SPOTLIGHT_EVASION := 20
## Toaster's Overheat: the share of his max HP it burns off him (never Breaks him).
const OVERHEAT_SELF_PCT := 0.2
const CRIT_MULT := 2
const COLLISION_PCT := 0.10
const BASE_ACCURACY := 85
const STAR_TURN_TARGET := 7

## Body radius of a Normal and a Large unit.
const UNIT_RADIUS := 0.3
const LARGE_RADIUS := 0.75
## Edge-to-edge gap that still counts as melee (no cover, Weatherproof doesn't apply).
const MELEE_REACH := 0.6
## Edge-to-edge gap that counts as "next to" for Talk, Watchful, Canopy and Comforting Presence.
const ADJACENT_GAP := 0.7
## Spill and sticky tape multiply the cost of moving through them.
const SLOW_COST_MULT := 3.0
## Radius of the sticky patch Tape Lash leaves.
const TAPE_RADIUS := 0.55
## Half cover protects a defender when it sits this close to them, between them and the shot.
const COVER_REACH := 1.2
## Pushed and pulled units stop this far short of whatever they hit.
const CONTACT_GAP := 0.05

const TYPE_NAMES := {
	DmgType.SMASH: "Smash",
	DmgType.PIERCE: "Pierce",
	DmgType.BIND: "Bind",
	DmgType.NEUTRAL: "Neutral",
}


## +1 advantage, -1 disadvantage, 0 neutral. Smash > Pierce > Bind > Smash.
static func type_relation(attacker: int, defender: int) -> int:
	if attacker == DmgType.NEUTRAL or defender == DmgType.NEUTRAL:
		return 0
	if attacker == defender:
		return 0
	var beats := {DmgType.SMASH: DmgType.PIERCE, DmgType.PIERCE: DmgType.BIND, DmgType.BIND: DmgType.SMASH}
	return 1 if beats[attacker] == defender else -1
