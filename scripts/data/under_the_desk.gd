class_name UnderTheDesk
extends RefCounted
## "Under the Desk" map and roster (vertical_slice_plan.md sections 5-11).
## Player stats: character_abilities_stats.md section 3 (level 5 benchmark).
## Enemy stats are Claude's proposal; the design docs don't define them yet.

const MAP_W := 15
const MAP_H := 11

const FULL_COVER := {
	Vector2i(6, 3): "desk_leg",
	Vector2i(6, 8): "desk_leg",
	Vector2i(10, 5): "chair_leg",
	Vector2i(13, 8): "cabinet",
	Vector2i(14, 8): "cabinet",
	Vector2i(13, 9): "cabinet",
	Vector2i(14, 9): "cabinet",
}

## kind -> hp (0 = durable)
const HALF_COVER := {
	Vector2i(5, 5): ["books", 0],
	Vector2i(8, 3): ["books", 0],
	Vector2i(8, 7): ["box", 12],
	Vector2i(11, 8): ["books", 0],
	Vector2i(12, 4): ["small_box", 8],
	# Paper Guard: the plan says the Captain starts near destructible cardboard,
	# but its cover list has none near (13,10). This box fills that gap.
	Vector2i(12, 10): ["box", 12],
}

const SPILL: Array[Vector2i] = [Vector2i(9, 6), Vector2i(10, 6), Vector2i(11, 6), Vector2i(10, 7)]

const P := Defs.Faction.PLAYER
const E := Defs.Faction.ENEMY
const N := Defs.Faction.NEUTRAL
const SMASH := Defs.DmgType.SMASH
const PIERCE := Defs.DmgType.PIERCE
const BIND := Defs.DmgType.BIND

static func unit_defs() -> Array:
	return [
		{"id": "lamp", "name": "Lamp", "faction": P, "type": SMASH, "pos": Vector2i(3, 2),
			"hp": 30, "pow": 8, "def": 8, "skl": 7, "spd": 6, "mov": 5, "might": 4, "range": 1,
			"arts": ["guard_beam", "flashbulb"], "item": "repair_tape"},
		{"id": "stapler", "name": "Stapler", "faction": P, "type": PIERCE, "pos": Vector2i(4, 2),
			"hp": 25, "pow": 8, "def": 4, "skl": 10, "spd": 10, "mov": 6, "might": 4, "range": 2,
			"arts": ["pin", "staple_burst"], "item": "repair_tape"},
		{"id": "toaster", "name": "Toaster", "faction": P, "type": SMASH, "pos": Vector2i(3, 3),
			"hp": 28, "pow": 10, "def": 5, "skl": 7, "spd": 6, "mov": 5, "might": 5, "range": 2,
			"arts": ["eject", "flash_bake"], "item": "repair_tape"},
		{"id": "teacup", "name": "Teacup", "faction": P, "type": BIND, "pos": Vector2i(4, 3),
			"hp": 26, "pow": 6, "def": 5, "skl": 9, "spd": 7, "mov": 5, "might": 3, "range": 2,
			"arts": ["warm_pour", "steady_sip"], "item": "repair_tape"},
		{"id": "vacuum", "name": "Vacuum", "sprite": "vacuum_256", "faction": P, "type": BIND, "pos": Vector2i(1, 2), "size": 2,
			"hp": 42, "pow": 10, "def": 9, "skl": 6, "spd": 3, "mov": 4, "might": 4, "range": 3,
			"arts": ["suction", "blowback"], "item": "repair_tape", "forced_move_reduction": 1},
		{"id": "umbrella", "name": "Umbrella", "faction": N, "type": PIERCE, "pos": Vector2i(13, 4),
			"hp": 29, "pow": 8, "def": 6, "skl": 8, "spd": 8, "mov": 6, "might": 4, "range": 1,
			"arts": ["lunge", "canopy"], "item": "repair_tape", "recruiter": "lamp"},

		{"id": "pencil_a", "name": "Pencil Lancer", "sprite": "pencil", "faction": E, "type": PIERCE,
			"pos": Vector2i(7, 3), "hp": 18, "pow": 7, "def": 3, "skl": 8, "spd": 8, "mov": 5,
			"might": 4, "range": 1, "ai": "pencil"},
		{"id": "rubber", "name": "Rubber Band Snarer", "sprite": "rubber", "faction": E, "type": BIND,
			"pos": Vector2i(7, 6), "hp": 18, "pow": 6, "def": 3, "skl": 7, "spd": 7, "mov": 4,
			"might": 3, "range": 2, "ai": "snarer"},
		{"id": "bookend", "name": "Bookend Guard", "sprite": "bookend", "faction": E, "type": SMASH,
			"pos": Vector2i(9, 4), "hp": 26, "pow": 7, "def": 7, "skl": 5, "spd": 3, "mov": 3,
			"might": 4, "range": 1, "ai": "guard", "forced_move_reduction": 1},
		{"id": "pencil_b", "name": "Pencil Lancer", "sprite": "pencil", "faction": E, "type": PIERCE,
			"pos": Vector2i(11, 3), "hp": 18, "pow": 7, "def": 3, "skl": 8, "spd": 8, "mov": 5,
			"might": 4, "range": 1, "ai": "pencil"},
		{"id": "tape", "name": "Tape Dispenser", "sprite": "tape", "faction": E, "type": BIND,
			"pos": Vector2i(11, 7), "hp": 20, "pow": 6, "def": 4, "skl": 6, "spd": 5, "mov": 4,
			"might": 3, "range": 2, "ai": "tape"},
		{"id": "roomba", "name": "Robot Vacuum", "sprite": "roomba", "faction": E, "type": BIND,
			"pos": Vector2i(12, 9), "hp": 20, "pow": 6, "def": 5, "skl": 5, "spd": 6, "mov": 5,
			"might": 3, "range": 1, "ai": "roomba", "expected_behavior": true},
		{"id": "cutter", "name": "Paper Cutter Captain", "sprite": "cutter", "faction": E, "type": PIERCE,
			"pos": Vector2i(13, 10), "hp": 34, "pow": 9, "def": 6, "skl": 9, "spd": 6, "mov": 3,
			"might": 5, "range": 1, "ai": "captain", "forced_move_reduction": 1},
	]


static func build_board() -> Board:
	var b := Board.new(MAP_W, MAP_H)
	for t in FULL_COVER:
		b.add_object(t, FULL_COVER[t], Defs.Terrain.FULL_COVER)
	for t in HALF_COVER:
		b.add_object(t, HALF_COVER[t][0], Defs.Terrain.HALF_COVER, HALF_COVER[t][1])
	for t in SPILL:
		b.slow_tiles[t] = "spill"
	for def in unit_defs():
		b.units.append(Unit.from_def(def))
	return b
