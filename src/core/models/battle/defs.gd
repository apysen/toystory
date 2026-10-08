class_name Defs
extends RefCounted
## Shared enums and tunable prototype values (gameplay_design.md section 31).

enum Faction { PLAYER, ENEMY, NEUTRAL }
enum DmgType { SMASH, PIERCE, BIND, NEUTRAL }
enum Terrain { FLOOR, FULL_COVER, HALF_COVER, SPILL }
enum Phase { PLAYER, ENEMY, VICTORY, DEFEAT }

const TILE_SIZE := 128
const SPRITE_SIZE := 128

const NOISE_THRESHOLD := 6
const GAZE_RADIUS := 1 # 3x3
const TYPE_HIT_BONUS := 15
const TYPE_DMG_BONUS := 0.20
const HALF_COVER_EVASION := 25
const WEATHERPROOF_EVASION := 15
const CRIT_MULT := 2
const COLLISION_PCT := 0.10
const BASE_ACCURACY := 85
const SPILL_EXTRA_COST := 2
const STAR_TURN_TARGET := 7

const TYPE_NAMES := {
	DmgType.SMASH: "Smash",
	DmgType.PIERCE: "Pierce",
	DmgType.BIND: "Bind",
	DmgType.NEUTRAL: "Neutral",
}

const DIRS: Array[Vector2i] = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]


## +1 advantage, -1 disadvantage, 0 neutral. Smash > Pierce > Bind > Smash.
static func type_relation(attacker: int, defender: int) -> int:
	if attacker == DmgType.NEUTRAL or defender == DmgType.NEUTRAL:
		return 0
	if attacker == defender:
		return 0
	var beats := {DmgType.SMASH: DmgType.PIERCE, DmgType.PIERCE: DmgType.BIND, DmgType.BIND: DmgType.SMASH}
	return 1 if beats[attacker] == defender else -1


static func manhattan(a: Vector2i, b: Vector2i) -> int:
	return absi(a.x - b.x) + absi(a.y - b.y)
