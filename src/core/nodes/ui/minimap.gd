class_name Minimap
extends Control

## A top-down map of the battlefield in the bottom-right corner: furniture, the
## spill, every unit, the Gaze circle, telegraphed lanes, and a wedge showing where
## the camera is looking. Clicking it moves the camera there.

signal focus_requested(point: Vector2)

@export var floor_color := Color("6b4a33")
@export var border_color := Color("4f8fd0")
@export var full_cover_color := Color("2a1d16")
@export var half_cover_color := Color("b48a58")
@export var spill_color := Color(0.75, 0.38, 0.12, 0.85)
@export var player_color := Color("5aa8f0")
@export var enemy_color := Color("ec5a50")
@export var neutral_color := Color("62c86c")
@export var gaze_color := Color(0.75, 0.6, 1.0, 0.45)
@export var padding := 8.0

var _battle: Battle
var _camera: BattleCamera
var _controlled: Unit = null


func setup(b: Battle, cam: BattleCamera) -> void:
	_battle = b
	_camera = cam


func set_controlled(u: Unit) -> void:
	_controlled = u


func _process(_delta: float) -> void:
	queue_redraw()


func _scale() -> float:
	var avail := size - Vector2.ONE * padding * 2
	return minf(avail.x / _battle.field.size.x, avail.y / _battle.field.size.y)


func _origin() -> Vector2:
	var s := _scale()
	var used := _battle.field.size * s
	return (size - used) * 0.5


func to_map(p: Vector2) -> Vector2:
	var s := _scale()
	return _origin() + Vector2(p.x, _battle.field.size.y - p.y) * s


func from_map(m: Vector2) -> Vector2:
	var s := _scale()
	var local := (m - _origin()) / s
	return Vector2(local.x, _battle.field.size.y - local.y)


func _draw() -> void:
	if _battle == null:
		return
	var s := _scale()
	var f := _battle.field
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.08, 0.06, 0.1, 0.82))
	var map_rect := Rect2(to_map(Vector2(0, f.size.y)), f.size * s)
	draw_rect(map_rect, floor_color)
	for z in f.slow_zones:
		if z.has("rect"):
			draw_rect(_rect(z.rect), spill_color)
		else:
			draw_circle(to_map(z.center), z.radius * s, Color(0.9, 0.8, 0.45, 0.8))
	for o in f.objects.values():
		draw_rect(_rect(o.rect), full_cover_color if o.cover == Defs.Cover.FULL else half_cover_color)
	if _battle.gaze_active():
		draw_circle(to_map(_battle.gaze_center), Defs.GAZE_RADIUS * s, gaze_color)
	for tg in _battle.telegraphs:
		draw_line(to_map(tg.a), to_map(tg.b), Color(1, 0.2, 0.15, 0.9), tg.half_width * 2.0 * s)
	draw_rect(map_rect, border_color, false, 2.0)
	for u in f.living_units():
		var col := player_color if u.faction == Defs.Faction.PLAYER else (enemy_color if u.faction == Defs.Faction.ENEMY else neutral_color)
		if u.pending_join:
			col = neutral_color
		var r := maxf(u.radius * s, 3.0)
		draw_circle(to_map(u.pos), r + 1.5, Color(0.05, 0.03, 0.06))
		draw_circle(to_map(u.pos), r, col.darkened(0.45) if (u.acted and u.faction == Defs.Faction.PLAYER) or u.frozen else col)
		if u == _controlled:
			draw_arc(to_map(u.pos), r + 4.0, 0, TAU, 20, Color.WHITE, 2.0)
	if _camera != null:
		var c := to_map(BattleSpace.to_floor(_camera.focus))
		var look := BattleSpace.to_floor(-_camera.camera.global_transform.basis.z)
		look = Vector2(look.x, -look.y).normalized()
		var side := Vector2(-look.y, look.x)
		var back := c - look * 22.0
		draw_colored_polygon(PackedVector2Array([back, c + side * 16.0, c - side * 16.0]), Color(1, 1, 1, 0.18))
		draw_circle(c, 3.0, Color(1, 1, 1, 0.8))


func _rect(r: Rect2) -> Rect2:
	var a := to_map(Vector2(r.position.x, r.end.y))
	return Rect2(a, r.size * _scale())


func _gui_input(event: InputEvent) -> void:
	if _battle == null:
		return
	if (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT) \
			or (event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_LEFT):
		var p := from_map(event.position)
		if _battle.field.bounds().grow(1.0).has_point(p):
			focus_requested.emit(p)
		accept_event()
