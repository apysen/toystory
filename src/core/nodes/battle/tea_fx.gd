class_name TeaFX
extends RefCounted
## Builders for the particles round Teacup's tea: droplets of tea that fall (slopped
## over the rim, the warm rain of Tea Break, the splash of a Tea Lash), the steam
## that curls off her cup, and the sparkles a heal leaves. Emitters are top level and
## emit in world space (FireFX.blobs). Presentation only.

## A droplet's colour over its life: the tea in her cup, fading out at the end.
const DROP_COLORS: Array[Color] = [Color(0.65, 0.32, 0.15, 1.0), Color(0.6, 0.29, 0.13, 1.0),
	Color(0.55, 0.26, 0.11, 0.0)]
const STEAM_COLORS: Array[Color] = [Color(1.0, 1.0, 1.0, 0.0), Color(1.0, 0.98, 0.94, 0.2),
	Color(1.0, 1.0, 1.0, 0.0)]
const SPARKLE_COLORS: Array[Color] = [Color(1.0, 0.96, 0.78, 0.9), Color(1.0, 0.74, 0.3, 0.7),
	Color(1.0, 0.55, 0.2, 0.0)]
const DROP_SHADER := preload("res://assets/shaders/tea_drop.gdshader")

static var _drop_mat: ShaderMaterial


## Droplets of tea: `amount` alive at once, `size` metres across, falling under
## gravity; aim them with `direction` and the velocities.
static func drops(amount: int, size: float, lifetime := 0.6) -> CPUParticles3D:
	var p := FireFX.blobs(amount, size, lifetime, DROP_COLORS, false)
	(p.mesh as QuadMesh).material = _drop_material()
	p.direction = Vector3.UP
	p.spread = 35.0
	p.gravity = Vector3(0, -6.0, 0)
	p.initial_velocity_min = 0.4
	p.initial_velocity_max = 0.9
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = size * 0.5
	return p


## Droplets are solid beads of tea with a soft rim (tea_drop.gdshader), not the soft
## blobs of smoke.
static func _drop_material() -> ShaderMaterial:
	if _drop_mat == null:
		_drop_mat = ShaderMaterial.new()
		_drop_mat.shader = DROP_SHADER
	return _drop_mat


## Steam curling up off hot tea: slow, faint, widening wisps.
static func steam(amount: int, size: float, lifetime := 1.6) -> CPUParticles3D:
	var p := FireFX.blobs(amount, size, lifetime, STEAM_COLORS, false)
	p.direction = Vector3.UP
	p.spread = 10.0
	p.gravity = Vector3(0, 0.05, 0)
	p.initial_velocity_min = 0.08
	p.initial_velocity_max = 0.16
	p.tangential_accel_min = -0.05
	p.tangential_accel_max = 0.05
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.preprocess = lifetime   # already curling when it appears
	return p


## Glints of amber light drifting up (a heal settling in).
static func sparkles(amount: int, size: float, lifetime := 0.8) -> CPUParticles3D:
	var p := FireFX.blobs(amount, size, lifetime, SPARKLE_COLORS, true)
	p.direction = Vector3.UP
	p.spread = 30.0
	p.gravity = Vector3(0, 0.3, 0)
	p.initial_velocity_min = 0.1
	p.initial_velocity_max = 0.35
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	return p
