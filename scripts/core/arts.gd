class_name Arts
extends RefCounted
## Art and item definitions for the slice squad (character_abilities_stats.md).
## Signature Arts are paralogue unlocks and are not in the slice.
##
## target kinds:
##   "enemy"     pick a hostile unit (or destructible cover for attacks) in range
##   "ally"      pick a friendly unit in range (min 0 = self allowed)
##   "self"      no pick
##   "direction" pick one of four cardinal directions (cones)
##   "lunge"     pick a hostile unit in a straight line 2..4 tiles away

const DATA := {
	"guard_beam": {"name": "Guard Beam", "noise": 1, "target": "ally", "min": 1, "max": 3,
		"desc": "Next hit on the ally before your next phase deals 50% less damage and can't displace them."},
	"flashbulb": {"name": "Flashbulb", "noise": 1, "target": "direction", "might": 2, "type": Defs.DmgType.SMASH,
		"desc": "Short cone. Light Smash damage and Dazzle (-20 Hit on next attack)."},
	"pin": {"name": "Pin", "noise": 1, "target": "enemy", "min": 1, "max": 2, "might": 4, "type": Defs.DmgType.PIERCE,
		"desc": "Pierce attack. On hit, target can't move next Enemy Phase."},
	"staple_burst": {"name": "Staple Burst", "noise": 2, "target": "enemy", "min": 1, "max": 2, "might": 2, "type": Defs.DmgType.PIERCE,
		"desc": "Two reduced-Might attacks. The second picks another target if the first falls."},
	"eject": {"name": "Eject", "noise": 1, "target": "enemy", "min": 1, "max": 2, "might": 5, "type": Defs.DmgType.SMASH,
		"desc": "Smash attack. On hit, push the target 2 tiles."},
	"flash_bake": {"name": "Flash Bake", "noise": 2, "target": "direction", "might": 6, "type": Defs.DmgType.SMASH,
		"desc": "Short cone. High Smash damage to everything in it."},
	"warm_pour": {"name": "Warm Pour", "noise": 1, "target": "ally", "min": 0, "max": 3,
		"desc": "Restore 30% of the ally's max HP."},
	"steady_sip": {"name": "Steady Sip", "noise": 0, "target": "ally", "min": 0, "max": 2,
		"desc": "Remove one negative status and grant +2 Defense until your next phase."},
	"suction": {"name": "Suction", "noise": 1, "target": "enemy", "min": 2, "max": 4,
		"desc": "Pull a normal enemy up to 3 tiles toward Vacuum. Always succeeds."},
	"blowback": {"name": "Blowback", "noise": 1, "target": "direction",
		"desc": "Cone. Push everything in it 2 tiles. Always succeeds."},
	"lunge": {"name": "Lunge", "noise": 1, "target": "lunge", "might": 6, "type": Defs.DmgType.PIERCE,
		"desc": "Dash up to 3 tiles in a straight line and attack."},
	"canopy": {"name": "Canopy", "noise": 0, "target": "self",
		"desc": "Adjacent allies count as in Half Cover against ranged attacks until your next phase."},
}

const ITEMS := {
	"repair_tape": {"name": "Repair Tape", "heal_pct": 0.4, "desc": "Restore 40% of max HP. Uses the Action."},
}


static func get_art(id: String) -> Dictionary:
	return DATA[id]


static func noise_of(id: String) -> int:
	return DATA[id].noise


## Cone tiles in front of a footprint: one row the width of the user, then a row
## one tile wider on each side.
static func cone_tiles(user: Unit, anchor: Vector2i, dir: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var s := user.size
	var side := Vector2i(absi(dir.y), absi(dir.x)) # perpendicular, positive
	var front_start: Vector2i
	if dir.x > 0:
		front_start = anchor + Vector2i(s, 0)
	elif dir.x < 0:
		front_start = anchor + Vector2i(-1, 0)
	elif dir.y > 0:
		front_start = anchor + Vector2i(0, s)
	else:
		front_start = anchor + Vector2i(0, -1)
	for i in s:
		out.append(front_start + side * i)
	var second := front_start + dir
	for i in range(-1, s + 1):
		out.append(second + side * i)
	return out
