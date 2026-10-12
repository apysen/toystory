class_name BattleHud
extends Control

## The battle's whole interface apart from the diorama itself: the objective in
## the top-left; turn, phase, Noise meter and End Turn in the bottom-left (the type
## triangle over them while a unit is controlled), with a
## line of control hints; the phase banner, Art name toasts and short notices; and
## the letterbox and name card a signature Art plays under. The minimap sits in the
## bottom-right as its own child.
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

@export_group("Type Triangle")
## Smash > Pierce > Bind > Smash, shown while a unit is controlled.
@export var type_triangle: TypeTriangle

@export_group("Signature Arts")
@export var letterbox_top: ColorRect
@export var letterbox_bottom: ColorRect
@export var signature_card: Control
@export var signature_name: Label
@export var signature_who: Label
## Height of the letterbox bars, and the seconds they take to slide in.
@export var letterbox_height := 96.0
@export var letterbox_seconds := 0.3

var _battle: Battle
var _objective := ""
var _notice_tween: Tween
var _letterbox_tween: Tween
var _type := -1
var _signature_on := false


func _ready() -> void:
	end_turn_button.pressed.connect(end_turn_requested.emit)
	banner_label.visible = false
	toast_label.visible = false
	notice_label.modulate.a = 0.0
	letterbox_top.offset_bottom = 0.0
	letterbox_bottom.offset_top = 0.0
	signature_card.position.x = -900.0
	signature_card.modulate.a = 0.0


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
	type_triangle.visible = on and _type >= 0


## Lights the controlled unit's type on the triangle; -1 hides it.
func show_type(t: int) -> void:
	_type = t
	type_triangle.show_type(t)


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
	if _signature_on:
		return # the name card already says it
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


## A signature Art: letterbox bars slide in, the rest of the interface steps
## aside, and the Art's name slides in on the bottom bar under who uses it.
func signature_in(art_name: String, who: String) -> void:
	_signature_on = true
	signature_name.text = art_name
	signature_who.text = who
	_letterbox(true)


## Back to the battle once the signature Art's playback is over.
func signature_out() -> void:
	if not _signature_on:
		return
	_signature_on = false
	_letterbox(false)


func _letterbox(on: bool) -> void:
	if _letterbox_tween != null:
		_letterbox_tween.kill()
	var h := letterbox_height if on else 0.0
	letterbox_top.visible = true
	letterbox_bottom.visible = true
	signature_card.visible = true
	for n in [turn_panel, hint_label, minimap, objective_label.get_parent().get_parent()]:
		(n as CanvasItem).visible = not on
	type_triangle.visible = not on and _type >= 0
	_letterbox_tween = create_tween().set_parallel()
	_letterbox_tween.tween_property(letterbox_top, "offset_bottom", h, letterbox_seconds).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_letterbox_tween.tween_property(letterbox_bottom, "offset_top", -h, letterbox_seconds).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	var x := 64.0 if on else -900.0
	_letterbox_tween.tween_property(signature_card, "position:x", x, letterbox_seconds + 0.15).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT if on else Tween.EASE_IN).set_delay(0.12 if on else 0.0)
	_letterbox_tween.tween_property(signature_card, "modulate:a", 1.0 if on else 0.0, 0.2).set_delay(0.12 if on else 0.0)
	if not on:
		_letterbox_tween.chain().tween_callback(func() -> void:
			letterbox_top.visible = false
			letterbox_bottom.visible = false
			signature_card.visible = false)


func pulse_end_turn() -> void:
	var tw := create_tween()
	tw.tween_property(end_turn_button, "modulate", Color(1.4, 1.4, 0.8), 0.25)
	tw.tween_property(end_turn_button, "modulate", Color.WHITE, 0.25)
