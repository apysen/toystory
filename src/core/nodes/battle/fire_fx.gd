class_name FireFX
extends RefCounted
## Builders for the particle fire and smoke in the diorama (the Toaster's palm flames,
## rocket jets, vents and his Arts' fire): CPU particles drawn as soft camera-facing
## blobs, the fire additive (white-yellow at its heart, through orange to red as it
## dies) and the smoke a grey haze. Emitters are top level and emit in world space, so
## what they shed trails behind a moving source. Presentation only.

## Fire's colour over a particle's life.
const FIRE_COLORS: Array[Color] = [Color(1.0, 0.82, 0.4, 0.75), Color(1.0, 0.5, 0.1, 0.7),
	Color(0.8, 0.14, 0.04, 0.45), Color(0.35, 0.03, 0.01, 0.0)]
const SMOKE_COLORS: Array[Color] = [Color(0.42, 0.38, 0.38, 0.0), Color(0.36, 0.33, 0.33, 0.5),
	Color(0.3, 0.28, 0.28, 0.0)]

static var _fire_mat: StandardMaterial3D
static var _smoke_mat: StandardMaterial3D


## A fire emitter: `amount` blobs alive at once, each `size` metres across at its
## biggest, living `lifetime` seconds; it burns upward until given a direction.
static func flame(amount: int, size: float, lifetime := 0.45) -> CPUParticles3D:
	var p := _emitter(amount, size, lifetime, _fire_material(), FIRE_COLORS)
	p.direction = Vector3.UP
	p.spread = 12.0
	p.gravity = Vector3(0, 1.4, 0)
	p.initial_velocity_min = 0.15
	p.initial_velocity_max = 0.35
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = size * 0.2
	return p


## A smoke emitter: slow grey puffs that rise, spread and fade.
static func smoke(amount: int, size: float, lifetime := 1.4) -> CPUParticles3D:
	var p := _emitter(amount, size, lifetime, _smoke_material(), SMOKE_COLORS)
	p.direction = Vector3.UP
	p.spread = 25.0
	p.gravity = Vector3(0, 0.25, 0)
	p.initial_velocity_min = 0.1
	p.initial_velocity_max = 0.3
	p.damping_min = 0.2
	p.damping_max = 0.4
	return p


## A light that flickers like fire; `energy` is its middle brightness.
static func light(energy: float, reach: float) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.light_color = Color(1.0, 0.55, 0.2)
	l.light_energy = energy
	l.omni_range = reach
	l.shadow_enabled = false
	return l


## Soft blobs of any colour (Teacup's tea droplets, steam and sparkles use them too):
## `colors` run over a particle's life; additive ones glow, the rest are see-through.
static func blobs(amount: int, size: float, lifetime: float, colors: Array[Color], additive: bool) -> CPUParticles3D:
	return _emitter(amount, size, lifetime, _fire_material() if additive else _smoke_material(), colors)


static func _emitter(amount: int, size: float, lifetime: float, mat: Material, colors: Array[Color]) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(size, size)
	quad.material = mat
	p.mesh = quad
	p.amount = maxi(amount, 1)
	p.lifetime = lifetime
	p.local_coords = false
	p.top_level = true
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var ramp := Gradient.new()
	var offsets := PackedFloat32Array()
	for i in colors.size():
		offsets.append(float(i) / (colors.size() - 1))
	ramp.offsets = offsets
	ramp.colors = PackedColorArray(colors)
	p.color_ramp = ramp
	var grow := Curve.new()
	grow.add_point(Vector2(0.0, 0.35))
	grow.add_point(Vector2(0.25, 1.0))
	grow.add_point(Vector2(1.0, 0.45))
	p.scale_amount_curve = grow
	p.angle_min = 0.0
	p.angle_max = 360.0
	return p


static func _fire_material() -> StandardMaterial3D:
	if _fire_mat == null:
		_fire_mat = _material(BaseMaterial3D.BLEND_MODE_ADD)
	return _fire_mat


static func _smoke_material() -> StandardMaterial3D:
	if _smoke_mat == null:
		_smoke_mat = _material(BaseMaterial3D.BLEND_MODE_MIX)
	return _smoke_mat


static func _material(blend: int) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = blend
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	m.disable_fog = true   # the room's fog would show each blob's square
	var blob := GradientTexture2D.new()
	blob.fill = GradientTexture2D.FILL_RADIAL
	blob.fill_from = Vector2(0.5, 0.5)
	blob.fill_to = Vector2(1.0, 0.5)
	blob.width = 64
	blob.height = 64
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	g.add_point(0.45, Color(1, 1, 1, 0.55))
	blob.gradient = g
	m.albedo_texture = blob
	return m
