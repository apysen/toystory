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

signal animation_done(anim: String)

## Sprite or unit id -> model scene.
const MODELS := {
	"lamp": "res://assets/models/lamp/lamp_warden.glb",
	"stapler": "res://assets/models/stapler/stapler_rogue.glb",
}
## Clips that loop; everything else plays once.
const LOOPS: Array[String] = ["idle", "move"]
## Clips where the unit just stands: it turns three-quarters toward the camera, on
## the side of its heading, so the viewer sees its front the way the sprite shows
## it. Moving, striking and casting face the heading exactly.
const STANDING: Array[String] = ["idle", "hurt", "broken"]
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

## Direction the unit faces on the floor; the model turns toward it each frame.
var heading := Vector3.RIGHT

var _player: AnimationPlayer
var _meshes: Array[MeshInstance3D] = []
var _anim := ""
var _return_to_idle := true
var _events: Dictionary = {}
## Seconds into the current clip to stop and hold at (NAN = play through).
var _hold_at := NAN
var _last_pos := Vector3.INF
var _speed := 0.0


## The model for a unit, or null when it only has sprite art.
static func for_unit(u: Unit) -> UnitModel:
	var path: String = MODELS.get(u.sprite, MODELS.get(u.id, ""))
	if path == "" or not ResourceLoader.exists(path):
		return null
	var m := UnitModel.new()
	m.name = "Model"
	m._load(load(path))
	m._events = _read_events(path.get_basename() + "_events.json")
	return m


static func _read_events(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


## Seconds into `anim` at which `event` happens, or NAN when the clip has no such
## moment (or the unit has no model).
func event_time(anim: String, event: String) -> float:
	var ev: Dictionary = _events.get(anim, {})
	return float(ev[event]) if ev.has(event) and has_anim(anim) else NAN


func _load(scene: PackedScene) -> void:
	var inst := scene.instantiate()
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
		var root_node := _player.get_node(_player.root_node)
		_player.root_motion_track = NodePath("%s:%s" % [root_node.get_path_to(skeleton), skeleton.get_bone_name(0)])
	_player.animation_finished.connect(_on_finished)
	play("idle")


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
func play(anim: String, return_to_idle := true) -> void:
	if not has_anim(anim):
		return
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
	if _return_to_idle:
		play("idle")
	animation_done.emit(String(anim))


## Fades the whole model in or out (1 = solid, 0 = gone), dithered like the cards.
func set_opacity(v: float) -> void:
	for m in _meshes:
		m.set_instance_shader_parameter("fade", clampf(v, 0.0, 1.0))


func _process(delta: float) -> void:
	_follow_clip_timing(delta)
	var yaw := _target_yaw()
	if not is_nan(yaw):
		rotation.y = lerp_angle(rotation.y, yaw, 1.0 - exp(-turn_rate * delta))


func _follow_clip_timing(delta: float) -> void:
	if _player == null:
		return
	if not is_nan(_hold_at) and _player.is_playing() and _player.current_animation_position >= _hold_at:
		_player.pause()
		_player.seek(_hold_at, true)
	# The travel loop plays at the pace the unit actually covers ground.
	var authored := float(_events.get("move", {}).get("speed", 0.0))
	if delta > 0.0 and _last_pos != Vector3.INF:
		var moved := global_position - _last_pos
		moved.y = 0.0
		_speed = lerpf(_speed, moved.length() / delta, 1.0 - exp(-speed_follow * delta))
	_last_pos = global_position
	if _anim == "move" and authored > 0.0:
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
