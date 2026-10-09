class_name BattleHud
extends Control

## The battle's whole interface apart from the diorama itself: the objective in
## the top-left; turn, phase, Noise meter and End Turn in the bottom-left, with a
## line of control hints; the phase banner, Art name toasts and short notices.
## The minimap sits in the bottom-right as its own child.
##
## It reads the Battle it is handed in `setup()` and reports End Turn upward.

signal end_turn_requested

@export_group("Objective")
@export var objective_label: Label
@export var stars_label: Label

@export_group("Turn Panel")
## The bottom-left panel; hidden while the battle preview has the bottom of the screen.
@export var turn_panel: Control
@export var turn_label: Label
@export var phase_label: Label
@export var noise_meter: NoiseMeter
@export var end_turn_button: Button
@export var hint_label: Label

@export_group("Announcements")
@export var banner_label: Label
@export var toast_label: Label
@export var notice_label: Label
@export var banner_hold_seconds := 0.6
@export var toast_seconds := 0.6
@export var notice_seconds := 2.2

@export_group("Minimap")
@export var minimap: Minimap

var _battle: Battle
var _objective := ""
var _notice_tween: Tween


func _ready() -> void:
	end_turn_button.pressed.connect(end_turn_requested.emit)
	banner_label.visible = false
	toast_label.visible = false
	notice_label.modulate.a = 0.0


func setup(b: Battle, objective: String) -> void:
	_battle = b
	_objective = objective
	refresh()


func refresh() -> void:
	var b := _battle
	if b == null:
		return
	objective_label.text = _objective
	var s := b.stars()
	stars_label.text = "%s Recruit Umbrella    %s %d turns or fewer    %s No one Broken" % [
		Stars.glyph(s.recruit), Stars.glyph(b.turn <= Defs.STAR_TURN_TARGET), Defs.STAR_TURN_TARGET, Stars.glyph(not b.any_broken)]
	turn_label.text = "Turn %d" % b.turn
	var phase := "Player Phase" if b.phase == Defs.Phase.PLAYER else ("Enemy Phase" if b.phase == Defs.Phase.ENEMY else "")
	phase_label.text = phase + ("  ·  HUMAN GAZE" if b.gaze_active() else "")
	phase_label.add_theme_color_override("font_color", Color("d8c8ff") if b.gaze_active() else Color("cfc8d8"))
	noise_meter.show_noise(b.noise, b.gaze_active())


func set_hint(text: String) -> void:
	hint_label.text = text


## The battle preview takes the bottom of the screen while a target is picked;
## the turn panel, hint line and minimap step aside for it.
func set_bottom_visible(on: bool) -> void:
	turn_panel.visible = on
	hint_label.visible = on
	minimap.visible = on


func set_end_turn_enabled(on: bool) -> void:
	end_turn_button.disabled = not on


func banner(s: String) -> void:
	banner_label.text = s
	banner_label.visible = true
	banner_label.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(banner_label, "modulate:a", 1.0, 0.15)
	tw.tween_interval(banner_hold_seconds)
	tw.tween_property(banner_label, "modulate:a", 0.0, 0.2)
	await tw.finished
	banner_label.visible = false


func toast(s: String) -> void:
	toast_label.text = s
	toast_label.visible = true
	await get_tree().create_timer(toast_seconds, false).timeout
	toast_label.visible = false


## A short line of news ("Cover destroyed", "Lamp intercepts the hit").
func notify(s: String) -> void:
	notice_label.text = s
	if _notice_tween != null:
		_notice_tween.kill()
	notice_label.modulate.a = 1.0
	_notice_tween = create_tween()
	_notice_tween.tween_interval(notice_seconds)
	_notice_tween.tween_property(notice_label, "modulate:a", 0.0, 0.4)


func pulse_end_turn() -> void:
	var tw := create_tween()
	tw.tween_property(end_turn_button, "modulate", Color(1.4, 1.4, 0.8), 0.25)
	tw.tween_property(end_turn_button, "modulate", Color.WHITE, 0.25)
