class_name CoverShields
extends Control

## Cover shields while a unit is steered (XCOM style), drawn on screen over the
## diorama. Each piece of cover close enough to shelter the unit where it stands
## gets a shield on the side facing it: a half shield for waist-high cover, a full
## one for cover that blocks sight. A half shield lights up when it is actually
## sheltering the unit from an enemy that could shoot it next Enemy Phase; it stays
## faint when no threat comes from its side.

## Metres above the floor the shields float.
@export var height := 0.42
@export var shield_size := 15.0
@export var sheltering_color := Color("8fd4ff")
@export var idle_color := Color(1.0, 0.98, 0.94, 0.55)
## Full cover this close (edge to edge, metres) counts as standing against it.
@export var full_cover_gap := 0.35

## [{at: Vector3, full: bool, active: bool}]
var _marks: Array = []


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## Shields for `u` standing at `p`, given its movement forecast there.
func show_for(battle: Battle, u: Unit, p: Vector2, forecast: Dictionary) -> void:
	_marks.clear()
	if u.is_large():
		queue_redraw()
		return
	var sheltering := {}
	for th in forecast.get("threats", []):
		if th.preview.cover:
			for id in battle.field.covering(u, p, th.from):
				sheltering[id] = true
	for o in battle.field.objects.values():
		var r: Rect2 = o.rect
		var nearest := Vector2(clampf(p.x, r.position.x, r.end.x), clampf(p.y, r.position.y, r.end.y))
		var gap := p.distance_to(nearest) - u.radius
		if o.cover == Defs.Cover.HALF and gap <= Defs.COVER_REACH - u.radius:
			_marks.append({"at": BattleSpace.to_world(nearest, height), "full": false, "active": sheltering.has(o.id)})
		elif o.cover == Defs.Cover.FULL and gap <= full_cover_gap:
			_marks.append({"at": BattleSpace.to_world(nearest, height), "full": true, "active": true})
	queue_redraw()


func clear() -> void:
	_marks.clear()
	queue_redraw()


func _process(_delta: float) -> void:
	if not _marks.is_empty():
		queue_redraw()


func _draw() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	for m in _marks:
		if cam.is_position_behind(m.at):
			continue
		_shield(cam.unproject_position(m.at), m.full, m.active)


func _shield(c: Vector2, full: bool, active: bool) -> void:
	var s := shield_size * (1.15 if active else 1.0)
	var col := sheltering_color if active else idle_color
	var dark := Color(0.05, 0.04, 0.08, 0.9)
	var outline := _outline(c, s, 0.0)
	# Full cover fills the shield; half cover only its lower half.
	draw_colored_polygon(outline if full else _outline(c, s, 1.0 / 2.1), Color(col, col.a * 0.85))
	var closed := PackedVector2Array(outline)
	closed.append(outline[0])
	draw_polyline(closed, dark, 4.0, true)
	draw_polyline(closed, col, 2.0, true)


## A heater shield round `c` (flat top, sides curving in to a point), from `from`
## of the way down (0 the top, 1 the point) to the bottom.
func _outline(c: Vector2, s: float, from: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var steps := 8
	for k in steps + 1:
		var t := lerpf(from, 1.0, float(k) / steps)
		pts.append(c + Vector2(s * 0.8 * cos(t * PI * 0.5), -s + t * s * 2.1))
	for k in range(steps - 1, -1, -1):
		var t := lerpf(from, 1.0, float(k) / steps)
		pts.append(c + Vector2(-s * 0.8 * cos(t * PI * 0.5), -s + t * s * 2.1))
	return pts
