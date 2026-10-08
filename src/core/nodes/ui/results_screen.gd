class_name ResultsScreen
extends Control

## Post-battle results: outcome, turns, the three stars, who was Broken, and the
## playtest numbers. Reports retry or return.

signal retry_requested
signal return_requested

@export var heading_label: Label
@export var turns_label: Label
@export var recruit_label: Label
@export var turn_star_label: Label
@export var unbroken_label: Label
@export var broken_label: Label
@export var stats_label: Label
@export var metrics_label: Label
@export var retry_button: Button
@export var return_button: Button


func _ready() -> void:
	retry_button.pressed.connect(retry_requested.emit)
	return_button.pressed.connect(return_requested.emit)


func show_result(result: Dictionary) -> void:
	heading_label.text = "Victory" if result.victory else "Defeat"
	var s: Dictionary = result.stars
	turns_label.text = "Turns: %d" % result.turns
	recruit_label.text = "%s  Recruit Umbrella" % Stars.glyph(s.recruit)
	turn_star_label.text = "%s  Finish in %d turns or fewer" % [Stars.glyph(s.turns), Defs.STAR_TURN_TARGET]
	unbroken_label.text = "%s  No one Broken" % Stars.glyph(s.unbroken)
	broken_label.visible = not result.broken.is_empty()
	broken_label.text = "Broken: %s" % ", ".join(result.broken)
	var st: Dictionary = result.stats
	stats_label.text = "Arts used: %d   Human Gaze triggered: %d   Enemies caught in Gaze: %d   Allies caught: %d" % [
		st.arts_used, st.gaze_triggers, st.enemies_caught, st.allies_caught]
	var m: Dictionary = result.metrics
	metrics_label.text = "Battle time %d:%02d   Avg predicted HP error %.1f   Threat inspections %d   (saved to the playtests folder)" % [
		int(m.duration_s) / 60, int(m.duration_s) % 60, m.avg_predicted_hp_error, m.threat_inspections]
