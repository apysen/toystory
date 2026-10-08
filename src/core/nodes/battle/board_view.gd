class_name BoardView
extends Node2D

## Draws the battlefield: floor and terrain, the highlight overlay, y-sorted units
## and cover, and the forecast lines on top. Owns the tile <-> pixel mapping.
##
## It reads the live `Battle` and the shared `BattleSelection` and never changes
## either. Art falls back to graybox when sprites aren't in the project.

const T := Defs.TILE_SIZE
const NONE := BattleSelection.NONE

@export_group("Layers")
## Floor art, spill and tape overlays, rubble and the grid.
@export var floor_layer: Node2D
## Gaze area, telegraphs, movement and target highlights.
@export var overlay_layer: Node2D
## Y-sorted units and cover, so whatever stands lower on screen is drawn in front.
@export var units_layer: Node2D
## Path preview, threat lines, displacement arrows and the cursor.
@export var top_layer: Node2D

@export_group("Layout")
## Pixel position of the map's top-left corner.
@export var map_origin := Vector2(16, 48)
@export var grid_color := Color(0, 0, 0, 0.18)

var battle: Battle
var selection: BattleSelection
## Short-lived area flashes: tile -> Color.
var flash_tiles := {}
## Destroyed cardboard left as rubble: tile -> kind.
var destroyed_cover := {}

var _views := {} # unit id -> UnitView
var _props: Array[PropView] = []
var _env: Dictionary = {}


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_env = EnvArt.load_all()
	floor_layer.draw.connect(_draw_floor)
	overlay_layer.draw.connect(_draw_overlay)
	top_layer.draw.connect(_draw_top)


## Builds the unit and cover views for a freshly started battle.
func setup(b: Battle, s: BattleSelection) -> void:
	battle = b
	selection = s
	for u in battle.board.units:
		var v := UnitView.new()
		v.setup(u)
		units_layer.add_child(v)
		_views[u.id] = v
		place(u)
	sync_props()


func view_of(u: Unit) -> UnitView:
	return _views[u.id]


func redraw() -> void:
	floor_layer.queue_redraw()
	overlay_layer.queue_redraw()
	top_layer.queue_redraw()


## Copies every unit's state into its view (HP, Gaze form, Broken).
func sync_units() -> void:
	for id in _views:
		var v: UnitView = _views[id]
		v.shown_hp = v.unit.hp
		if not v.unit.broken:
			v.refresh()


func place(u: Unit) -> void:
	view_of(u).position = foot_point(u, u.pos)


func map_rect() -> Rect2:
	return Rect2(map_origin, Vector2(battle.board.width, battle.board.height) * T)


# --- Coordinates ----------------------------------------------------------------

func tile_rect(t: Vector2i) -> Rect2:
	return Rect2(map_origin + Vector2((t.x - 1) * T, (battle.board.height - t.y) * T), Vector2(T, T))


func tile_center(t: Vector2i) -> Vector2:
	return tile_rect(t).get_center()


func unit_center(u: Unit, anchor: Vector2i) -> Vector2:
	var a := tile_rect(anchor)
	var s := u.size * T
	return Vector2(a.position.x + s / 2.0, a.end.y - s / 2.0)


## Bottom-centre of the footprint: where the unit's feet go.
func foot_point(u: Unit, anchor: Vector2i) -> Vector2:
	var a := tile_rect(anchor)
	return Vector2(a.position.x + u.size * T / 2.0, a.end.y - 4)


func px_to_tile(p: Vector2) -> Vector2i:
	var local := p - map_origin
	if local.x < 0 or local.y < 0:
		return NONE
	var t := Vector2i(int(local.x / T) + 1, battle.board.height - int(local.y / T))
	return t if battle.board.in_bounds(t) else NONE


# --- Cover ------------------------------------------------------------------------

## Props live in the y-sorted unit layer so units in front overlap them.
func sync_props() -> void:
	for c in _props:
		c.queue_free()
	_props.clear()
	var b := battle.board
	var done := {}
	for t: Vector2i in b.objects:
		var o: Dictionary = b.objects[t]
		var tile := t
		var size_tiles := 1
		if o.kind == "cabinet":
			# One 2x2 prop drawn from the cabinet's bottom-left tile.
			if done.has("cabinet"):
				continue
			done["cabinet"] = true
			tile = _bottom_left_of_kind(b, "cabinet")
			size_tiles = 2
		var p := PropView.new()
		p.obj = o
		p.size_tiles = size_tiles
		var tag := ""
		if b.is_destructible(tile):
			tag = "damaged" if o.hp < o.max_hp else "intact"
		elif _env.variants.has(tile):
			tag = _env.variants[tile]
		p.tex = EnvArt.frame(_env, o.kind, tag)
		p.offset = EnvArt.offset(_env, o.kind)
		var r := tile_rect(tile)
		p.position = Vector2(r.position.x, r.end.y)
		units_layer.add_child(p)
		_props.append(p)


func _bottom_left_of_kind(b: Board, kind: String) -> Vector2i:
	var best := Vector2i(999, 999)
	for t: Vector2i in b.objects:
		if b.objects[t].kind == kind and (t.y < best.y or (t.y == best.y and t.x < best.x)):
			best = t
	return best


func mark_destroyed(t: Vector2i, kind: String) -> void:
	destroyed_cover[t] = kind
	sync_props()
	floor_layer.queue_redraw()


# --- Drawing ---------------------------------------------------------------------------

func _draw_floor() -> void:
	if battle == null:
		return
	var n := floor_layer
	var b := battle.board
	var floor_tex: Texture2D = _env.floor
	if floor_tex != null:
		n.draw_texture(floor_tex, map_origin)
	for x in range(1, b.width + 1):
		for y in range(1, b.height + 1):
			var t := Vector2i(x, y)
			var r := tile_rect(t)
			if floor_tex == null:
				var c := Color("6b5544") if (x + y) % 2 == 0 else Color("735b49")
				n.draw_rect(r, c)
			if b.slow_tiles.has(t):
				var kind: String = b.slow_tiles[t]
				var over: Texture2D = EnvArt.frame(_env, "sticky_tape") if kind == "tape" else EnvArt.spill_frame(_env, t)
				if over != null:
					n.draw_texture(over, r.position)
				else:
					n.draw_rect(r.grow(-4), Color("4a8fb8", 0.75) if kind == "spill" else Color("d8c070", 0.7))
	for t in destroyed_cover:
		var kind: String = destroyed_cover[t]
		var tex := EnvArt.frame(_env, kind, "destroyed")
		if tex != null:
			var r := tile_rect(t)
			n.draw_texture(tex, Vector2(r.position.x, r.end.y) - EnvArt.offset(_env, kind))
	for x in range(b.width + 1):
		n.draw_line(map_origin + Vector2(x * T, 0), map_origin + Vector2(x * T, b.height * T), grid_color)
	for y in range(b.height + 1):
		n.draw_line(map_origin + Vector2(0, y * T), map_origin + Vector2(b.width * T, y * T), grid_color)


func _draw_overlay() -> void:
	if battle == null:
		return
	var n := overlay_layer
	var s := selection
	for t in battle.gaze_tiles:
		n.draw_rect(tile_rect(t), Color(0.7, 0.55, 1.0, 0.35))
		n.draw_rect(tile_rect(t).grow(-1), Color(0.85, 0.75, 1.0, 0.9), false, 2.0)
	if battle.gaze_active():
		_draw_eye(n, tile_center(battle.gaze_center) + Vector2(0, -T * 1.6))
	# Telegraphed lanes are always visible.
	for tg in battle.telegraphs:
		for t in tg.tiles:
			var r := tile_rect(t)
			n.draw_rect(r, Color(1, 0.1, 0.1, 0.25))
			for i in range(-T, T, 12):
				n.draw_line(r.position + Vector2(maxf(i, 0), maxf(-i, 0)), r.position + Vector2(minf(i + T, T), minf(T - i, T)), Color(1, 0.2, 0.2, 0.5), 2.0)
	if s.inspected_enemy != null and not s.inspected_enemy.broken:
		var e := s.inspected_enemy
		var m := battle.board.reach_map(e, e.pos, battle.effective_move(e))
		var reach := {}
		for a in m:
			if a == e.pos or battle.board.can_stand(e, a):
				for t in e.tiles_at(a):
					reach[t] = true
		for t in reach:
			n.draw_rect(tile_rect(t).grow(-2), Color(1, 0.5, 0.3, 0.28))
	if s.mode == BattleSelection.Mode.SELECTED and s.selected != null:
		for a in s.move_set:
			for t in s.selected.tiles_at(a):
				n.draw_rect(tile_rect(t).grow(-3), Color(0.35, 0.65, 1.0, 0.22))
				n.draw_rect(tile_rect(t).grow(-3), Color(0.55, 0.8, 1.0, 0.45), false, 2.0)
	if s.mode == BattleSelection.Mode.TARGET:
		var friendly := s.target_kind == "talk" or s.is_art_kind("ally")
		var directional := s.is_art_kind("direction")
		for o in s.target_options:
			if o is Unit:
				for t in o.tiles():
					n.draw_rect(tile_rect(t).grow(-2), Color(0.3, 1, 0.5, 0.4) if friendly else Color(1, 0.3, 0.3, 0.4))
			elif o is Vector2i and not directional:
				n.draw_rect(tile_rect(o).grow(-2), Color(1, 0.8, 0.3, 0.4))
		if directional and s.hover_target != null:
			for t in battle.cone_for(s.selected, s.hover_target):
				n.draw_rect(tile_rect(t).grow(-2), Color(1, 0.6, 0.2, 0.45))
		elif directional:
			for d in s.target_options:
				for t in battle.cone_for(s.selected, d):
					n.draw_rect(tile_rect(t).grow(-6), Color(1, 0.6, 0.2, 0.15))
	for t in flash_tiles:
		n.draw_rect(tile_rect(t), flash_tiles[t])
	if s.selected != null:
		for t in s.selected.tiles():
			n.draw_rect(tile_rect(t).grow(-1), Color(1, 1, 1, 0.9), false, 2.0)


## A watching eye over the Attention Point.
func _draw_eye(n: Node2D, c: Vector2) -> void:
	var eye := SpriteLib.load_ui("eye")
	if eye != null:
		n.draw_texture(eye, (c - eye.get_size() / 2).round())
		return
	var pts := PackedVector2Array()
	for i in 32:
		var a := TAU * i / 32.0
		pts.append(c + Vector2(cos(a) * 44, sin(a) * 20))
	n.draw_colored_polygon(pts, Color(0.95, 0.92, 1.0, 0.9))
	n.draw_polyline(pts + PackedVector2Array([pts[0]]), Color(0.3, 0.2, 0.45), 3.0)
	n.draw_circle(c, 15, Color(0.45, 0.3, 0.7))
	n.draw_circle(c, 7, Color(0.08, 0.05, 0.12))


func _draw_top() -> void:
	if battle == null:
		return
	var n := top_layer
	var s := selection
	var sel := s.selected
	# Movement forecast: path, threat lines, displacement arrows.
	if s.mode == BattleSelection.Mode.SELECTED and sel != null and s.move_set.has(s.hover):
		var path := battle.path_to(sel, s.hover)
		for i in range(1, path.size()):
			n.draw_line(unit_center(sel, path[i - 1]), unit_center(sel, path[i]), Color(1, 1, 1, 0.7), 4.0)
		for t in sel.tiles_at(s.hover):
			n.draw_rect(tile_rect(t).grow(-1), Color.WHITE, false, 3.0)
	if not s.forecast.is_empty() and sel != null and (s.mode == BattleSelection.Mode.SELECTED or s.mode == BattleSelection.Mode.MENU):
		var dest: Vector2i = s.hover if s.mode == BattleSelection.Mode.SELECTED and s.move_set.has(s.hover) else sel.pos
		var to := unit_center(sel, dest)
		for th in s.forecast.threats:
			var e: Unit = th.enemy
			var from := unit_center(e, e.pos)
			var pv: Dictionary = th.preview
			var col := Color(1, 0.55, 0.2)
			if pv.ranged:
				col = Color(1, 0.85, 0.3)
			if not th.displacement.is_empty():
				col = Color(0.4, 0.85, 1.0)
			col.a = 0.35 + 0.6 * pv.hit / 100.0
			var stand := unit_center(e, th.from)
			if th.from != e.pos:
				_dashed(n, from, stand, Color(col, col.a * 0.6), 2.0)
			n.draw_line(stand, to, col, 3.0)
			_arrow_head(n, stand, to, col)
			if not th.displacement.is_empty() and th.displacement.dist > 0:
				var d: Vector2i = th.displacement.dir
				var tip := to + Vector2(d.x, -d.y) * T * 0.8
				n.draw_line(to, tip, Color(0.4, 0.85, 1.0), 4.0)
				_arrow_head(n, to, tip, Color(0.4, 0.85, 1.0))
	if s.hover != NONE and s.mode != BattleSelection.Mode.BUSY:
		var cur := SpriteLib.load_ui("cursor")
		if cur != null:
			n.draw_texture(cur, tile_rect(s.hover).position)
		else:
			n.draw_rect(tile_rect(s.hover), Color(1, 1, 0.6, 0.9), false, 2.0)


func _dashed(n: Node2D, a: Vector2, b: Vector2, c: Color, w: float) -> void:
	var length := a.distance_to(b)
	var dir := (b - a).normalized()
	var d := 0.0
	while d < length:
		n.draw_line(a + dir * d, a + dir * minf(d + 8, length), c, w)
		d += 14


func _arrow_head(n: Node2D, from: Vector2, to: Vector2, c: Color) -> void:
	var dir := (to - from).normalized()
	# Red threat arrows use the drawn arrowhead (points right in the art).
	var head := SpriteLib.load_ui("threat_arrowhead")
	if head != null and c.r > c.b:
		n.draw_set_transform(to - dir * 10, dir.angle())
		n.draw_texture(head, -head.get_size() / 2)
		n.draw_set_transform(Vector2.ZERO)
		return
	var tip := to - dir * 14
	var side := Vector2(-dir.y, dir.x) * 7
	n.draw_colored_polygon(PackedVector2Array([to - dir * 4, tip + side, tip - side]), c)
