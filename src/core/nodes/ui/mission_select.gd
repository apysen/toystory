class_name MissionSelect
extends Control

## The mission card: title, setup, objective and the optional stars, with the best
## result this session. Reports the player's choice; `AppRoot` decides what follows.

signal mission_chosen
signal quit_requested

@export var title_label: Label
@export var blurb_label: Label
@export var objective_label: Label
@export var optional_label: Label
@export var select_button: Button
@export var quit_button: Button

@export var not_cleared_text := "Not cleared yet"


func _ready() -> void:
	select_button.pressed.connect(mission_chosen.emit)
	quit_button.pressed.connect(quit_requested.emit)


## `best` is the best star result this session, or empty if never cleared.
func show_mission(mission: MissionDefinition, best: Dictionary) -> void:
	title_label.text = mission.title
	blurb_label.text = mission.blurb
	objective_label.text = "Objective: %s." % mission.objective_text
	var record := not_cleared_text if best.is_empty() else "Best: %s" % Stars.text(best)
	optional_label.text = "Optional: %s.   %s" % ["  /  ".join(mission.optional_objectives), record]
