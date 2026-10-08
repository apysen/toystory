class_name BattleSelection
extends RefCounted

## What the player is pointing at and choosing right now: the interface state of
## one battle, separate from the battle rules.
##
## `BattleRoot` is the only writer. `BoardView` and `BattleHud` are handed the same
## instance through their `setup()` and only read it, so the board's highlights and
## the side panel can never disagree about what is selected.

enum Mode { IDLE, SELECTED, MENU, TARGET, BUSY, DONE }

const NONE := Vector2i(-99, -99)

var mode := Mode.IDLE
var selected: Unit = null
var hover := NONE
## "attack", "art:<id>" or "talk" while picking a target.
var target_kind := ""
## Units, cover tiles, or cone directions the current action may pick.
var target_options: Array = []
var hover_target: Variant = null
## Anchor tiles the selected unit can move to: tile -> true.
var move_set := {}
## Movement forecast for the hovered destination (see `Forecast.for_destination`).
var forecast := {}
## Enemy whose reach is shown after clicking it.
var inspected_enemy: Unit = null


func clear_action() -> void:
	selected = null
	forecast = {}
	target_options = []
	hover_target = null


## Whether the player may end the phase now.
func can_end_turn() -> bool:
	return mode == Mode.IDLE or mode == Mode.SELECTED


## The current action is an Art whose target kind is `kind` ("direction", "ally", ...).
func is_art_kind(kind: String) -> bool:
	if not target_kind.begins_with("art:"):
		return false
	return Arts.get_art(target_kind.substr(4)).target == kind


## The unit the side panel describes: the selection, else the hovered unit, else
## the inspected enemy.
func focus_unit(board: Board) -> Unit:
	if selected != null:
		return selected
	if hover != NONE:
		var u := board.unit_at(hover)
		if u != null:
			return u
	return inspected_enemy
