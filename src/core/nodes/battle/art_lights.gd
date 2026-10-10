class_name ArtLights
extends Node3D

## Light the Arts throw into the diorama in 3D: Lamp's Flashbulb pop, Guard Beam's
## beam and the bubble round the ally, and Spotlight's stamp ring, sky beam and the
## stage light that drops onto its area. Presentation only: EventPlayer starts each
## piece on its clip's event, and nothing here feeds back into the rules. Pieces
## either free themselves or are handed back to `fade`.

const SHADER := preload("res://assets/shaders/art_light.gdshader")
## The shader's modes (art_light.gdshader).
enum Look { BEAM, SHELL, GLARE, RING, VOLUME }

## Lamplight: the beams, bubble and stage light.
@export var light_color := Color(1.0, 0.86, 0.55)
## The Flashbulb pop, nearly white.
@export var flash_color := Color(1.0, 0.97, 0.88)

@export_group("Flashbulb")
@export var flash_energy := 9.0
@export var flash_range := 3.5
@export var flash_seconds := 0.45
## Metres across the glare at its widest.
@export var glare_size := 1.6

@export_group("Guard Beam")
@export var beam_radius := 0.03
@export var beam_grow_seconds := 0.12
## The bubble's radius as a multiple of the ally's body radius.
@export var bubble_scale := 1.8
@export var bubble_pop_seconds := 0.25

@export_group("Spotlight")
## Metres across the stamp's ring at its widest.
@export var ring_size := 3.4
@export var ring_seconds := 0.5
@export var sky_beam_height := 7.0
@export var sky_beam_radius := 0.06
## Height of the stage light above the floor.
@export var stage_height := 5.0
@export var stage_energy := 7.0
@export var stage_drop_seconds := 0.18
@export var motes := 28

## Beams that follow moving ends: [{node, from: Callable, to: Callable, grow: Array[float]}].
var _live: Array = []


## Flashbulb: a blinding pop at `at` (the lamp's shade), facing along `dir`.
func flash(at: Vector3, dir: Vector3) -> void:
	var light := OmniLight3D.new()
	light.light_color = flash_color
	light.light_energy = 0.0
	light.omni_range = flash_range
	add_child(light)
	light.global_position = at + dir * 0.1
	var glare := _mesh(_quad(1.0), _material(Look.GLARE, flash_color, true))
	glare.global_position = at + dir * 0.08
	glare.scale = Vector3.ONE * 0.2
	var tw := create_tween()
	tw.tween_property(light, "light_energy", flash_energy, 0.05)
	tw.parallel().tween_property(glare, "scale", Vector3.ONE * glare_size, 0.08)
	tw.tween_property(light, "light_energy", 0.0, flash_seconds).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_method(_strength.bind(glare), 1.0, 0.0, flash_seconds).set_ease(Tween.EASE_IN)
	tw.tween_callback(light.queue_free)
	tw.tween_callback(glare.queue_free)


## A beam of light between two moving points (each a Callable returning a world
## position), shooting out from `from`. Hand it to `fade` to end it.
func beam(from: Callable, to: Callable, radius := -1.0) -> Node3D:
	var r := beam_radius if radius < 0.0 else radius
	var cyl := CylinderMesh.new()
	cyl.top_radius = r
	cyl.bottom_radius = r
	cyl.height = 1.0
	cyl.radial_segments = 10
	cyl.rings = 1
	var m := _mesh(cyl, _material(Look.BEAM, light_color))
	var entry := {"node": m, "from": from, "to": to, "grow": [0.0]}
	_live.append(entry)
	_place(entry)
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void: entry.grow[0] = v, 0.0, 1.0, beam_grow_seconds)
	return m


## A bubble of light round a unit (Guard Beam): pops up to `radius` at `center`.
func bubble(center: Vector3, radius: float) -> Node3D:
	var sphere := SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 24
	sphere.rings = 12
	var m := _mesh(sphere, _material(Look.SHELL, light_color))
	m.global_position = center
	m.scale = Vector3.ONE * 0.01
	var tw := create_tween()
	tw.tween_property(m, "scale", Vector3.ONE * radius * 1.12, bubble_pop_seconds * 0.6).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_BACK)
	tw.tween_property(m, "scale", Vector3.ONE * radius, bubble_pop_seconds * 0.4)
	return m


## Spotlight's stamp: a ring of light running out across the floor from `at`, in
## lamplight unless `tint` is given (Overheat's eruption rings out in fire).
func ground_ring(at: Vector3, tint := Color.TRANSPARENT) -> void:
	var q := _mesh(_quad(ring_size), _material(Look.RING, light_color if tint.a == 0.0 else tint))
	q.global_position = Vector3(at.x, 0.03, at.z)
	q.rotation.x = -PI * 0.5
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void: q.set_instance_shader_parameter("ring", v), 0.05, 1.0, ring_seconds)
	tw.parallel().tween_method(_strength.bind(q), 1.0, 0.0, ring_seconds).set_ease(Tween.EASE_IN)
	tw.tween_callback(q.queue_free)


## A shaft of light straight up into the sky from a moving point.
func sky_beam(from: Callable) -> Node3D:
	return beam(from, func() -> Vector3: return from.call() + Vector3.UP * sky_beam_height, sky_beam_radius)


## Spotlight's stage light dropping onto a circle of `radius` round `center` (on the
## floor): a column of light from above, a real spot lamp, a glow on the floor and
## motes rising through it. Hand it to `fade` to end it.
func stage_light(center: Vector3, radius: float) -> Node3D:
	var root := Node3D.new()
	add_child(root)
	root.global_position = Vector3(center.x, 0.0, center.z)
	# the column hangs from a pivot at the top and grows down to the floor
	var pivot := Node3D.new()
	root.add_child(pivot)
	pivot.position = Vector3(0, stage_height, 0)
	pivot.scale = Vector3(1, 0.01, 1)
	var cone := CylinderMesh.new()
	cone.top_radius = radius * 0.45
	cone.bottom_radius = radius
	cone.height = stage_height
	cone.radial_segments = 32
	cone.rings = 1
	cone.cap_top = false
	cone.cap_bottom = false
	var column := _mesh(cone, _material(Look.VOLUME, light_color), pivot)
	column.position = Vector3(0, -stage_height * 0.5, 0)
	var floor_glow := _mesh(_quad(radius * 2.4), _material(Look.GLARE, light_color), root)
	floor_glow.position = Vector3(0, 0.025, 0)
	floor_glow.rotation.x = -PI * 0.5
	_strength(0.0, floor_glow)
	var spot := SpotLight3D.new()
	spot.light_color = light_color
	spot.light_energy = 0.0
	spot.spot_range = stage_height + 2.0
	spot.spot_angle = rad_to_deg(atan(radius / (stage_height + 1.0))) * 1.25
	spot.rotation.x = -PI * 0.5
	spot.position = Vector3(0, stage_height + 1.0, 0)
	root.add_child(spot)
	var dust := CPUParticles3D.new()
	var mote := _quad(0.045)
	mote.material = _material(Look.GLARE, light_color, true)
	dust.mesh = mote
	dust.amount = motes
	dust.lifetime = 1.4
	dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	dust.emission_box_extents = Vector3(radius * 0.7, 0.3, radius * 0.7)
	dust.direction = Vector3.UP
	dust.spread = 15.0
	dust.initial_velocity_min = 0.15
	dust.initial_velocity_max = 0.4
	dust.gravity = Vector3(0, 0.15, 0)
	dust.position = Vector3(0, 0.4, 0)
	root.add_child(dust)
	var tw := create_tween()
	tw.tween_property(pivot, "scale", Vector3.ONE, stage_drop_seconds).set_ease(Tween.EASE_IN)
	tw.tween_property(spot, "light_energy", stage_energy, 0.08)
	tw.parallel().tween_method(_strength.bind(floor_glow), 0.0, 1.0, 0.12)
	return root


## A quick shimmer round a unit the light has just covered.
func shimmer(center: Vector3, radius: float) -> void:
	var b := bubble(center, radius)
	await get_tree().create_timer(bubble_pop_seconds + 0.15, false).timeout
	fade(b, 0.35)


## Fades a piece (and everything under it) out over `seconds`, then frees it.
func fade(piece: Node3D, seconds := 0.3) -> void:
	if not is_instance_valid(piece):
		return
	var tw := create_tween().set_parallel()
	var nodes: Array[Node] = [piece]
	nodes.append_array(piece.find_children("*", "", true, false))
	for n in nodes:
		if n is GeometryInstance3D and not (n is CPUParticles3D):
			tw.tween_method(_strength.bind(n), 1.0, 0.0, seconds)
		elif n is Light3D:
			tw.tween_property(n, "light_energy", 0.0, seconds)
		elif n is CPUParticles3D:
			n.emitting = false
	tw.chain().tween_callback(func() -> void:
		_live = _live.filter(func(e: Dictionary) -> bool: return e.node != piece)
		piece.queue_free())


## How many pieces are showing (tests check everything cleans up).
func live_count() -> int:
	return get_child_count()


func _process(_delta: float) -> void:
	for entry in _live:
		if is_instance_valid(entry.node):
			_place(entry)


func _place(entry: Dictionary) -> void:
	var a: Vector3 = entry.from.call()
	var b: Vector3 = entry.to.call()
	var d: Vector3 = (b - a) * float(entry.grow[0])
	var l := d.length()
	var m: Node3D = entry.node
	if l < 0.001:
		m.visible = false
		return
	m.visible = true
	var y := d / l
	var x := y.cross(Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT).normalized()
	m.global_transform = Transform3D(Basis(x, y * l, x.cross(y)), a + d * 0.5)


func _strength(v: float, n: GeometryInstance3D) -> void:
	if is_instance_valid(n):
		n.set_instance_shader_parameter("strength", v)


func _quad(size: float) -> QuadMesh:
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	return q


func _material(mode: int, color: Color, billboard := false) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.set_shader_parameter("mode", mode)
	mat.set_shader_parameter("color", color)
	mat.set_shader_parameter("billboard", billboard)
	return mat


func _mesh(mesh: Mesh, mat: Material, parent: Node = self) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	m.mesh = mesh
	m.material_override = mat
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(m)
	return m
