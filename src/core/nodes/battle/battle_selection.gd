class_name BattleSelection
extends RefCounted

## What the player is doing right now: the interface state of one battle,
## separate from the battle rules. BattleRoot is the only writer; the overlays and
## HUD read it.

## IDLE: free camera, nobody controlled. CONTROL: steering a unit inside its
## movement area. MENU: the action ring is open. TARGET: picking a target or
## aiming, with the battle preview showing. BUSY: playback. DONE: battle over.
enum Mode { IDLE, CONTROL, MENU, TARGET, BUSY, DONE }

var mode := Mode.IDLE
var controlled: Unit = null
## "attack", "art:<id>" or "talk" while picking a target.
var action := ""
## Units, cover ids, suggested centres (areas), or (for cones) nothing: cones aim with `aim`.
var targets: Array = []
var target_index := 0
## Aim direction for cones, on the floor.
var aim := Vector2.RIGHT
## Centre of an area Art's circle, on the floor (follows the mouse; ◀ ▶ step it
## through `targets`).
var spot := Vector2.ZERO
## Movement forecast for the controlled unit where it stands.
var forecast := {}
## Enemy whose reach is shown after clicking it.
var inspected_enemy: Unit = null
## Index the action ring last showed, per unit id, so reopening keeps your place.
var ring_memory := {}


func current_target() -> Variant:
	if targets.is_empty():
		return null
	return targets[clampi(target_index, 0, targets.size() - 1)]


func is_aiming() -> bool:
	return action.begins_with("art:") and Arts.get_art(action.substr(4)).target == "direction"


func is_placing() -> bool:
	return action.begins_with("art:") and Arts.get_art(action.substr(4)).target == "area"


## A self-centred area Art (Staple Storm): its circle round the user is shown, then confirmed.
func is_self_area() -> bool:
	if not action.begins_with("art:"):
		return false
	var art := Arts.get_art(action.substr(4))
	return art.target == "self" and art.has("radius")


func is_friendly_action() -> bool:
	if action == "talk":
		return true
	return action.begins_with("art:") and Arts.get_art(action.substr(4)).target in ["ally", "area"]


func clear_action() -> void:
	action = ""
	targets = []
	target_index = 0
