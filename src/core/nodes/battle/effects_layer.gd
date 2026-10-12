class_name EffectsLayer
extends Node3D

## Presentation-only effects in the diorama: pixel-art bursts and projectiles on
## camera-facing sprites, Stapler's 3D staples (assets/models/vfx/staples.glb, built
## by tools/build_staples_3d.py), the Toaster's flying toast (toast.glb, built by
## tools/build_toast_3d.py) and his fire (FireFX particles: Flash Bake's cone,
## Overheat's swirl and pillars, smoke), Teacup's bent tea (TeaRibbon streams, Tea
## Lash's dart, splashes, warm rain and sparkles), floating damage numbers, and the
## Gaze transformation puff. Nothing here feeds back into the rules; everything it
## spawns frees itself.

const STAPLES := "res://assets/models/vfx/staples.glb"
const TOAST := "res://assets/models/vfx/toast.glb"
const MODEL_SHADER := preload("res://assets/shaders/unit_model.gdshader")
const LIGHT_SHADER := preload("res://assets/shaders/art_light.gdshader")
const RAIN_STREAK := "res://assets/sprites/vfx/rain_streak/rain_streak_sheet.png"
## Raincheck's drops: their size (m), how high over the circle they start, how fast they fall.
const RAIN_DROP_SIZE := Vector2(0.025, 0.11)
const RAIN_HEIGHT := 1.7
const RAIN_SPEED := 3.4
## How far up the dust sheet's middle sits over the feet (its floor line is 28 px below it).
const DUST_LIFT := 0.18

@export var float_text_size := 56
@export var float_text_pixel_size := 0.006
## Metres per second a projectile travels, clamped to a short flight.
@export var projectile_speed := 11.0

@export_group("Staples")
## Metres per second a fired staple flies, straight from the muzzle.
@export var staple_speed := 10.0
## How much bigger a flying staple is drawn than it's built: true to the pistols
## (5 cm) it is a few pixels at battle zoom and can't be seen.
@export var staple_scale := 2.2
## Seconds a staple stays stuck in what it hit before it fades.
@export var staple_stick_seconds := 0.35
@export var staple_fade_seconds := 0.25
## How far a staple that missed flies on past its target.
@export var staple_miss_metres := 1.5
## The light streak behind a flying staple.
@export var staple_trail_length := 0.4
@export var staple_trail_color := Color(1.0, 0.96, 0.9)

@export_group("Toast")
## Metres per second a launched slice travels along its arc.
@export var toast_speed := 5.5
## How big a flying slice is drawn against how it's built (the slots' size).
@export var toast_scale := 1.4
## How high its arc climbs, as a share of the distance (plus a little).
@export var toast_arc := 0.3
## Turns it tumbles over a flight.
@export var toast_turns := 1.5

@export_group("Fire")
## Metres per second Flash Bake's fire rushes out of the palms.
@export var cone_speed := 3.6
@export var cone_size := 0.2
@export var cone_amount := 60

@export_group("Rain")
## Raincheck's drops per square metre of its circle, and seconds between splashes.
@export var rain_density := 70.0
@export var rain_splash_every := 0.05

@export_group("Tea")
## Metres per second Tea Lash's dart of tea flies.
@export var dart_speed := 8.0
## How much thicker and longer bent tea is drawn than its path's true size, so it
## reads at battle zoom.
@export var tea_width := 2.0
@export var tea_length := 1.5

## "Staple" / "StapleHeavy" -> [Mesh, ShaderMaterial], loaded on first use.
var _staple_parts := {}
## [Mesh, ShaderMaterial] of the slice of toast, loaded on first use.
var _toast_part: Array = []


## Plays a one-shot effect sheet centred at `p` (world). Returns immediately.
func burst(effect: String, p: Vector3, scale_by := 1.0) -> void:
	var sf := SpriteLib.load_vfx(effect)
	if sf == null:
		return
	var s := _sprite(sf)
	s.position = p
	s.scale = Vector3.ONE * scale_by
	add_child(s)
	s.play(sf.get_animation_names()[0])
	s.animation_finished.connect(s.queue_free)


## Flies a looping projectile from a to b (no-op without art).
func projectile(effect: String, a: Vector3, b: Vector3) -> void:
	var sf := SpriteLib.load_vfx(effect)
	if sf == null:
		return
	var s := _sprite(sf)
	s.position = a
	add_child(s)
	var anim: String = sf.get_animation_names()[0]
	sf.set_animation_loop(anim, true)
	s.play(anim)
	var mid := (a + b) * 0.5 + Vector3.UP * a.distance_to(b) * 0.15
	var tw := create_tween()
	tw.tween_method(func(t: float) -> void: s.position = a.lerp(mid, t).lerp(mid.lerp(b, t), t), 0.0, 1.0,
		clampf(a.distance_to(b) / projectile_speed, 0.1, 0.35))
	await tw.finished
	s.queue_free()


## Fires a staple (Pin's heavy one if `heavy`) from `a`, a pistol's muzzle, straight
## at `b`, legs first, and waits until it gets there. One that hits sticks for a
## moment and fades; one that missed flies on past and fades.
func staple(heavy: bool, a: Vector3, b: Vector3, hit := true) -> void:
	var m := _staple_mesh(heavy)
	if m == null:
		return
	add_child(m)
	m.global_position = a
	var dir := b - a
	if dir.length() < 0.01:
		dir = Vector3.FORWARD
	m.look_at(a + dir, Vector3.UP if absf(dir.normalized().y) < 0.95 else Vector3.RIGHT, true)  # legs (+Z) lead
	m.scale = Vector3.ONE * staple_scale
	var trail := _staple_trail(m)
	var end := b if hit else b + dir.normalized() * staple_miss_metres
	var tw := create_tween()
	tw.tween_property(m, "global_position", end, clampf(a.distance_to(end) / staple_speed, 0.06, 0.6))
	if not hit:
		tw.tween_method(_staple_fade.bind(m, trail), 1.0, 0.0, staple_fade_seconds)
		tw.tween_callback(m.queue_free)
		await get_tree().create_timer(a.distance_to(b) / staple_speed, false).timeout
		return
	await tw.finished
	var after := create_tween()
	after.tween_method(func(v: float) -> void: trail.set_instance_shader_parameter("strength", v), 1.0, 0.0, 0.1)
	after.tween_interval(staple_stick_seconds)
	after.tween_method(_staple_fade.bind(m, null), 1.0, 0.0, staple_fade_seconds)
	after.tween_callback(m.queue_free)


func _staple_mesh(heavy: bool) -> MeshInstance3D:
	var key := "StapleHeavy" if heavy else "Staple"
	if not _staple_parts.has(key):
		if not ResourceLoader.exists(STAPLES):
			return null
		var inst: Node = load(STAPLES).instantiate()
		for n in inst.find_children("*", "MeshInstance3D", true, false):
			var src := (n as MeshInstance3D).mesh.surface_get_material(0) as StandardMaterial3D
			var mat := ShaderMaterial.new()
			mat.shader = MODEL_SHADER
			mat.set_shader_parameter("palette", src.albedo_texture if src != null else null)
			mat.set_shader_parameter("glow", src.emission_texture if src != null else null)
			_staple_parts[n.name] = [n.mesh, mat]
		inst.free()
	if not _staple_parts.has(key):
		return null
	var m := MeshInstance3D.new()
	m.mesh = _staple_parts[key][0]
	m.material_override = _staple_parts[key][1]
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return m


## A soft streak of light trailing behind a flying staple (along its -Z).
func _staple_trail(staple_mesh: MeshInstance3D) -> MeshInstance3D:
	var cyl := CylinderMesh.new()
	# under the staple's scale, so sized in the staple's own units
	cyl.top_radius = 0.002
	cyl.bottom_radius = 0.009
	cyl.height = staple_trail_length / staple_scale
	cyl.radial_segments = 6
	cyl.rings = 1
	var mat := ShaderMaterial.new()
	mat.shader = LIGHT_SHADER
	mat.set_shader_parameter("mode", 0)
	mat.set_shader_parameter("color", staple_trail_color)
	mat.set_shader_parameter("end_fade", 0.45)
	var t := MeshInstance3D.new()
	t.mesh = cyl
	t.material_override = mat
	t.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	t.rotation.x = -PI * 0.5   # the cylinder's thin top end points back along -Z
	t.position = Vector3(0, 0, -staple_trail_length / staple_scale * 0.5)
	staple_mesh.add_child(t)
	return t


func _staple_fade(v: float, m: MeshInstance3D, trail: MeshInstance3D) -> void:
	if is_instance_valid(m):
		m.set_instance_shader_parameter("fade", v)
	if trail != null and is_instance_valid(trail):
		trail.set_instance_shader_parameter("strength", v)


## Launches a slice of toast from `a` (a slot on the toaster) in a hot arc at `b`,
## tumbling, trailing fire and smoke, and waits until it gets there. One that hits
## drops to the floor and fades; one that missed flies on past. `arc` scales the
## climb (Overheat's are blasted sky-high).
func toast(a: Vector3, b: Vector3, hit := true, arc := 1.0) -> void:
	var m := _toast_mesh()
	if m == null:
		return
	add_child(m)
	m.scale = Vector3.ONE * toast_scale
	var end := b if hit else b + (b - a).normalized() * 1.2
	var mid := (a + end) * 0.5 + Vector3.UP * (a.distance_to(end) * toast_arc + 0.15) * arc
	var spin := Vector3(randf_range(-1, 1), 0.3, randf_range(-1, 1)).normalized()
	var trail := FireFX.flame(16, 0.07, 0.25)
	add_child(trail)
	var haze := FireFX.smoke(10, 0.1, 0.8)
	add_child(haze)
	var seconds := clampf((a.distance_to(mid) + mid.distance_to(end)) / toast_speed, 0.18, 1.2)
	var fly := func(t: float) -> void:
		var p := a.lerp(mid, t).lerp(mid.lerp(end, t), t)
		m.global_position = p
		m.basis = Basis(spin, TAU * toast_turns * t).scaled(Vector3.ONE * toast_scale)
		trail.global_position = p
		haze.global_position = p
	fly.call(0.0)
	var tw := create_tween()
	tw.tween_method(fly, 0.0, 1.0, seconds)
	await tw.finished
	trail.emitting = false
	haze.emitting = false
	_free_later(trail, 0.4)
	_free_later(haze, 1.0)
	var fall := create_tween()
	if hit:
		fall.tween_property(m, "global_position:y", 0.05, 0.3).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_QUAD)
		fall.tween_interval(0.35)
	fall.tween_method(func(v: float) -> void: m.set_instance_shader_parameter("fade", v), 1.0, 0.0, 0.25)
	fall.tween_callback(m.queue_free)


## Flash Bake: fire rushes out of each palm (`sources`, Callables returning world
## points) along `dir`, spreading over `half_angle` degrees, `reach` metres long, for
## `seconds`; a fire light flickers over it.
func fire_cone(sources: Array, dir: Vector3, reach: float, half_angle: float, seconds: float) -> void:
	var life := reach / cone_speed
	var emitters: Array[CPUParticles3D] = []
	for src in sources:
		var p := FireFX.flame(cone_amount, cone_size, life)
		p.direction = dir.normalized()
		p.spread = half_angle * 0.8
		p.gravity = Vector3(0, 0.6, 0)
		p.initial_velocity_min = cone_speed * 0.8
		p.initial_velocity_max = cone_speed * 1.1
		p.emission_sphere_radius = 0.04
		add_child(p)
		p.global_position = (src as Callable).call()
		emitters.append(p)
	var glow := FireFX.light(3.0, reach + 1.0)
	add_child(glow)
	var follow := func(_t: float) -> void:
		for k in emitters.size():
			emitters[k].global_position = (sources[k] as Callable).call()
		glow.global_position = emitters[0].global_position + dir.normalized() * reach * 0.5 + Vector3(0, 0.3, 0)
		glow.light_energy = 3.0 * (0.8 + 0.2 * sin(Time.get_ticks_msec() * 0.03))
	var tw := create_tween()
	tw.tween_method(follow, 0.0, 1.0, seconds)
	tw.tween_callback(func() -> void:
		for e in emitters:
			e.emitting = false)
	tw.tween_property(glow, "light_energy", 0.0, life)
	tw.tween_callback(glow.queue_free)
	for e in emitters:
		_free_later(e, seconds + life + 0.1)


## A pillar of fire roaring up from the floor at `at` for `seconds`.
func fire_pillar(at: Vector3, height: float, seconds: float) -> void:
	var p := FireFX.flame(40, 0.22, 0.5)
	p.emission_sphere_radius = 0.12
	p.spread = 6.0
	p.gravity = Vector3(0, 2.0, 0)
	p.initial_velocity_min = height * 1.4
	p.initial_velocity_max = height * 2.0
	add_child(p)
	p.global_position = Vector3(at.x, 0.05, at.z)
	var tw := create_tween()
	tw.tween_interval(seconds)
	tw.tween_callback(func() -> void: p.emitting = false)
	_free_later(p, seconds + 0.6)


## A ring of fire swirling up round a moving point (Overheat lifting off).
func fire_swirl(center: Callable, radius: float, seconds: float) -> void:
	var p := FireFX.flame(70, 0.16, 0.7)
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_RING
	p.emission_ring_axis = Vector3.UP
	p.emission_ring_radius = radius
	p.emission_ring_inner_radius = radius * 0.8
	p.emission_ring_height = 0.05
	p.spread = 10.0
	p.gravity = Vector3(0, 1.5, 0)
	p.initial_velocity_min = 0.6
	p.initial_velocity_max = 1.0
	p.tangential_accel_min = 4.0
	p.tangential_accel_max = 6.0
	p.radial_accel_min = -1.5
	p.radial_accel_max = -0.5
	add_child(p)
	var tw := create_tween()
	tw.tween_method(func(_t: float) -> void: p.global_position = center.call(), 0.0, 1.0, seconds)
	tw.tween_callback(func() -> void: p.emitting = false)
	_free_later(p, seconds + 0.8)


## A ribbon of Teacup's bent tea trailing a moving point (`head` returns it in the
## world), `half_width` metres either side, `seconds` long; `stop()` it to end it.
func tea_ribbon(head: Callable, half_width := 0.02, seconds := 0.4) -> TeaRibbon:
	var r := TeaRibbon.new(head, half_width * tea_width, seconds * tea_length)
	add_child(r)
	return r


## A strand of tea drawn whole along `path` (a Callable taking 0..1 from tail to head)
## each frame, joining two moving ends; `stop()` it and it drains away.
func tea_strand(path: Callable, half_width := 0.02, seconds := 0.4) -> TeaRibbon:
	var r := TeaRibbon.new(Callable(), half_width * tea_width, seconds * tea_length)
	r.strand = path
	add_child(r)
	return r


## Tea Lash's dart: a hard bead of tea punched straight from `a` (her bending hand)
## to `b` with a short tail; it splashes where it lands (one that missed flies on
## past). Waits until it gets there.
func tea_dart(a: Vector3, b: Vector3, hit := true) -> void:
	var at := [a]
	var tail := tea_ribbon(func() -> Vector3: return at[0], 0.03, 0.12)
	var end := b if hit else b + (b - a).normalized() * staple_miss_metres
	var tw := create_tween()
	tw.tween_method(func(p: Vector3) -> void: at[0] = p, a, end, clampf(a.distance_to(end) / dart_speed, 0.08, 0.5))
	await tw.finished
	tail.stop()
	if hit:
		tea_splash(end, 16)


## A splash of tea droplets bursting out of `at` and falling.
func tea_splash(at: Vector3, amount := 12) -> void:
	var p := TeaFX.drops(amount, 0.03, 0.6)
	p.one_shot = true
	p.explosiveness = 0.95   # (a one-shot burst at 1.0 draws nothing)
	p.spread = 70.0
	p.initial_velocity_min = 0.6
	p.initial_velocity_max = 1.3
	add_child(p)
	p.global_position = at
	_free_later(p, 1.0)


## Tea Break's warm rain: droplets of tea falling softly over the circle round
## `center` for `seconds`.
func tea_rain(center: Vector3, radius: float, seconds: float) -> void:
	var p := TeaFX.drops(int(radius * 40.0), 0.025, 0.55)
	p.preprocess = 0.55   # (rain that's still filling draws its unborn drops black)
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(radius * 0.7, 0.05, radius * 0.7)
	p.direction = Vector3.DOWN
	p.spread = 5.0
	p.initial_velocity_min = 0.3
	p.initial_velocity_max = 0.6
	add_child(p)
	p.global_position = center + Vector3(0, 1.4, 0)
	var tw := create_tween()
	tw.tween_interval(seconds)
	tw.tween_callback(func() -> void: p.emitting = false)
	_free_later(p, seconds + 0.8)


## Glints of amber light drifting up round `at` (a heal settling in).
func tea_sparkles(at: Vector3, radius := 0.25, amount := 14) -> void:
	var p := TeaFX.sparkles(amount, 0.06, 0.9)
	p.one_shot = true
	p.explosiveness = 0.6
	p.emission_sphere_radius = radius
	add_child(p)
	p.global_position = at
	_free_later(p, 1.2)


## Floor dust kicked out from under a unit at `at` (its feet) as it springs up into
## its float or lands.
func dust(at: Vector3) -> void:
	burst("dust_puff", at + Vector3(0, DUST_LIFT, 0), 0.8)


## Raincheck's shower: vector raindrops falling over the circle round `center` for
## `seconds`, with splashes where they land.
func rain(center: Vector3, radius: float, seconds: float) -> void:
	var p := CPUParticles3D.new()
	var quad := QuadMesh.new()
	quad.size = RAIN_DROP_SIZE
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = load(RAIN_STREAK)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y   # upright streaks
	mat.vertex_color_use_as_albedo = true
	mat.disable_fog = true   # fog would tint the whole quad
	quad.material = mat
	p.mesh = quad
	p.amount = int(radius * radius * rain_density)
	p.lifetime = RAIN_HEIGHT / RAIN_SPEED
	p.preprocess = p.lifetime   # already falling when it starts
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(radius * 0.75, 0.05, radius * 0.75)
	p.direction = Vector3.DOWN
	p.spread = 4.0
	p.gravity = Vector3.ZERO
	p.initial_velocity_min = RAIN_SPEED
	p.initial_velocity_max = RAIN_SPEED * 1.1
	p.color = Color(1, 1, 1, 0.85)
	add_child(p)
	p.global_position = center + Vector3(0, RAIN_HEIGHT, 0)
	var tw := create_tween()
	tw.tween_interval(seconds)
	tw.tween_callback(func() -> void: p.emitting = false)
	_free_later(p, seconds + p.lifetime + 0.2)
	var t := 0.0
	while t < seconds and is_inside_tree():
		t += rain_splash_every
		var a := randf() * TAU
		var d := sqrt(randf()) * radius * 0.75
		burst("rain_splash", center + Vector3(cos(a) * d, 0.12, sin(a) * d), 0.5)
		await get_tree().create_timer(rain_splash_every, false).timeout


## A puff of smoke at `at` (a slot, the floor where he lands).
func smoke_puff(at: Vector3, amount := 10, size := 0.18) -> void:
	var p := FireFX.smoke(amount, size, 1.2)
	p.one_shot = true
	p.explosiveness = 0.8
	add_child(p)
	p.global_position = at
	_free_later(p, 1.5)


func _free_later(n: Node, seconds: float) -> void:
	await get_tree().create_timer(seconds, false).timeout
	if is_instance_valid(n):
		n.queue_free()


func _toast_mesh() -> MeshInstance3D:
	if _toast_part.is_empty():
		if not ResourceLoader.exists(TOAST):
			return null
		var inst: Node = load(TOAST).instantiate()
		for n in inst.find_children("*", "MeshInstance3D", true, false):
			var src := (n as MeshInstance3D).mesh.surface_get_material(0) as StandardMaterial3D
			var mat := ShaderMaterial.new()
			mat.shader = MODEL_SHADER
			mat.set_shader_parameter("palette", src.albedo_texture if src != null else null)
			mat.set_shader_parameter("glow", src.emission_texture if src != null else null)
			_toast_part = [n.mesh, mat]
			break
		inst.free()
	if _toast_part.is_empty():
		return null
	var m := MeshInstance3D.new()
	m.mesh = _toast_part[0]
	m.material_override = _toast_part[1]
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return m


func float_text(p: Vector3, text: String, c: Color) -> void:
	var l := Label3D.new()
	l.text = text
	l.font_size = float_text_size
	l.pixel_size = float_text_pixel_size
	l.modulate = c
	l.outline_modulate = Color(0.08, 0.05, 0.08)
	l.outline_size = 14
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.render_priority = 20
	l.position = p
	add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "position:y", p.y + 0.5, 0.7).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.5).set_delay(0.45)
	tw.tween_callback(l.queue_free)


## Squash-and-flash for the Gaze transformation in both directions. A unit being
## watched first squashes down ("gaze_in"); the card swaps form at the flash and
## springs back out ("gaze_out") when the human looks away.
func gaze_poof(card: UnitCard, to_object: bool) -> void:
	if to_object:
		await card.play_gaze_in()
	var big := card.unit.is_large()
	burst("gaze_poof", card.global_position + Vector3(0, 0.9 if big else 0.45, 0), 2.0 if big else 1.0)
	var tw := create_tween()
	tw.tween_property(card, "scale", Vector3(1.25, 0.7, 1.25), 0.07)
	tw.tween_callback(card.play_transform.bind(to_object))
	tw.tween_property(card, "scale", Vector3.ONE, 0.12)


func _sprite(sf: SpriteFrames) -> AnimatedSprite3D:
	var s := AnimatedSprite3D.new()
	s.sprite_frames = sf
	# pixel art stays crisp; a smooth sheet drawn at a higher density (SpriteLib's
	# "density" meta) is shrunk to the same size and filtered
	var density: float = sf.get_meta("density", 1.0)
	s.pixel_size = 1.0 / (BattleSpace.PIXELS_PER_METRE * density)
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST if density <= 1.0 		else BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	s.shaded = false
	s.no_depth_test = true
	s.render_priority = 15
	return s
