class_name PropView
extends Node2D
## One piece of cover, y-sorted with units. Position = bottom-left corner of
## its footprint. Falls back to a graybox block when there's no art.

var view: BattleView
var tile: Vector2i
var obj: Dictionary
var size_tiles := 1
var tex: Texture2D
var offset := Vector2.ZERO


func _draw() -> void:
	var T := Defs.TILE_SIZE
	var w := size_tiles * T
	if tex != null:
		draw_texture(tex, -offset)
	else:
		var full: bool = obj.terrain == Defs.Terrain.FULL_COVER
		var col := Color("3d2f26") if full else (Color("b08a58") if obj.kind.contains("box") else Color("8a5a7a"))
		var h := (1.6 if full else 0.75) * T
		var top := Rect2(6, -h - 4, w - 12, h)
		draw_rect(top, col)
		draw_rect(top, Color.BLACK, false, 2.0)
		draw_string(ThemeDB.fallback_font, top.position + Vector2(6, 18), obj.kind.replace("_", " "),
			HORIZONTAL_ALIGNMENT_LEFT, top.size.x - 8, 14, Color(1, 1, 1, 0.85))
	if obj.destructible:
		var frac: float = float(obj.hp) / obj.max_hp
		draw_rect(Rect2(12, -12, (w - 24), 6), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(12, -12, (w - 24) * frac, 6), Color("e0d080"))
