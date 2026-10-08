class_name Unit
extends RefCounted
## One battlefield unit. `pos` is the bottom-left tile of its footprint, in map
## coordinates where (1,1) is the bottom-left tile (vertical_slice_plan.md section 5).

var id: String
var name: String
var sprite: String # folder name under assets/sprites
var faction: int
var dmg_type: int
var size := 1 # 1 = Normal, 2 = Large (2x2)
var max_hp: int
var hp: int
var power: int
var defense: int
var skill: int
var speed: int
var move: int
var might: int
var attack_range := 1
var min_range := 1
var arts: Array = [] # Array of art ids (see Arts)
var item := "" # consumable item id, "" once used
var ai := "" # enemy AI archetype id
var forced_move_reduction := 0 # Heavy Frame / Heavy Chassis
var expected_behavior := false # Robot Vacuum: may move while watched
var recruiter := "" # unit id that may Talk to recruit this neutral

var pos := Vector2i.ZERO
var moved := false
var acted := false
var frozen := false # transformed by Human Gaze
var broken := false
var pending_join := false # recruited, becomes controllable next Player Phase
var status := {} # name -> value, see Battle for meanings
var displaced_this_phase := false
var move_path_len := 0 # tiles moved in a straight approach this activation


static func from_def(def: Dictionary) -> Unit:
	var u := Unit.new()
	u.id = def.id
	u.name = def.name
	u.sprite = def.get("sprite", def.id)
	u.faction = def.faction
	u.dmg_type = def.type
	u.size = def.get("size", 1)
	u.max_hp = def.hp
	u.hp = def.hp
	u.power = def.pow
	u.defense = def.def
	u.skill = def.skl
	u.speed = def.spd
	u.move = def.mov
	u.might = def.might
	u.attack_range = def.range
	u.min_range = def.get("min_range", 1)
	u.arts = def.get("arts", [])
	u.item = def.get("item", "")
	u.ai = def.get("ai", "")
	u.forced_move_reduction = def.get("forced_move_reduction", 0)
	u.expected_behavior = def.get("expected_behavior", false)
	u.recruiter = def.get("recruiter", "")
	u.pos = def.pos
	return u


func tiles_at(anchor: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for dx in size:
		for dy in size:
			out.append(anchor + Vector2i(dx, dy))
	return out


func tiles() -> Array[Vector2i]:
	return tiles_at(pos)


func occupies(t: Vector2i) -> bool:
	return t.x >= pos.x and t.x < pos.x + size and t.y >= pos.y and t.y < pos.y + size


## Smallest Manhattan distance from this unit's footprint (placed at `anchor`) to `t`.
func distance_from(anchor: Vector2i, t: Vector2i) -> int:
	var best := 1 << 30
	for p in tiles_at(anchor):
		best = mini(best, Defs.manhattan(p, t))
	return best


## Smallest distance between two footprints.
func distance_to_unit(anchor: Vector2i, other: Unit, other_anchor: Vector2i) -> int:
	var best := 1 << 30
	for p in tiles_at(anchor):
		for q in other.tiles_at(other_anchor):
			best = mini(best, Defs.manhattan(p, q))
	return best


func center_tile() -> Vector2i:
	return pos


func is_alive() -> bool:
	return not broken


func is_hostile_to(other: Unit) -> bool:
	if faction == other.faction:
		return false
	# Neutral recruits are attacked by enemies but never by the player.
	if faction == Defs.Faction.PLAYER and other.faction == Defs.Faction.NEUTRAL:
		return false
	if faction == Defs.Faction.NEUTRAL and other.faction == Defs.Faction.PLAYER:
		return false
	return true


func can_activate() -> bool:
	return faction == Defs.Faction.PLAYER and not broken and not frozen and not acted and not pending_join


func is_large() -> bool:
	return size > 1
