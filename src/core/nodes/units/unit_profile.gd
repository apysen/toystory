class_name UnitProfile
extends Node

## One combatant in the mission roster: identity, deployment, stats and kit.
##
## Player stats follow character_abilities_stats.md section 3 (level 5 benchmark).
## Enemy stats are a proposal; the design docs only give types and traits. A profile
## is copied into a `Unit` when a battle starts, so editing one in the Inspector
## changes the next battle and never a battle already running.

@export_group("Identity")
## Stable id the rules, art and dialogue refer to ("lamp", "pencil_a").
@export var unit_id := ""
@export var display_name := ""
## Folder under assets/sprites/<group>/. Empty uses `unit_id`.
@export var sprite := ""
@export var faction := Defs.Faction.PLAYER
@export var damage_type := Defs.DmgType.SMASH
## 1 = Normal (1x1), 2 = Large (2x2).
@export_range(1, 2) var footprint := 1

@export_group("Deployment")
## Bottom-left tile of the unit's footprint when the battle starts.
@export var start_tile := Vector2i.ONE

@export_group("Stats")
@export var max_hp := 20
@export var power := 5
@export var defense := 5
@export var skill := 5
@export var speed := 5
@export var move := 5
@export var might := 3
@export var attack_range := 1
@export var min_range := 1

@export_group("Kit")
## Art ids from `Arts.DATA`.
@export var arts := PackedStringArray()
## Item id from `Arts.ITEMS`; empty for none.
@export var item := ""
## Enemy AI archetype id read by `EnemyAI`; empty for player units.
@export var ai := ""
## Heavy Frame / Heavy Chassis: forced movement against this unit is reduced by this much.
@export var forced_move_reduction := 0
## Robot Vacuum: keeps moving while watched by a human, but can't attack.
@export var expected_behavior := false
## For a neutral unit: the id of the player unit that can Talk to recruit it.
@export var recruiter := ""


## The plain definition `Unit.from_def` reads.
func to_def() -> Dictionary:
	return {
		"id": unit_id, "name": display_name, "sprite": sprite if sprite != "" else unit_id,
		"faction": faction, "type": damage_type, "size": footprint, "pos": start_tile,
		"hp": max_hp, "pow": power, "def": defense, "skl": skill, "spd": speed, "mov": move,
		"might": might, "range": attack_range, "min_range": min_range,
		"arts": Array(arts), "item": item, "ai": ai, "forced_move_reduction": forced_move_reduction,
		"expected_behavior": expected_behavior, "recruiter": recruiter,
	}
