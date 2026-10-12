class_name UnitModel
extends Node3D

## A unit's 3D model in the diorama. UnitCard shows one in place of its sprite card
## when the unit has a model (see MODELS); it plays the same animation names the
## sprite sheets use ("idle", "move", "attack", ...), plus any extra clips the model
## brings, cross-fading between them, and turns to face the unit's heading.
##
## Models and their clips are built in Blender by tools/build_<name>_3d.py and
## tools/animate_<name>_3d.py (shared parts in tools/toy3d.py and tools/toyanim.py).
## An Art with its own clip plays it (Lamp's "spotlight", Stapler's "pin" and
## "staple_burst"); models have no generic "art", "ready" or Gaze clips, so those
## moments simply show idle. Clips that travel (intercept_run) move the
## skeleton's root bone; that motion is taken out of the pose so the card's position
## alone places the unit, and playback tweens the card instead.
##
## Beside each model, <model>_events.json gives the moments the game times itself
## by: when "attack" connects or fires ("hit"), when "intercept_guard" is braced and when its
## impact lands, and the ground speed "move" was authored for. The travel loop's
## playback follows the unit's real speed so its feet match the floor.
##
## A model with a "move_start" clip floats instead of walking (Umbrella, hanging from
## his open umbrella): starting to move launches him ("move_start", then the "move"
## float), stopping leaves him hovering ("hover"), moving again carries on floating,
## and after `land_after` seconds of game time hovering still, or when `land_now()`
## is called (his action ring opening), he lands ("move_end", then idle). Any other
## clip asked for while he's aloft waits for the landing. Other models never float.
##
## A model with flame bones (the Toaster) keeps a UnitFire burning on them. His
## toast slices can be hidden (launched, not yet back) and browned (`set_slice`).
## A model with a "tea" bone (the Teacup) keeps a UnitTea: steam, and the tea level
## the game holds down after a hit. A model with `<model>_springs.json` beside it has
## its cloth on spring bones (UnitSprings), and its cloth ripples a little in the
## shader too.

signal animation_done(anim: String)
## A floating model's feet leave or touch the floor (dust to kick up), at `at` (world).
signal kicked_dust(at: Vector3)

## Sprite or unit id -> model scene.
const MODELS := {
	"lamp": "res://assets/models/lamp/lamp_warden.glb",
	"stapler": "res://assets/models/stapler/stapler_rogue.glb",
	"toaster": "res://assets/models/toaster/toaster_pyromancer.glb",
	"teacup": "res://assets/models/teacup/teacup_cleric.glb",
	"umbrella": "res://assets/models/umbrella/umbrella_lancer.glb",
}
## Sprite or unit id -> how much bigger the model is shown than it was built, so the
## squad stands about the same height (the owner's pick: Umbrella was built from his
## smaller sprite, 0.77 m to his hat's cross, against the others' 0.82 to 1.0 m).
## Everything scales with it: clips, spring bones, bone positions; travel loops
## scale their authored speeds with it, so feet still match the floor.
const SCALE := {
	"umbrella": 1.16,
}
## Clips that loop; everything else plays once.
const LOOPS: Array[String] = ["idle", "move", "hover", "lunge_run"]
## Clips where the unit just stands: it turns three-quarters toward the camera, on
## the side of its heading, so the viewer sees its front the way the sprite shows
## it. Moving, striking and casting face the heading exactly.
const STANDING: Array[String] = ["idle", "hover", "hurt", "broken"]
const SHADER := preload("res://assets/shaders/unit_model.gdshader")

## Seconds to cross-fade from one clip into the next.
@export var blend_seconds := 0.15
## How quickly the model swings round to a new heading (higher is snappier).
@export var turn_rate := 12.0
## How far a standing unit turns toward the camera (0 = not at all, 1 = halfway).
@export var camera_turn := 0.8
## Brightness of the lamp's glow (the shade and lantern).
@export var glow_energy := 1.6
## How quickly the travel loop's playback follows a change in speed.
@export var speed_follow := 10.0
## Seconds of game time a floating model hovers still before it lands (Battle Speed
## shortens it; moving again starts the count over).
@export var land_after := 3.0

## Direction the unit faces on the floor; the model turns toward it each frame.
var heading := Vector3.RIGHT

var _player: AnimationPlayer
var _skeleton: Skeleton3D
var _meshes: Array[MeshInstance3D] = []
var _anim := ""
var _return_to_idle := true
var _events: Dictionary = {}
## Seconds into the current clip to stop and hold at (NAN = play through).
var _hold_at := NAN
var _last_pos := Vector3.INF
var _speed := 0.0
var _fire: UnitFire
var _tea: UnitTea
var _springs: UnitSprings
## Toast slices: hidden front, hidden back, browned front, browned back.
var _toast := Vector4.ZERO
## How much bigger than built the model is shown (SCALE).
var _scale := 1.0
## Floating models: off the floor (launched, not yet landed), whether the unit is
## travelling, seconds hovered still, and the clip waiting for the landing
## ([anim, return_to_idle], or empty).
var _aloft := false
var _travelling := false
var _still := 0.0
var _after_landing: Array = []


## The model for a unit, or null when it only has sprite art.
static func for_unit(u: Unit) -> UnitModel:
	var path: String = MODELS.get(u.sprite, MODELS.get(u.id, ""))
	if path == "" or not ResourceLoader.exists(path):
		return null
	var m := UnitModel.new()
	m.name = "Model"
	m._scale = float(SCALE.get(u.sprite, SCALE.get(u.id, 1.0)))
	m._load(load(path))
	m._events = _read_events(path.get_basename() + "_events.json")
	m._add_springs(UnitSprings.read(path))
	return m


static func _read_events(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


## Seconds into `anim` at which `event` happens, or NAN when the clip has no such
## moment (or the unit has no model). A clip's "speed" (the m/s it was authored for)
## comes back at the size the model is shown.
func event_time(anim: String, event: String) -> float:
	var ev: Dictionary = _events.get(anim, {})
	if not ev.has(event) or not has_anim(anim):
		return NAN
	return float(ev[event]) * (_scale if event == "speed" else 1.0)


func _load(scene: PackedScene) -> void:
	var inst := scene.instantiate()
	inst.scale = Vector3.ONE * _scale
	add_child(inst)
	_player = inst.find_child("AnimationPlayer", true, false)
	for n in inst.find_children("*", "MeshInstance3D", true, false):
		_meshes.append(n)
		_crisp_palette(n)
	if _player == null:
		return
	for anim in LOOPS:
		if _player.has_animation(anim):
			_player.get_animation(anim).loop_mode = Animation.LOOP_LINEAR
	var skeletons := inst.find_children("*", "Skeleton3D", true, false)
	if not skeletons.is_empty():
		var skeleton: Skeleton3D = skeletons[0]
		_skeleton = skeleton
		var root_node := _player.get_node(_player.root_node)
		_player.root_motion_track = NodePath("%s:%s" % [root_node.get_path_to(skeleton), skeleton.get_bone_name(0)])
		if skeleton.find_bone(UnitFire.FLAME_BONES[0]) >= 0:
			_fire = UnitFire.new(self)
			add_child(_fire)
		if skeleton.find_bone(UnitTea.BONE) >= 0:
			_tea = UnitTea.new(self, skeleton)
			add_child(_tea)
	_player.animation_finished.connect(_on_finished)
	play("idle")


## Puts the model's cloth on spring bones, when it has a springs file.
func _add_springs(data: Dictionary) -> void:
	if data.is_empty() or _skeleton == null:
		return
	_springs = UnitSprings.new(_skeleton, data)
	add_child(_springs)
	for m in _meshes:
		m.set_instance_shader_parameter("cloth_ripple", 1.0)


## The model's spring bones, or null when its cloth has none.
func springs() -> UnitSprings:
	return _springs


## Swaps the imported material for the HD-2D model shader, keeping its palette and
## glow textures.
func _crisp_palette(mesh: MeshInstance3D) -> void:
	for i in mesh.mesh.get_surface_count():
		var src := mesh.mesh.surface_get_material(i) as StandardMaterial3D
		if src == null:
			continue
		var mat := ShaderMaterial.new()
		mat.shader = SHADER
		mat.set_shader_parameter("palette", src.albedo_texture)
		mat.set_shader_parameter("glow", src.emission_texture)
		mat.set_shader_parameter("glow_energy", glow_energy)
		mesh.set_surface_override_material(i, mat)


func has_anim(anim: String) -> bool:
	return _player != null and _player.has_animation(anim)


## Plays a clip: looping clips run until replaced; others finish with
## `animation_done` and then fall back to idle unless `return_to_idle` is false.
## A floating model routes travel through its launch, float, hover and landing.
func play(anim: String, return_to_idle := true) -> void:
	if not has_anim(anim):
		return
	if floats():
		if anim == "move":
			_travelling = true
			if not _aloft:
				_aloft = true
				_play_clip("move_start", false)
			elif _anim == "hover":
				_play_clip("move")
			elif _anim == "move_end":
				_after_landing = ["move", true]  # off again once the landing's done
			return
		if anim == "idle" and _aloft:
			_travelling = false
			if _anim == "move":
				_still = 0.0
				_play_clip("hover")
			return
		if _aloft and anim != "move_end":
			_after_landing = [anim, return_to_idle]
			land_now()
			return
	_play_clip(anim, return_to_idle)


## Whether this model floats on its umbrella instead of walking.
func floats() -> bool:
	return has_anim("move_start") and has_anim("move_end") and has_anim("hover")


## Whether a floating model is off the floor.
func is_aloft() -> bool:
	return _aloft


## Lands a floating model now ("move_end", then idle or the clip that was waiting);
## does nothing on the ground or for other models.
func land_now() -> void:
	if not _aloft or _anim == "move_end":
		return
	_travelling = false
	_play_clip("move_end", false)


func _play_clip(anim: String, return_to_idle := true) -> void:
	_return_to_idle = return_to_idle
	_hold_at = NAN
	if anim == _anim and anim in LOOPS and _player.is_playing():
		return
	if _anim != "" and _anim not in LOOPS and _player.is_playing():
		# Cut short: whoever waits for it to finish still hears that it did.
		animation_done.emit.call_deferred(_anim)
	_anim = anim
	_player.play(anim, blend_seconds)
	if anim not in LOOPS:
		_player.seek(0.0, true)
	if _tea != null:
		_tea.on_play(anim)


func current() -> String:
	return _anim


## Plays `anim` from the start and stops on the frame at `seconds`, holding it
## until `resume_from` (the guard waits braced for the blow).
func hold(anim: String, seconds: float) -> void:
	play(anim, false)
	_hold_at = seconds


## Carries on from `seconds` into the held clip.
func resume_from(seconds: float) -> void:
	if _player == null or _anim == "":
		return
	_hold_at = NAN
	_player.seek(seconds, true)
	_player.play()


func clip_length(anim: String) -> float:
	return _player.get_animation(anim).length if has_anim(anim) else 0.0


func _on_finished(anim: StringName) -> void:
	if String(anim) != _anim:
		return
	if anim == &"move_start":
		_still = 0.0
		_play_clip("move" if _travelling else "hover")
		return
	if anim == &"move_end":
		_aloft = false
		var next := _after_landing
		_after_landing = []
		if next.is_empty():
			_play_clip("idle")
		else:
			play(next[0], next[1])
		animation_done.emit("move_end")
		return
	if _return_to_idle:
		play("idle")
	animation_done.emit(String(anim))


## Multiplies the model's glow (1 = as built); Arts flare it.
func set_glow(v: float) -> void:
	for m in _meshes:
		m.set_instance_shader_parameter("glow_boost", maxf(v, 0.0))


## The fire burning on the model's bones, or null when it has none.
func fire() -> UnitFire:
	return _fire


## The tea in the model's cup (the Teacup's), or null when it has none.
func tea() -> UnitTea:
	return _tea


## One of the Toaster's slices ("front" or "back"): hidden while it is flying, and
## browned (0..1) once it has toasted; a negative `brown` leaves it as it is.
func set_slice(slot: String, hidden: bool, brown := -1.0) -> void:
	if slot == "front":
		_toast.x = 1.0 if hidden else 0.0
		_toast.z = brown if brown >= 0.0 else _toast.z
	else:
		_toast.y = 1.0 if hidden else 0.0
		_toast.w = brown if brown >= 0.0 else _toast.w
	for m in _meshes:
		m.set_instance_shader_parameter("toast_state", _toast)


func slice_brown(slot: String) -> float:
	return _toast.z if slot == "front" else _toast.w


func slice_hidden(slot: String) -> bool:
	return (_toast.x if slot == "front" else _toast.y) > 0.5


## How much the Teacup's tea sloshes (0 calm ripples .. 1 sloshing; unit shader).
func set_tea_slosh(v: float) -> void:
	for m in _meshes:
		m.set_instance_shader_parameter("tea_slosh", clampf(v, 0.0, 1.0))


## Goes cold (Broken): the glow dies and any fire goes out.
func go_cold(seconds := 1.2) -> void:
	if _fire != null:
		_fire.go_out()
	if _tea != null:
		_tea.go_cold()
	var tw := create_tween()
	tw.tween_method(set_glow, 1.0, 0.0, seconds)


## Where a point on a bone is in the world right now: `offset` in the bone's own
## frame, whose Y runs from its head toward its tail. (0, 0.13, 0) is the middle of
## the glass hanging below Lamp's "lantern" hinge; Stapler's muzzles sit up and
## along their "gun" bones. Vector3.INF when there is no such bone.
func bone_position(bone: String, offset := Vector3.ZERO) -> Vector3:
	if _skeleton == null:
		return Vector3.INF
	var i := _skeleton.find_bone(bone)
	if i < 0:
		return Vector3.INF
	return _skeleton.global_transform * (_skeleton.get_bone_global_pose(i) * offset)


## Fades the whole model in or out (1 = solid, 0 = gone), dithered like the cards.
func set_opacity(v: float) -> void:
	for m in _meshes:
		m.set_instance_shader_parameter("fade", clampf(v, 0.0, 1.0))
	if _tea != null:
		_tea.set_opacity(v)


func _process(delta: float) -> void:
	_follow_clip_timing(delta)
	_float_timing(delta)
	var yaw := _target_yaw()
	if not is_nan(yaw):
		rotation.y = lerp_angle(rotation.y, yaw, 1.0 - exp(-turn_rate * delta))


## A floating model kicks up dust as it lifts off and lands, and lands by itself
## after hovering still for `land_after` seconds.
func _float_timing(delta: float) -> void:
	if not floats() or _player == null:
		return
	if _anim == "move_start" or _anim == "move_end":
		var ev := "lift" if _anim == "move_start" else "land"
		var t := event_time(_anim, ev)
		var pos := _player.current_animation_position
		if not is_nan(t) and pos >= t and pos - delta * _player.speed_scale < t:
			kicked_dust.emit(global_position)
	if _aloft and _anim == "hover":
		_still += delta
		if _still >= land_after:
			land_now()


func _follow_clip_timing(delta: float) -> void:
	if _player == null:
		return
	if not is_nan(_hold_at) and _player.is_playing() and _player.current_animation_position >= _hold_at:
		_player.pause()
		_player.seek(_hold_at, true)
	# Travel loops play at the pace the unit actually covers ground.
	var authored := float(_events.get(_anim, {}).get("speed", 0.0)) * _scale
	if delta > 0.0 and _last_pos != Vector3.INF:
		var moved := global_position - _last_pos
		moved.y = 0.0
		_speed = lerpf(_speed, moved.length() / delta, 1.0 - exp(-speed_follow * delta))
	_last_pos = global_position
	if _anim in LOOPS and authored > 0.0:
		_player.speed_scale = clampf(_speed / authored, 0.35, 2.5)
	else:
		_player.speed_scale = 1.0


## Snaps straight to its facing (no swing), e.g. when first placed.
func face_now() -> void:
	var yaw := _target_yaw()
	if not is_nan(yaw):
		rotation.y = yaw


## World yaw to face: the heading, turned partly toward the camera while standing.
func _target_yaw() -> float:
	var flat := Vector3(heading.x, 0.0, heading.z)
	if flat.length() < 0.001:
		return NAN
	flat = flat.normalized()
	var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
	if cam != null and _anim in STANDING:
		var to_cam := cam.global_position - global_position
		to_cam.y = 0.0
		if to_cam.length() > 0.001:
			flat = (flat + to_cam.normalized() * camera_turn).normalized()
	return atan2(flat.x, flat.z)  # the model faces +Z
