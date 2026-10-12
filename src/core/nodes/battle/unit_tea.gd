class_name UnitTea
extends Node3D
## The tea in Teacup's cup (her head): sloshing (tipping about in the cup and heaving
## in waves) while she runs, is hit or bends it, and spilling a little over the rim at
## each high point as she runs; steam curling off it while it's hot; its level, which
## the game holds down after she's hit (a third lower each hit, down to the bottom of
## the cup) or has spilt some running (at most a third) until her next attack or Art
## refills it; the splash a flinch slops over the rim; and, when she's Broken, the
## stream her tipped cup pours out and the puddle it leaves. UnitModel adds one to a model with a "tea" bone and
## tells it each clip it plays. Presentation only.

const BONE := "tea"
## Metres the tea can be held down (TEA_LOWEST in the build): lower, its plug would
## poke out of the cup's bottom.
const LOWEST := 0.016
## Share of the way to the bottom each hit takes it.
const HIT_DROP := 1.0 / 3.0
## Clips that spend the tea and bring it back up, and the event they refill it on
## ("" for the clip's end).
const REFILLS := {"attack": "refill", "warm_pour": "refill", "steady_sip": "", "tea_break": "return"}
## The flinch slops tea over the rim this far into "hurt" without a "spill" event.
const SPILL_FALLBACK := 0.08
## Metres the shader's waves heave the tea's edge at full slosh (TEA_WAVE in
## unit_model.gdshader).
const WAVE := 0.002

## Metres from the cup's axis out to the tea's edge.
@export var rim_radius := 0.11
@export var steam_amount := 7
@export var steam_size := 0.09
## Seconds the tea takes to come back up to full.
@export var refill_seconds := 0.5
## How hard the tea sloshes (0 calm .. 1) while she scurries, while she bends it in
## an attack or Art, and in the jolt of a hit (which then calms down).
@export var move_slosh := 1.0
@export var bend_slosh := 0.8
@export var hit_slosh := 1.0
## How quickly the slosh follows (higher is snappier).
@export var slosh_follow := 4.0
## How far the surface tips about in the cup at full slosh (the rim may stop it
## sooner), and how fast it rocks front to back (side to side is slower).
@export var slosh_degrees := 9.0
@export var slosh_hz := 2.2
## Running: a few drops spill over the rim at each high point of the slosh, each
## spill lowering the tea this much (share of the way to the bottom), to at most
## `run_spill_most`.
@export var run_spill := 0.08
@export var run_spill_most := 1.0 / 3.0

## How far down the game holds the tea: 0 full, 1 at the bottom.
var held := 0.0
## How much it is sloshing right now (0 calm .. 1).
var slosh := 0.0

var _model: UnitModel
var _level: TeaLevel
var _steam: CPUParticles3D
var _stream: CPUParticles3D
var _puddle: MeshInstance3D
## Counts clips played, so a refill waiting on a clip that was cut short lets go.
var _clip := 0
## Seconds the slosh has been rocking, and which half-swing it was last on (each
## ends at a high point: front and back in turn).
var _rock := 0.0
var _half := 0


func _init(model: UnitModel, skeleton: Skeleton3D) -> void:
	_model = model
	name = "Tea"
	_level = TeaLevel.new()
	_level.name = "TeaLevel"
	skeleton.add_child(_level)
	_level.setup(skeleton, BONE)


func _ready() -> void:
	_steam = TeaFX.steam(steam_amount, steam_size)
	_steam.emission_sphere_radius = rim_radius * 0.5
	add_child(_steam)


func _process(delta: float) -> void:
	_level.drop = held * LOWEST
	var want := 0.0
	match _model.current():
		"move":
			want = move_slosh
		"attack", "warm_pour", "steady_sip", "tea_break":
			want = bend_slosh
	slosh = lerpf(slosh, want, 1.0 - exp(-slosh_follow * delta))
	_model.set_tea_slosh(slosh)
	_rock += delta
	var swing := sin(TAU * slosh_hz * _rock)
	var sway := 0.45 * sin(TAU * slosh_hz * 0.62 * _rock + 1.0)
	_level.tilt = Vector2(swing, sway) * deg_to_rad(slosh_degrees) * slosh
	_level.wave = WAVE * slosh
	# running, a few drops go over the rim at each high point (counted by half-swing, so
	# none is missed however long a frame is)
	var half := floori(2.0 * slosh_hz * _rock - 0.5)
	if half != _half and _model.current() == "move" and slosh > 0.5:
		_run_spill(1.0 if half % 2 == 0 else -1.0)
	_half = half
	var surface := _model.bone_position(BONE)
	if surface != Vector3.INF:
		_steam.global_position = surface + Vector3(0, 0.03, 0)
	if _stream != null and is_instance_valid(_stream):
		_stream.global_position = low_rim()


## Metres the game is holding the tea below where her clip puts it right now.
func lowered() -> float:
	return _level.lowered


## Radians the slosh is tipping the tea about in the cup right now.
func tipped() -> float:
	return _level.tipped


## The tea's surface in the world (where Tea Break's column climbs out of).
func surface() -> Vector3:
	return _model.bone_position(BONE)


## The lowest point of the cup's rim as it tips (where tea spills over), or the back
## of the rim while the cup stands upright.
func low_rim() -> Vector3:
	var c := _model.bone_position(BONE)
	var head := _model.bone_position("head")
	var axis := (_model.bone_position("head", Vector3.UP) - head).normalized()
	var out := Vector3.DOWN - axis * axis.dot(Vector3.DOWN)
	if out.length() < 0.08:
		out = -_model.global_basis.z    # upright: over the back (she faces +Z)
		out.y = 0.0
	return c + out.normalized() * rim_radius + axis * 0.012


## Called as the model starts a clip.
func on_play(anim: String) -> void:
	_clip += 1
	var clip := _clip
	match anim:
		"hurt":
			var spill := _model.event_time("hurt", "spill")
			await _after(SPILL_FALLBACK if is_nan(spill) else spill)
			_spill()
		"broken":
			_pour()
		_:
			if REFILLS.has(anim) and held > 0.0:
				var ev: String = REFILLS[anim]
				var at := _model.event_time(anim, ev) if ev != "" else NAN
				await _after(_model.clip_length(anim) - 0.3 if is_nan(at) else at)
				if clip == _clip:
					refill()


## Brings the tea back up to full.
func refill() -> void:
	var tw := create_tween()
	tw.tween_property(self, "held", 0.0, refill_seconds).set_ease(Tween.EASE_OUT)


## Goes cold (Broken): the steam stops.
func go_cold() -> void:
	_steam.emitting = false


## Fades the puddle with the model.
func set_opacity(v: float) -> void:
	if _puddle != null:
		_puddle.set_instance_shader_parameter("strength", clampf(v, 0.0, 1.0))


## The flinch: tea slops over the rim and the level drops a third of the way down.
func _spill() -> void:
	held = minf(held + HIT_DROP, 1.0)
	slosh = hit_slosh
	var p := TeaFX.drops(14, 0.03, 0.55)
	p.one_shot = true
	p.explosiveness = 0.95   # (a one-shot burst at 1.0 draws nothing)
	var out := low_rim() - surface()
	out.y = 0.0
	p.direction = (out.normalized() + Vector3.UP * 0.9).normalized()
	p.spread = 25.0
	p.initial_velocity_min = 0.5
	p.initial_velocity_max = 1.0
	add_child(p)
	p.global_position = low_rim()
	_free_later(p, 1.0)


## A few drops over the rim on the side the slosh has just lifted (`side` +1: her
## back, -1: her front), a little tea lost each time.
func _run_spill(side: float) -> void:
	if held < run_spill_most:
		held = minf(held + run_spill, run_spill_most)
	var c := surface()
	if c == Vector3.INF:
		return
	var out := _model.global_basis * Vector3(0, 0, -side)
	out.y = 0.0
	out = out.normalized()
	var p := TeaFX.drops(12, 0.03, 0.6)
	p.one_shot = true
	p.explosiveness = 0.95   # (a one-shot burst at 1.0 draws nothing)
	p.direction = (out + Vector3.UP * 1.2).normalized()
	p.spread = 25.0
	p.initial_velocity_min = 0.8
	p.initial_velocity_max = 1.3
	add_child(p)
	# on the rim itself, just outside the bowl, so the drops are clear of the porcelain
	p.global_position = c + out * TeaLevel.RADIUS * 1.2 + Vector3(0, 0.02, 0)
	_free_later(p, 0.9)


## Broken: as the cup tips past the rim the tea pours out over it in a stream and
## pools on the floor in front of her, until it's all gone.
func _pour() -> void:
	var pour := _model.event_time("broken", "pour")
	var empty := _model.event_time("broken", "empty")
	if is_nan(pour) or is_nan(empty):
		return
	await _after(pour)
	_stream = TeaFX.drops(70, 0.04, 0.45)
	_stream.preprocess = 0.45   # (a stream that's still filling draws its unborn drops black)
	_stream.direction = Vector3.DOWN
	_stream.spread = 5.0
	_stream.initial_velocity_min = 0.3
	_stream.initial_velocity_max = 0.5
	_stream.emission_sphere_radius = 0.015
	add_child(_stream)
	_stream.global_position = low_rim()
	var at := low_rim()
	_puddle = _make_puddle(Vector3(at.x, 0.006, at.z))
	var tw := create_tween()
	tw.tween_property(_puddle, "scale", Vector3.ONE * 0.65, empty - pour + 0.6).set_ease(Tween.EASE_OUT)
	await _after(empty - pour)
	_stream.emitting = false
	_free_later(_stream, 0.6)


func _make_puddle(at: Vector3) -> MeshInstance3D:
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	quad.orientation = PlaneMesh.FACE_Y
	var mat := ShaderMaterial.new()
	mat.shader = TeaRibbon.SHADER
	mat.set_shader_parameter("mode", 1)
	var m := MeshInstance3D.new()
	m.name = "Puddle"
	m.mesh = quad
	m.material_override = mat
	m.top_level = true
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	m.scale = Vector3.ONE * 0.05
	add_child(m)
	m.global_position = at
	return m


func _after(seconds: float) -> void:
	if seconds > 0.0:
		await get_tree().create_timer(seconds, false).timeout


func _free_later(n: Node, seconds: float) -> void:
	await get_tree().create_timer(seconds, false).timeout
	if is_instance_valid(n):
		n.queue_free()
