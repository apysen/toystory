class_name ThreatArcs
extends MeshInstance3D

## Pulsing arcs from every enemy that could hit the controlled unit where it stands
## (Fire Emblem Fortune's Weave style). Colour says what kind of hit it is, the
## width how much it would hurt, the brightness how likely it is to land. A push or
## pull also gets a blue arrow on the floor showing where the unit would end up.

const ARC_SHADER := preload("res://assets/shaders/threat_arc.gdshader")
const CARD_HEIGHT := 0.45

@export_group("Colours")
@export var normal_color := Color(1.0, 0.28, 0.22)
@export var crit_color := Color(1.0, 0.85, 0.25)
@export var effective_color := Color(0.78, 0.35, 1.0)
@export var displace_color := Color(0.35, 0.8, 1.0)
## A crit chance at or above this shows the arc as a high-crit threat.
@export var crit_threshold := 15

@export_group("Shape")
@export var segments := 24
## Half-width of the line in metres: thin, a little thicker for heavier hits.
@export var min_width := 0.012
@export var max_width := 0.022
## Arc height as a share of its length.
@export var lift := 0.28


func _ready() -> void:
	mesh = ImmediateMesh.new()
	var mat := ShaderMaterial.new()
	mat.shader = ARC_SHADER
	material_override = mat
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# Arcs follow the camera's view; never cull them.
	custom_aabb = AABB(Vector3(-100, -10, -100), Vector3(200, 40, 200))


func clear() -> void:
	(mesh as ImmediateMesh).clear_surfaces()


## Draws the arcs for a forecast of `u` standing at `p`.
func show_forecast(forecast: Dictionary, u: Unit, p: Vector2) -> void:
	var im := mesh as ImmediateMesh
	im.clear_surfaces()
	# Telegraphed lanes are already painted on the floor; arcs are for enemies.
	if forecast.is_empty() or forecast.threats.is_empty():
		return
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var to := BattleSpace.to_world(p, CARD_HEIGHT * (2.0 if u.is_large() else 1.0))
	for th in forecast.threats:
		var e: Unit = th.enemy
		var pv: Dictionary = th.preview
		var col := normal_color
		if not th.displacement.is_empty():
			col = displace_color
		elif pv.type_rel > 0:
			col = effective_color
		elif pv.crit >= crit_threshold:
			col = crit_color
		var w := lerpf(min_width, max_width, clampf(pv.damage / 12.0, 0.0, 1.0))
		var from := BattleSpace.to_world(e.pos, CARD_HEIGHT * (2.0 if e.is_large() else 1.0))
		_arc(im, cam, from, to, w, Color(col, pv.hit / 100.0))
		if not th.displacement.is_empty() and th.displacement.dist > 0.0:
			var d: Vector2 = th.displacement.dir
			_floor_arrow(im, p, p + d * th.displacement.dist, Color(displace_color, 0.9))
	im.surface_end()


func _arc(im: ImmediateMesh, cam: Camera3D, a: Vector3, b: Vector3, width: float, col: Color) -> void:
	var mid := (a + b) * 0.5 + Vector3.UP * (a.distance_to(b) * lift + 0.3)
	var pts: Array[Vector3] = []
	for k in segments + 1:
		var t := float(k) / segments
		pts.append(a.lerp(mid, t).lerp(mid.lerp(b, t), t))
	for k in segments:
		var p0 := pts[k]
		var p1 := pts[k + 1]
		var tangent := (p1 - p0).normalized()
		var to_cam := (cam.global_position - p0).normalized()
		var side := tangent.cross(to_cam).normalized() * width
		var u0 := float(k) / segments
		var u1 := float(k + 1) / segments
		_vert(im, p0 + side, Vector2(u0, 0), col)
		_vert(im, p0 - side, Vector2(u0, 1), col)
		_vert(im, p1 - side, Vector2(u1, 1), col)
		_vert(im, p0 + side, Vector2(u0, 0), col)
		_vert(im, p1 - side, Vector2(u1, 1), col)
		_vert(im, p1 + side, Vector2(u1, 0), col)


func _floor_arrow(im: ImmediateMesh, from: Vector2, to: Vector2, col: Color) -> void:
	var d := to - from
	var len := d.length()
	if len < 0.05:
		return
	var dir := d / len
	var side := Vector2(-dir.y, dir.x)
	var h := 0.07
	var shaft_end := from + dir * maxf(len - 0.25, 0.0)
	var quad := [from + side * 0.05, from - side * 0.05, shaft_end - side * 0.05, shaft_end + side * 0.05]
	for i in [0, 1, 2, 0, 2, 3]:
		_vert(im, BattleSpace.to_world(quad[i], h), Vector2(0.9, 0.5), col)
	for v in [shaft_end + side * 0.16, shaft_end - side * 0.16, to]:
		_vert(im, BattleSpace.to_world(v, h), Vector2(1.0, 0.5), col)


func _vert(im: ImmediateMesh, p: Vector3, uv: Vector2, col: Color) -> void:
	im.surface_set_color(col)
	im.surface_set_uv(uv)
	im.surface_add_vertex(p)
