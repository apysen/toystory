class_name TypeTriangle
extends Control

## The type triangle in the bottom-left corner while a unit is controlled: Smash
## beats Pierce, Pierce beats Bind, Bind beats Smash. The controlled unit's type
## is lit; the arrow out of it (what it beats) is green and the arrow into it
## (what beats it) red, matching the arrows on the units' bars.

@export var icon_size := 34.0
@export var advantage_color := Color("5ee07a")
@export var disadvantage_color := Color("ff5a4a")
@export var idle_color := Color(0.85, 0.8, 0.9, 0.35)
@export var panel_color := Color(0.09, 0.07, 0.11, 0.82)

## Corner positions as shares of the control's size: Smash at the top, Pierce
## bottom right, Bind bottom left, so every arrow runs clockwise.
const SPOTS := {
	Defs.DmgType.SMASH: Vector2(0.5, 0.3),
	Defs.DmgType.PIERCE: Vector2(0.8, 0.74),
	Defs.DmgType.BIND: Vector2(0.2, 0.74),
}
const BEATS := {
	Defs.DmgType.SMASH: Defs.DmgType.PIERCE,
	Defs.DmgType.PIERCE: Defs.DmgType.BIND,
	Defs.DmgType.BIND: Defs.DmgType.SMASH,
}

var _type := -1
var _icons := {}
var _panel := StyleBoxFlat.new()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	for t in SPOTS:
		_icons[t] = SpriteLib.load_ui("type_" + Defs.TYPE_NAMES[t].to_lower())
	_panel.bg_color = panel_color
	_panel.set_corner_radius_all(10)
	visible = false


## Lights `t` (a Defs.DmgType); a type outside the triangle hides it.
func show_type(t: int) -> void:
	_type = t
	visible = SPOTS.has(t)
	queue_redraw()


func _draw() -> void:
	draw_style_box(_panel, Rect2(Vector2.ZERO, size))
	for t in BEATS:
		var col := idle_color
		if t == _type:
			col = advantage_color
		elif BEATS[t] == _type:
			col = disadvantage_color
		_arrow(_spot(t), _spot(BEATS[t]), col)
	for t in SPOTS:
		var s := icon_size * (1.25 if t == _type else 1.0)
		var tint := Color.WHITE if t == _type else Color(1, 1, 1, 0.6)
		draw_texture_rect(_icons[t], Rect2(_spot(t) - Vector2(s, s) * 0.5, Vector2(s, s)), false, tint)


func _spot(t: int) -> Vector2:
	return SPOTS[t] * size


func _arrow(a: Vector2, b: Vector2, col: Color) -> void:
	var d := (b - a).normalized()
	var from := a + d * icon_size * 0.62
	var to := b - d * icon_size * 0.66
	draw_line(from, to, col, 2.5, true)
	var side := Vector2(-d.y, d.x)
	draw_colored_polygon(PackedVector2Array([to + d * 2.0, to - d * 7.0 + side * 4.5, to - d * 7.0 - side * 4.5]), col)
