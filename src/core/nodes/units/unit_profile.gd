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
## Bottom-left tile of the unit's footprint on the mission's 1 m layout grid.
@export var start_tile := Vector2i.ONE

@export_group("Stats")
@export var max_hp := 20
@export var power := 5
@export var defense := 5
@export var skill := 5
@export var speed := 5
## Metres of path per activation.
@export var move := 5.0
@export var might := 3
## Basic Attack reach: the edge-to-edge gap in metres (0.6 is melee).
@export var attack_range := 0.6
@export var min_range := 0.0

@export_group("Kit")
## Art ids from `Arts.DATA`.
@export var arts := PackedStringArray()
## Item id from `Arts.ITEMS`; empty for none.
@export var item := ""
## Enemy AI archetype id read by `EnemyAI`; empty for player units.
@export var ai := ""
## Heavy Frame / Heavy Chassis: metres taken off any push or pull against this unit.
@export var forced_move_reduction := 0.0
## Robot Vacuum: keeps moving while watched by a human, but can't attack.
@export var expected_behavior := false
## For a neutral unit: the id of the player unit that can Talk to recruit it.
@export var recruiter := ""

@export_group("Dev")
## Dev testing: a neutral that starts the battle already in the player's squad (no
## recruiting), standing at `dev_squad_tile`. Off for the real slice.
@export var dev_in_squad := false
@export var dev_squad_tile := Vector2i.ONE


## The plain definition `Unit.from_def` reads.
func to_def() -> Dictionary:
	return {
		"id": unit_id, "name": display_name, "sprite": sprite if sprite != "" else unit_id,
		"faction": Defs.Faction.PLAYER if dev_in_squad else faction, "type": damage_type, "size": footprint,
		"start_tile": dev_squad_tile if dev_in_squad else start_tile,
		"hp": max_hp, "pow": power, "def": defense, "skl": skill, "spd": speed, "mov": move,
		"might": might, "range": attack_range, "min_range": min_range,
		"arts": Array(arts), "item": item, "ai": ai, "forced_move_reduction": forced_move_reduction,
		"expected_behavior": expected_behavior, "recruiter": "" if dev_in_squad else recruiter,
	}
