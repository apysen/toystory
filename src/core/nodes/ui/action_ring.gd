class_name ActionRing
extends Control

## The action ring (Paper Mario: The Thousand-Year Door style): every action the
## controlled unit can take, on a ring that floats above it. The action at the
## front is the one chosen; its description sits in a box above the ring. The
## arrows either side, left/right, the D-pad or the stick turn the ring one action.
##
## It reports the choice; BattleRoot decides what happens.

signal chosen(action_id: String)
signal cancelled
signal hovered(action_id: String)

const ICON_DIR := "res://assets/sprites/ui/actions/"

@export var left_button: Button
@export var right_button: Button
@export var info_panel: Control
@export var title_label: Label
@export var desc_label: Label
@export var cost_label: Label

@export_group("Shape")
@export var radius_x := 118.0
@export var radius_y := 30.0
@export var icon_size := 64.0
## Smallest scale an icon shrinks to at the back of the ring.
@export var back_scale := 0.55
@export var turn_seconds := 0.16
## Pixels above the unit's head the ring's centre sits.
@export var lift := 70.0

var _actions: Array = []
var _index := 0
var _angle := 0.0
var _anchor: Node3D
var _anchor_height := 1.0
var _icons := {}
var _tween: Tween


func _ready() -> void:
	visible = false
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Left brings the action on the left round to the front, and right the one on the right.
	left_button.pressed.connect(turn.bind(1))
	right_button.pressed.connect(turn.bind(-1))


## Opens over `anchor` (the unit's card). Actions: [{id, label, enabled, tooltip, icon, noise}].
func open(anchor: Node3D, anchor_height: float, actions: Array, start := 0) -> void:
	_anchor = anchor
	_anchor_height = anchor_height
	_actions = actions
	_index = clampi(start, 0, actions.size() - 1)
	_angle = _target_angle()
	for a in actions:
		if not _icons.has(a.icon):
			var path: String = ICON_DIR + a.icon + ".png"
			_icons[a.icon] = load(path) if ResourceLoader.exists(path) else null
	visible = true
	_show_info()
	_place()
	hovered.emit(current().id)


func close() -> void:
	visible = false


func is_open() -> bool:
	return visible


func current() -> Dictionary:
	return _actions[_index] if not _actions.is_empty() else {}


## Turns the ring one action left (-1) or right (+1).
func turn(step: int) -> void:
	if _actions.is_empty():
		return
	_index = posmod(_index + step, _actions.size())
	var target := _target_angle()
	# Turn the short way round.
	while target - _angle > PI:
		target -= TAU
	while target - _angle < -PI:
		target += TAU
	if _tween != null:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(self, "_angle", target, turn_seconds).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_show_info()
	hovered.emit(current().id)


func choose() -> void:
	var a := current()
	if a.is_empty():
		return
	if not a.enabled:
		_shake()
		return
	chosen.emit(a.id)


func _target_angle() -> float:
	return -TAU * _index / maxf(_actions.size(), 1.0)


func _process(_delta: float) -> void:
	if visible:
		_place()
		queue_redraw()


func _place() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null or _anchor == null:
		return
	var head := _anchor.global_position + Vector3(0, _anchor_height, 0)
	var c := cam.unproject_position(head) - Vector2(0, lift)
	left_button.position = c + Vector2(-radius_x - icon_size * 0.5 - left_button.size.x - 6, -left_button.size.y * 0.5 + radius_y * 0.6)
	right_button.position = c + Vector2(radius_x + icon_size * 0.5 + 6, -right_button.size.y * 0.5 + radius_y * 0.6)
	info_panel.position = c + Vector2(-info_panel.size.x * 0.5, -radius_y - icon_size * 0.5 - info_panel.size.y - 8)


func _center() -> Vector2:
	var cam := get_viewport().get_camera_3d()
	if cam == null or _anchor == null:
		return size * 0.5
	return cam.unproject_position(_anchor.global_position + Vector3(0, _anchor_height, 0)) - Vector2(0, lift)


## Icon positions, back to front: [[index, position, scale, depth]].
func _layout() -> Array:
	var c := _center()
	var out: Array = []
	var n := _actions.size()
	for i in n:
		var a := _angle + TAU * i / n + PI * 0.5
		var depth := (sin(a) + 1.0) * 0.5 # 1 at the front (bottom of the ellipse)
		var p := c + Vector2(cos(a) * radius_x, sin(a) * radius_y)
		out.append([i, p, lerpf(back_scale, 1.0, depth), depth])
	out.sort_custom(func(x, y): return x[3] < y[3])
	return out


func _draw() -> void:
	var c := _center()
	# A soft shadow ellipse under the ring.
	var pts := PackedVector2Array()
	for k in 32:
		var a := TAU * k / 32.0
		pts.append(c + Vector2(cos(a) * (radius_x + 26), sin(a) * (radius_y + 14) + 10))
	draw_colored_polygon(pts, Color(0.05, 0.03, 0.07, 0.35))
	for item in _layout():
		var a: Dictionary = _actions[item[0]]
		var s: float = item[2]
		var depth: float = item[3]
		var sz := icon_size * s
		var r := Rect2(item[1] - Vector2(sz, sz) * 0.5, Vector2(sz, sz))
		var tint := Color(1, 1, 1, 1).lerp(Color(0.45, 0.42, 0.5, 1), 1.0 - depth)
		if not a.enabled:
			tint = tint * Color(0.55, 0.55, 0.6, 1)
		var tex: Texture2D = _icons.get(a.icon)
		if tex != null:
			draw_texture_rect(tex, r, false, tint)
		else:
			draw_circle(item[1], sz * 0.45, tint)
		if item[0] == _index:
			draw_arc(item[1], sz * 0.55, 0, TAU, 32, Color(1, 0.93, 0.6, 0.6 + 0.4 * sin(Time.get_ticks_msec() / 180.0)), 3.0)


func _show_info() -> void:
	var a := current()
	if a.is_empty():
		return
	title_label.text = a.label
	desc_label.text = a.tooltip
	var noise: int = a.get("noise", 0)
	cost_label.visible = a.has("noise") or not a.enabled
	if not a.enabled:
		cost_label.text = a.get("reason", "Unavailable")
		cost_label.modulate = Color("ff8f80")
	else:
		cost_label.text = ("Noise +%d" % noise) if noise > 0 else "Quiet (0 Noise)"
		cost_label.modulate = Color("ffc56b") if noise > 0 else Color("8fe0c0")
		if a.get("triggers_gaze", false):
			cost_label.text += "  ·  TRIGGERS HUMAN GAZE"
	info_panel.reset_size()


func _shake() -> void:
	var tw := create_tween()
	var base := info_panel.position
	for dx in [8.0, -8.0, 5.0, -3.0, 0.0]:
		tw.tween_property(info_panel, "position:x", base.x + dx, 0.03)


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	var stick := event is InputEventJoypadMotion
	if event.is_action_pressed("ring_left") or (stick and event.is_action_pressed("move_left")):
		turn(1)
	elif event.is_action_pressed("ring_right") or (stick and event.is_action_pressed("move_right")):
		turn(-1)
	elif event.is_action_pressed("confirm"):
		choose()
	elif event.is_action_pressed("cancel"):
		cancelled.emit()
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var hit := _icon_at(event.position)
		if hit < 0:
			return
		if hit == _index:
			choose()
		else:
			var n := _actions.size()
			var step := posmod(hit - _index, n)
			turn(step if step <= n / 2 else step - n)
	else:
		return
	get_viewport().set_input_as_handled()


func _icon_at(p: Vector2) -> int:
	var layout := _layout()
	for k in range(layout.size() - 1, -1, -1):
		var item: Array = layout[k]
		if p.distance_to(item[1]) <= icon_size * item[2] * 0.5:
			return item[0]
	return -1
