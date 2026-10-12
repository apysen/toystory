class_name GroundOverlays
extends Node3D

## Every marking painted on the floor: the controlled unit's movement area and
## where its move began, the reach ring of the chosen action, the aimed cone or
## placed circle, target rings, gold rings under what it can hit from here, an
## inspected enemy's reach, every enemy's danger zone, the Gaze circle with its
## watching eye, Paper Cutter's telegraphed lanes and short-lived area flashes.
##
## It reads the Battle and changes nothing. All shapes are one shader on flat quads.

const SHAPE_SHADER := preload("res://assets/shaders/ground_shape.gdshader")
const LIGHT_WALL_SHADER := preload("res://assets/shaders/light_wall.gdshader")
const AREA_SHADER := preload("res://assets/shaders/reach_area.gdshader")
const HEIGHT := 0.05

## How movement areas are drawn. GLOW: a lit rim that fades inward, fainter where
## furniture stops it, growing out from the unit. CLASSIC: the earlier flat sheet
## with a line at the budget's edge, kept to compare against.
enum AreaStyle { GLOW, CLASSIC }

@export var area_style := AreaStyle.GLOW

@export_group("Movement Areas")
## The controlled unit's area (GLOW): warm cream, like chalk under the lamp.
@export var move_rim := Color(1.0, 0.94, 0.78, 1.0)
@export var move_glow_fill := Color(1.0, 0.92, 0.72, 0.05)
## An inspected enemy's reach (GLOW).
@export var enemy_rim := Color(1.0, 0.5, 0.4, 1.0)
@export var enemy_glow_fill := Color(1.0, 0.45, 0.35, 0.07)
## Every enemy's combined danger zone (the danger toggle).
@export var danger_rim := Color(1.0, 0.36, 0.3, 1.0)
@export var danger_fill := Color(1.0, 0.3, 0.25, 0.05)
## Seconds the area takes to grow out from the unit.
@export var grow_seconds := 0.35

@export_group("Colours")
@export var move_fill := Color(0.32, 0.62, 1.0, 0.1)
@export var move_edge := Color(0.6, 0.86, 1.0, 0.9)
@export var enemy_reach_fill := Color(1.0, 0.45, 0.3, 0.14)
@export var enemy_reach_edge := Color(1.0, 0.55, 0.4, 0.8)
@export var reach_ring_color := Color(1.0, 0.85, 0.4, 0.95)
@export var heal_ring_color := Color(0.5, 1.0, 0.6, 0.95)
@export var gaze_fill := Color(0.72, 0.56, 1.0, 0.22)
@export var gaze_edge := Color(0.86, 0.76, 1.0, 0.95)
## Height of the curtain of light around a Gaze, and the spotlight from above.
@export var light_wall_height := 2.4
@export var gaze_light_color := Color(0.86, 0.8, 1.0)
@export var gaze_light_energy := 6.0
@export var telegraph_fill := Color(1.0, 0.15, 0.12, 0.35)
@export var telegraph_edge := Color(1.0, 0.3, 0.25, 0.95)
@export var cone_fill := Color(1.0, 0.6, 0.2, 0.3)
## A placed area Art's circle (Spotlight), in warm lamplight.
@export var area_fill := Color(1.0, 0.86, 0.5, 0.22)
@export var area_edge := Color(1.0, 0.92, 0.65, 0.95)

var _battle: Battle
## Whether the Gaze circle is shown. Follows playback (the Gaze events) rather than
## the rules, which already know the end state before the events are played.
var gaze_visible := false
## Telegraphed lanes on the floor ({owner, a, b, half_width}). Like the Gaze, these
## follow playback: a lane appears when the Captain is seen marking it, not as soon
## as the rules know about it.
var shown_telegraphs: Array = []
var _move: MeshInstance3D
var _enemy_reach: MeshInstance3D
var _move_glow: MeshInstance3D
var _enemy_glow: MeshInstance3D
var _danger: MeshInstance3D
var _grows := {} # area mesh -> its grow-in Tween
var _reach_ring: MeshInstance3D
var _cone: MeshInstance3D
var _area: MeshInstance3D
var _start_marker: MeshInstance3D
var _gaze: MeshInstance3D
var _eye: Sprite3D
var _light_wall: MeshInstance3D
var _gaze_light: SpotLight3D
var _trail: MeshInstance3D
var _targets: Array[MeshInstance3D] = []
var _marks: Array[MeshInstance3D] = []
var _telegraphs: Array[MeshInstance3D] = []


func setup(b: Battle) -> void:
	_battle = b
	gaze_visible = b.gaze_active()
	shown_telegraphs = b.telegraphs.duplicate()
	var size := b.field.size
	_move = _quad(size, 3)
	_enemy_reach = _quad(size, 3)
	_move_glow = _area_quad(size, move_rim, move_glow_fill)
	_enemy_glow = _area_quad(size, enemy_rim, enemy_glow_fill)
	_danger = _area_quad(size, danger_rim, danger_fill)
	_params(_danger, {"glow_alpha": 0.26, "shimmer": 0.45, "shimmer_speed": 2.2})
	_danger.visible = false
	_reach_ring = _quad(size, 0)
	_cone = _quad(size, 1)
	_area = _quad(size, 0)
	_start_marker = _quad(size, 0)
	_gaze = _quad(size, 0)
	_trail = MeshInstance3D.new()
	_trail.mesh = ImmediateMesh.new()
	var tm := StandardMaterial3D.new()
	tm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	tm.albedo_color = Color(1, 1, 1, 0.75)
	tm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_trail.material_override = tm
	_trail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_trail)
	_eye = Sprite3D.new()
	_eye.texture = SpriteLib.load_ui("eye")
	_eye.pixel_size = 1.0 / 64.0
	_eye.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_eye.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	_eye.no_depth_test = true
	_eye.visible = false
	add_child(_eye)
	# The Gaze's edge: a curtain of light the rules treat as a wall.
	_light_wall = MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = Defs.GAZE_RADIUS
	cyl.bottom_radius = Defs.GAZE_RADIUS
	cyl.height = light_wall_height
	cyl.cap_top = false
	cyl.cap_bottom = false
	cyl.radial_segments = 64
	cyl.rings = 1
	_light_wall.mesh = cyl
	var lm := ShaderMaterial.new()
	lm.shader = LIGHT_WALL_SHADER
	lm.set_shader_parameter("light_color", gaze_light_color)
	lm.set_shader_parameter("wall_height", light_wall_height)
	_light_wall.material_override = lm
	_light_wall.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_light_wall.visible = false
	add_child(_light_wall)
	_gaze_light = SpotLight3D.new()
	_gaze_light.light_color = gaze_light_color
	_gaze_light.light_energy = gaze_light_energy
	_gaze_light.spot_range = 16.0
	_gaze_light.spot_angle = 12.0
	_gaze_light.spot_attenuation = 0.4
	_gaze_light.shadow_enabled = true
	_gaze_light.rotation = Vector3(-PI * 0.5, 0, 0)
	_gaze_light.visible = false
	add_child(_gaze_light)
	_params(_move, {"fill_color": move_fill, "edge_color": move_edge, "edge_width": 0.08, "pulse": 0.0})
	_params(_enemy_reach, {"fill_color": enemy_reach_fill, "edge_color": enemy_reach_edge, "edge_width": 0.06})
	_params(_gaze, {"fill_color": gaze_fill, "edge_color": gaze_edge, "pulse": 2.2, "edge_width": 0.1})
	_params(_start_marker, {"fill_color": Color(1, 1, 1, 0.12), "edge_color": Color(1, 1, 1, 0.6), "edge_width": 0.04})
	_params(_cone, {"fill_color": cone_fill, "edge_color": Color(1.0, 0.8, 0.4, 0.95), "edge_width": 0.05, "pulse": 3.0})
	_params(_area, {"fill_color": area_fill, "edge_color": area_edge, "edge_width": 0.06, "pulse": 2.0})
	hide_all()
	sync()


func hide_all() -> void:
	for m in [_move, _enemy_reach, _move_glow, _enemy_glow, _reach_ring, _cone, _area, _start_marker]:
		m.visible = false
	_trail.visible = false
	clear_targets()
	clear_marks()


## Re-reads the Gaze and the telegraphs (call after every batch of events).
func sync() -> void:
	_gaze.visible = gaze_visible
	_eye.visible = gaze_visible
	_light_wall.visible = gaze_visible
	_gaze_light.visible = gaze_visible
	if gaze_visible:
		_params(_gaze, {"center": _battle.gaze_center, "radius": Defs.GAZE_RADIUS})
		_eye.position = BattleSpace.to_world(_battle.gaze_center, light_wall_height + 1.0)
		_light_wall.position = BattleSpace.to_world(_battle.gaze_center, light_wall_height * 0.5)
		_gaze_light.position = BattleSpace.to_world(_battle.gaze_center, 7.5)
	for t in _telegraphs:
		t.queue_free()
	_telegraphs.clear()
	for tg in shown_telegraphs:
		var q := _quad(_battle.field.size, 2)
		_params(q, {"seg_a": tg.a, "seg_b": tg.b, "half_width": tg.half_width, "fill_color": telegraph_fill,
			"edge_color": telegraph_edge, "hatch": 2.0, "pulse": 4.0})
		_telegraphs.append(q)


func add_telegraph(owner: Unit, a: Vector2, b: Vector2, half_width: float) -> void:
	shown_telegraphs.append({"owner": owner, "a": a, "b": b, "half_width": half_width})
	sync()


func remove_telegraphs(owner: Unit) -> void:
	shown_telegraphs = shown_telegraphs.filter(func(t): return t.owner != owner)
	sync()


## The movement area of a unit and where its activation began.
func show_move_area(r: ReachField, start: Vector2, radius: float) -> void:
	if area_style == AreaStyle.CLASSIC:
		_show_field(_move, r)
	else:
		_show_glow(_move_glow, r, start)
	_start_marker.visible = true
	_params(_start_marker, {"center": start, "radius": radius, "inner_radius": radius * 0.7})


func hide_move_area() -> void:
	_move.visible = false
	_move_glow.visible = false
	_start_marker.visible = false
	_trail.visible = false


## A dotted trail along the path from where the move began to where the unit is.
func show_trail(path: Array[Vector2]) -> void:
	var im := _trail.mesh as ImmediateMesh
	im.clear_surfaces()
	if path.size() < 2:
		_trail.visible = false
		return
	var verts := PackedVector3Array()
	var dash := 0.18
	var gap := 0.14
	for k in range(1, path.size()):
		var a := path[k - 1]
		var b := path[k]
		var d := a.distance_to(b)
		var dir := (b - a) / maxf(d, 0.0001)
		var side := Vector2(-dir.y, dir.x) * 0.045
		var s := 0.0
		while s < d:
			var p0 := a + dir * s
			var p1 := a + dir * minf(s + dash, d)
			var v := [BattleSpace.to_world(p0 + side, HEIGHT + 0.01), BattleSpace.to_world(p0 - side, HEIGHT + 0.01),
				BattleSpace.to_world(p1 - side, HEIGHT + 0.01), BattleSpace.to_world(p1 + side, HEIGHT + 0.01)]
			for i in [0, 1, 2, 0, 2, 3]:
				verts.append(v[i])
			s += dash + gap
	_trail.visible = not verts.is_empty()
	if verts.is_empty():
		return
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for v in verts:
		im.surface_add_vertex(v)
	im.surface_end()


func show_enemy_reach(r: ReachField) -> void:
	if area_style == AreaStyle.CLASSIC:
		_show_field(_enemy_reach, r)
	else:
		_show_glow(_enemy_glow, r, r.start)


## Every enemy's combined danger zone, from Forecast.danger_grid.
func show_danger(grid: Dictionary) -> void:
	var none := PackedFloat32Array()
	none.resize(grid.cells.size())
	var t := ReachAreaTexture.from_grid(grid.cells, none, grid.cols, grid.rows, false)
	_danger.visible = true
	_params(_danger, {"shape_tex": t.shape, "glow_tex": t.glow, "tex_origin": t.origin, "tex_size": t.size})


func hide_danger() -> void:
	_danger.visible = false


func is_danger_shown() -> bool:
	return _danger.visible


func hide_enemy_reach() -> void:
	_enemy_reach.visible = false
	_enemy_glow.visible = false


## The ring an action reaches to, measured from the unit's centre.
func show_reach_ring(center: Vector2, radius: float, healing := false) -> void:
	_reach_ring.visible = true
	var c := heal_ring_color if healing else reach_ring_color
	_params(_reach_ring, {"center": center, "radius": radius, "inner_radius": maxf(radius - 0.06, 0.0),
		"fill_color": Color(c, 0.0), "edge_color": c, "edge_width": 0.05, "pulse": 2.5})


func hide_reach_ring() -> void:
	_reach_ring.visible = false


func show_cone(cone: Dictionary) -> void:
	_cone.visible = true
	_params(_cone, {"center": cone.apex, "dir": cone.dir, "cone_length": cone.length, "half_angle": cone.half_angle})


func hide_cone() -> void:
	_cone.visible = false


## The circle an area Art would cover ({center, radius}).
func show_area(area: Dictionary) -> void:
	_area.visible = true
	_params(_area, {"center": area.center, "radius": area.radius})


func hide_area() -> void:
	_area.visible = false


## Thin gold rings under the units the controlled unit could Basic Attack from here.
func show_marks(units: Array) -> void:
	clear_marks()
	for o in units:
		var q := _quad(_battle.field.size, 0)
		_params(q, {"center": o.pos, "radius": o.radius + 0.13, "inner_radius": o.radius + 0.09,
			"fill_color": Color(reach_ring_color, 0.0), "edge_color": Color(reach_ring_color, 0.85), "edge_width": 0.04,
			"pulse": 2.0})
		_marks.append(q)


func clear_marks() -> void:
	for m in _marks:
		m.queue_free()
	_marks.clear()


## Rings under the units (or cover) an action could pick; the current one pulses brighter.
func show_targets(units: Array, current: Variant, healing := false) -> void:
	clear_targets()
	for o in units:
		var center: Vector2
		var r: float
		if o is Unit:
			center = o.pos
			r = o.radius
		elif o is String and _battle.field.objects.has(o):
			var rect: Rect2 = _battle.field.objects[o].rect
			center = rect.get_center()
			r = rect.size.length() * 0.5
		else:
			continue
		var q := _quad(_battle.field.size, 0)
		var on: bool = typeof(o) == typeof(current) and o == current
		var c := heal_ring_color if healing else Color(1.0, 0.35, 0.3, 1.0)
		_params(q, {"center": center, "radius": r + (0.16 if on else 0.1), "inner_radius": r + (0.04 if on else 0.05),
			"fill_color": Color(c, 0.0), "edge_color": Color(c, 1.0 if on else 0.55), "edge_width": 0.05, "pulse": 6.0 if on else 0.0})
		_targets.append(q)


func clear_targets() -> void:
	for t in _targets:
		t.queue_free()
	_targets.clear()


## A brief flash over an Art's area or a resolving Cutting Line.
func flash_area(e: Dictionary, seconds := 0.35) -> void:
	var q: MeshInstance3D
	if e.shape == "cone":
		q = _quad(_battle.field.size, 1)
		var c: Dictionary = e.cone
		var col := Color(0.6, 0.9, 1.0, 0.4) if e.kind == "blowback" else Color(1.0, 0.6, 0.2, 0.45)
		_params(q, {"center": c.apex, "dir": c.dir, "cone_length": c.length, "half_angle": c.half_angle,
			"fill_color": col, "edge_color": Color(col, 0.95)})
	elif e.shape == "circle":
		q = _quad(_battle.field.size, 0)
		var fill := area_fill if e.kind != "staple_storm" else Color(0.85, 0.82, 0.8, 0.3)
		var edge := area_edge if e.kind != "staple_storm" else Color(0.95, 0.93, 0.9, 0.95)
		_params(q, {"center": e.center, "radius": e.radius, "fill_color": Color(fill, 0.4), "edge_color": edge,
			"edge_width": 0.06})
	else:
		q = _quad(_battle.field.size, 2)
		_params(q, {"seg_a": e.a, "seg_b": e.b, "half_width": e.half_width, "fill_color": Color(1, 0.15, 0.15, 0.6),
			"edge_color": Color(1, 0.4, 0.3, 1.0)})
	await get_tree().create_timer(seconds, false).timeout
	q.queue_free()


func _show_field(m: MeshInstance3D, r: ReachField) -> void:
	var img := Image.create(r.cols, r.rows, false, Image.FORMAT_RF)
	for cy in r.rows:
		for cx in r.cols:
			var i := cy * r.cols + cx
			var c := r.cost[i]
			# Row cy of the image is row cy of the field; the shader samples at p / size.
			img.set_pixel(cx, cy, Color(minf(c, 99.0), 0, 0))
	var tex := ImageTexture.create_from_image(img)
	m.visible = true
	_params(m, {"field_tex": tex, "field_size": Vector2(r.cols, r.rows) * ReachField.CELL, "budget": r.budget})


## Draws `r` on `m` with the reach-area shader, growing out from `from`.
func _show_glow(m: MeshInstance3D, r: ReachField, from: Vector2) -> void:
	var t := ReachAreaTexture.build(r)
	m.visible = true
	_params(m, {"shape_tex": t.shape, "glow_tex": t.glow, "tex_origin": t.origin, "tex_size": t.size, "center": from})
	if _grows.has(m):
		(_grows[m] as Tween).kill()
	var mat := m.material_override as ShaderMaterial
	var far := r.budget + 1.0
	var grow := create_tween()
	_grows[m] = grow
	grow.tween_method(func(v: float) -> void: mat.set_shader_parameter("reveal", v), 0.0, far, grow_seconds) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	grow.tween_callback(func() -> void: mat.set_shader_parameter("reveal", 1000.0))


func _area_quad(size: Vector2, rim: Color, fill: Color) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = size + Vector2(4, 4)
	m.mesh = plane
	var mat := ShaderMaterial.new()
	mat.shader = AREA_SHADER
	mat.set_shader_parameter("rim_color", rim)
	mat.set_shader_parameter("fill_color", fill)
	m.material_override = mat
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	m.position = BattleSpace.to_world(size * 0.5, HEIGHT)
	add_child(m)
	return m


func _quad(size: Vector2, mode: int) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = size + Vector2(4, 4)
	m.mesh = plane
	var mat := ShaderMaterial.new()
	mat.shader = SHAPE_SHADER
	mat.set_shader_parameter("mode", mode)
	m.material_override = mat
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	m.position = BattleSpace.to_world(size * 0.5, HEIGHT)
	add_child(m)
	return m


func _params(m: MeshInstance3D, params: Dictionary) -> void:
	var mat := m.material_override as ShaderMaterial
	for k in params:
		mat.set_shader_parameter(k, params[k])
