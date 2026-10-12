class_name TeaRibbon
extends MeshInstance3D
## A ribbon of Teacup's bent tea: it trails behind a moving head (a Callable that
## returns a world point: a bending hand, or a point the Art's show moves along a
## path) and fades out down its length, a camera-facing strip that wobbles a little
## like a stream of water. A strand instead (`strand`, a Callable taking 0..1 from
## its tail to its head) is drawn whole along that path every frame, joining two
## moving ends (her cup to her hand). `stop()` lets the tail drain away and the ribbon
## free itself. Presentation only (EffectsLayer.tea_ribbon and tea_strand make them).

const SHADER := preload("res://assets/shaders/tea_ribbon.gdshader")

## Where the head is now (world).
var head: Callable
## A strand's whole path (0 tail .. 1 head), or empty for a trail.
var strand: Callable
## Half-width at its thickest, metres.
var width := 0.02
## Seconds a point stays in the trail: its length.
var life := 0.4
## Metres the stream wobbles side to side.
var wobble := 0.005

const STRAND_POINTS := 16

var _pts := PackedVector3Array()
var _ages := PackedFloat32Array()
var _feeding := true
var _strip := ImmediateMesh.new()
static var _mat: ShaderMaterial


func _init(head_at: Callable, half_width := 0.02, seconds := 0.4) -> void:
	head = head_at
	width = half_width
	life = seconds
	name = "TeaRibbon"
	mesh = _strip
	top_level = true
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	extra_cull_margin = 4.0
	material_override = _material()


static func _material() -> ShaderMaterial:
	if _mat == null:
		_mat = ShaderMaterial.new()
		_mat.shader = SHADER
	return _mat


## Stops following the head: the tail drains away and the ribbon frees itself.
func stop() -> void:
	_feeding = false
	strand = Callable()


func _process(delta: float) -> void:
	if strand.is_valid():
		_pts.resize(STRAND_POINTS)
		_ages.resize(STRAND_POINTS)
		for i in STRAND_POINTS:
			var t := float(i) / (STRAND_POINTS - 1)
			_pts[i] = strand.call(t)
			_ages[i] = (1.0 - t) * life * 0.5   # thickest at its head, thinning to its tail
		_rebuild()
		return
	for i in _ages.size():
		_ages[i] += delta
	if _feeding and head.is_valid():
		var p: Vector3 = head.call()
		if _pts.is_empty() or _pts[_pts.size() - 1].distance_to(p) > 0.003:
			_pts.append(p)
			_ages.append(0.0)
		else:
			_ages[_ages.size() - 1] = 0.0
	while not _ages.is_empty() and _ages[0] > life:
		_pts.remove_at(0)
		_ages.remove_at(0)
	if not _feeding and _pts.size() < 2:
		queue_free()
		return
	_rebuild()


func _rebuild() -> void:
	_strip.clear_surfaces()
	var n := _pts.size()
	var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
	if n < 2 or cam == null:
		return
	var eye := cam.global_position
	var now := Time.get_ticks_msec() * 0.001
	_strip.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for i in n:
		var p := _pts[i]
		var along := clampf(_ages[i] / life, 0.0, 1.0)
		var tangent := _pts[mini(i + 1, n - 1)] - _pts[maxi(i - 1, 0)]
		var side := tangent.cross(eye - p)
		if side.length() < 1e-6:
			side = Vector3.UP
		side = side.normalized()
		# thickest just behind the head, a rounded nose, thinning to the tail
		var w := width * sqrt(1.0 - along) * minf(1.0, 0.35 + along * 10.0)
		# a ripple running back down the stream
		p += side * sin(now * 13.0 - _ages[i] * 30.0) * wobble * along
		_strip.surface_set_color(Color.WHITE)
		_strip.surface_set_uv(Vector2(along, 0.0))
		_strip.surface_add_vertex(p - side * w)
		_strip.surface_set_color(Color.WHITE)
		_strip.surface_set_uv(Vector2(along, 1.0))
		_strip.surface_add_vertex(p + side * w)
	_strip.surface_end()
