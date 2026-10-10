class_name BattleCamera
extends Node3D

## The free orbit camera (Sparks of Hope style): a perspective camera circling a
## focus point on the floor. It centres on the unit being controlled and glides to
## enemies as they act; otherwise the player pans it freely.
##
## Orbit: Q/E, right stick, or right-mouse drag. Tilt: R/F, right stick, or
## right-mouse drag. Zoom: mouse wheel, PgUp/PgDn or the triggers. Pan (when no
## unit is being controlled): WASD, left stick, or middle-mouse drag.

signal moved

@export var camera: Camera3D

@export_group("Orbit")
@export var start_yaw_degrees := 0.0
@export var start_pitch_degrees := 48.0
@export var min_pitch_degrees := 22.0
@export var max_pitch_degrees := 62.0
@export var orbit_speed_degrees := 110.0
@export var mouse_orbit_degrees_per_pixel := 0.25

@export_group("Zoom")
@export var start_distance := 11.0
@export var min_distance := 4.5
@export var max_distance := 24.0
@export var zoom_step := 1.2

@export_group("Follow and Pan")
## How quickly the focus catches up with a followed unit (per second).
@export var follow_sharpness := 7.0
@export var pan_speed := 9.0
## The focus stays within the map grown by this much.
@export var bounds_margin := 3.0

@export_group("Depth of Field")
## Blur starts this far behind and in front of the focus, for a tilt-shift diorama feel.
@export var far_blur_offset := 7.0
@export var near_blur_offset := 4.0

var yaw := 0.0
var pitch := 0.0
var distance := 11.0
var focus := Vector3.ZERO
var target_focus := Vector3.ZERO
## A node to follow (the controlled unit's card), or null for free panning.
var follow: Node3D = null
var input_enabled := true
## When false, WASD and the left stick steer a unit instead of panning.
var free_pan := true

var _bounds := AABB()
## The inside of the room. The camera never leaves it, so no wall stands between it
## and the focus and nothing outside the room is ever in view.
var _room := AABB()
## How close to a wall, floor-level or the top of the walls the camera may come.
@export var wall_clearance := 0.8
var _dragging_orbit := false
var _dragging_pan := false
## The zoom to come back to after a signature Art's push-in (negative: none under way).
var _cinematic_distance := -1.0


func _ready() -> void:
	yaw = deg_to_rad(start_yaw_degrees)
	pitch = deg_to_rad(start_pitch_degrees)
	distance = start_distance
	if camera.attributes == null:
		var attrs := CameraAttributesPractical.new()
		attrs.dof_blur_far_enabled = true
		attrs.dof_blur_near_enabled = true
		attrs.dof_blur_amount = 0.06
		camera.attributes = attrs
	_apply()


## Fits the focus limits to the map and starts over `start`.
func frame_map(map_size: Vector2, start: Vector3) -> void:
	_bounds = AABB(Vector3(-bounds_margin, 0, -map_size.y - bounds_margin), Vector3(map_size.x + bounds_margin * 2, 0, map_size.y + bounds_margin * 2))
	focus = start
	target_focus = start
	camera.make_current()
	_apply()


## Keeps the camera inside `room` (world space).
func set_room(room: AABB) -> void:
	_room = room.grow(-wall_clearance)
	_apply()


func look_at_point(p: Vector3, snap := false) -> void:
	follow = null
	target_focus = _clamp(p)
	if snap:
		focus = target_focus
		_apply()


## Glides to `p` and waits until the camera is there (Enemy Phase playback).
func glide_to(p: Vector3, seconds := 0.35) -> void:
	follow = null
	target_focus = _clamp(p)
	if focus.distance_to(target_focus) < 1.5:
		return
	var tw := create_tween()
	tw.tween_property(self, "focus", target_focus, seconds).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await tw.finished


## Signature Arts: glides to `p` and eases in to `scale` of the current zoom, and
## waits until it is there. `ease_back` returns to the zoom it started from.
func push_in(p: Vector3, scale: float, seconds := 0.35) -> void:
	if _cinematic_distance < 0.0:
		_cinematic_distance = distance
	follow = null
	target_focus = _clamp(p)
	var tw := create_tween()
	tw.tween_property(self, "distance", maxf(_cinematic_distance * scale, min_distance), seconds) 		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await tw.finished


## Eases back out to the zoom from before `push_in`, framing `p`.
func ease_back(p: Vector3, seconds := 0.4) -> void:
	follow = null
	target_focus = _clamp(p)
	if _cinematic_distance < 0.0:
		return
	var tw := create_tween()
	tw.tween_property(self, "distance", _cinematic_distance, seconds).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_cinematic_distance = -1.0
	await tw.finished


## A floor direction for a stick or WASD input, relative to where the camera looks:
## up is always "into the screen".
func floor_direction(input: Vector2) -> Vector2:
	var fwd := -camera.global_transform.basis.z
	fwd.y = 0
	fwd = fwd.normalized()
	var right := camera.global_transform.basis.x
	right.y = 0
	right = right.normalized()
	var w := right * input.x + fwd * -input.y
	return BattleSpace.to_floor(w)


func _process(delta: float) -> void:
	if input_enabled:
		var orbit := Input.get_axis("camera_orbit_left", "camera_orbit_right")
		yaw += orbit * deg_to_rad(orbit_speed_degrees) * delta
		var tilt := Input.get_axis("camera_pitch_up", "camera_pitch_down")
		pitch = clampf(pitch + tilt * deg_to_rad(orbit_speed_degrees * 0.6) * delta, deg_to_rad(min_pitch_degrees), deg_to_rad(max_pitch_degrees))
		var zoom := Input.get_axis("camera_zoom_in", "camera_zoom_out")
		distance = clampf(distance + zoom * zoom_step * 6.0 * delta, min_distance, max_distance)
		if free_pan and follow == null:
			var pan := Input.get_vector("move_left", "move_right", "move_up", "move_down")
			if pan != Vector2.ZERO:
				var d := floor_direction(pan)
				target_focus = _clamp(target_focus + BattleSpace.dir_to_world(d) * pan_speed * delta * (distance / start_distance))
	if follow != null:
		target_focus = _clamp(follow.global_position)
	focus = focus.lerp(target_focus, 1.0 - exp(-follow_sharpness * delta))
	_apply()


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled:
		return
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			_dragging_orbit = event.pressed
		elif event.button_index == MOUSE_BUTTON_MIDDLE:
			_dragging_pan = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance - zoom_step, min_distance, max_distance)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance + zoom_step, min_distance, max_distance)
	elif event is InputEventMouseMotion:
		if _dragging_orbit:
			yaw -= deg_to_rad(event.relative.x * mouse_orbit_degrees_per_pixel)
			pitch = clampf(pitch + deg_to_rad(event.relative.y * mouse_orbit_degrees_per_pixel), deg_to_rad(min_pitch_degrees), deg_to_rad(max_pitch_degrees))
		elif _dragging_pan:
			follow = null
			var d := floor_direction(Vector2(-event.relative.x, -event.relative.y))
			target_focus = _clamp(target_focus + BattleSpace.dir_to_world(d) * 0.02 * distance)
			focus = target_focus


func _apply() -> void:
	var offset := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	offset *= _room_limit(focus, offset)
	global_position = focus
	camera.global_position = focus + offset
	camera.look_at(focus + Vector3(0, 0.4, 0), Vector3.UP)
	# Focus blur follows where the camera really is (the room may have pulled it in).
	var actual := offset.length()
	var attrs := camera.attributes as CameraAttributesPractical
	if attrs != null:
		attrs.dof_blur_far_distance = actual + far_blur_offset
		attrs.dof_blur_far_transition = far_blur_offset
		attrs.dof_blur_near_distance = maxf(actual - near_blur_offset, 0.5)
		attrs.dof_blur_near_transition = near_blur_offset * 0.6
	moved.emit()


## The share of `offset` (0..1) the camera can travel from `from` before leaving the room.
func _room_limit(from: Vector3, offset: Vector3) -> float:
	if _room.size == Vector3.ZERO:
		return 1.0
	var t := 1.0
	for axis in 3:
		var d := offset[axis]
		if absf(d) < 0.0001:
			continue
		var edge := _room.end[axis] if d > 0.0 else _room.position[axis]
		var reach := (edge - from[axis]) / d
		if reach >= 0.0:
			t = minf(t, reach)
	return clampf(t, 0.05, 1.0)


func _clamp(p: Vector3) -> Vector3:
	if _bounds.size == Vector3.ZERO:
		return p
	return Vector3(clampf(p.x, _bounds.position.x, _bounds.end.x), 0.0, clampf(p.z, _bounds.position.z, _bounds.end.z))
