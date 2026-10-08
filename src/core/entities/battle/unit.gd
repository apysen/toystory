class_name Unit
extends RefCounted
## One battlefield unit: a circle on the floor. `pos` is the centre of its body in
## metres, with (0, 0) at the bottom-left corner of the map (vertical_slice_plan.md
## section 5).

var id: String
var name: String
var sprite: String # folder name under assets/sprites
var faction: int
var dmg_type: int
var size := 1 # 1 = Normal, 2 = Large
var radius := Defs.UNIT_RADIUS
var max_hp: int
var hp: int
var power: int
var defense: int
var skill: int
var speed: int
## Metres of path the unit may cover in one activation.
var move: float
var might: int
## Basic Attack reach: the edge-to-edge gap, in metres.
var attack_range := 0.6
var min_range := 0.0
var arts: Array = [] # Array of art ids (see Arts)
var item := "" # consumable item id, "" once used
var ai := "" # enemy AI archetype id
var forced_move_reduction := 0.0 # Heavy Frame / Heavy Chassis, metres
var expected_behavior := false # Robot Vacuum: may move while watched
var recruiter := "" # unit id that may Talk to recruit this neutral

var pos := Vector2.ZERO
## Where the unit stood when its activation began. Its movement area is measured
## from here, so it can wander, undo, or be left and come back to.
var turn_start := Vector2.ZERO
var acted := false
var frozen := false # transformed by Human Gaze
var broken := false
var pending_join := false # recruited, becomes controllable next Player Phase
var status := {} # name -> value, see Battle for meanings
var displaced_this_phase := false
var facing := 1 # 1 = right, -1 = left; follows the last horizontal move
## Path length covered this activation (Pencil Lancer's Charge).
var moved_distance := 0.0


static func from_def(def: Dictionary, start: Vector2) -> Unit:
	var u := Unit.new()
	u.id = def.id
	u.name = def.name
	u.sprite = def.get("sprite", def.id)
	u.faction = def.faction
	u.dmg_type = def.type
	u.size = def.get("size", 1)
	u.radius = Defs.LARGE_RADIUS if u.size > 1 else Defs.UNIT_RADIUS
	u.max_hp = def.hp
	u.hp = def.hp
	u.power = def.pow
	u.defense = def.def
	u.skill = def.skl
	u.speed = def.spd
	u.move = def.mov
	u.might = def.might
	u.attack_range = def.range
	u.min_range = def.get("min_range", 0.0)
	u.arts = def.get("arts", [])
	u.item = def.get("item", "")
	u.ai = def.get("ai", "")
	u.forced_move_reduction = def.get("forced_move_reduction", 0.0)
	u.expected_behavior = def.get("expected_behavior", false)
	u.recruiter = def.get("recruiter", "")
	u.pos = start
	u.turn_start = start
	u.facing = -1 if u.faction == Defs.Faction.ENEMY else 1
	return u


## Faces the direction of the last horizontal move along `path`; unchanged if none.
func face_along(path: Array) -> void:
	for i in range(path.size() - 1, 0, -1):
		var dx: float = path[i].x - path[i - 1].x
		if absf(dx) > 0.01:
			facing = 1 if dx > 0 else -1
			return


## Edge-to-edge gap to another unit, with either one optionally placed elsewhere.
func gap_to(other: Unit, at := Vector2.INF, other_at := Vector2.INF) -> float:
	var a := pos if at == Vector2.INF else at
	var b := other.pos if other_at == Vector2.INF else other_at
	return Geometry.gap(a, radius, b, other.radius)


func is_adjacent(other: Unit) -> bool:
	return gap_to(other) <= Defs.ADJACENT_GAP


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
