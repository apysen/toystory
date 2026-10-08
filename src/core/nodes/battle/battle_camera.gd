class_name BattleCamera
extends Camera2D

## Scrolls and zooms over the battlefield: WASD/arrows or middle-drag to pan, the
## mouse wheel to zoom out. Clamped to the map plus room for the side panel.

@export_group("Controls")
@export var pan_speed := 900.0
@export var zoom_step := 0.25
@export var min_zoom := 0.5
@export var max_zoom := 1.0
## Seconds the camera takes to glide to a unit acting off screen.
@export var follow_seconds := 0.25

@export_group("Limits")
## Extra room around the map: left, top, right (side panel), bottom.
@export var margin_left := 48
@export var margin_top := 64
@export var margin_right := 372
@export var margin_bottom := 48

## Off while dialogue or results have the screen.
var input_enabled := true


## Fits the limits to the map and starts over `start`.
func frame_map(map: Rect2, start: Vector2) -> void:
	limit_left = int(map.position.x - margin_left)
	limit_top = int(map.position.y - margin_top)
	limit_right = int(map.end.x + margin_right)
	limit_bottom = int(map.end.y + margin_bottom)
	position = start
	make_current()
	pan(Vector2.ZERO)


func _process(dt: float) -> void:
	if not input_enabled:
		return
	var dir := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		dir.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		dir.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		dir.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		dir.y += 1
	if dir != Vector2.ZERO:
		pan(dir * pan_speed * dt / zoom.x)


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled:
		return
	if event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
		pan(-event.relative / zoom.x)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		set_zoom_level(zoom.x + (zoom_step if event.button_index == MOUSE_BUTTON_WHEEL_UP else -zoom_step))
		get_viewport().set_input_as_handled()


func set_zoom_level(z: float) -> void:
	z = clampf(z, min_zoom, max_zoom)
	zoom = Vector2(z, z)
	pan(Vector2.ZERO)


func pan(delta: Vector2) -> void:
	position += delta
	var half := get_viewport_rect().size / (2.0 * zoom.x)
	position.x = clampf(position.x, limit_left + half.x, maxf(limit_right - half.x, limit_left + half.x))
	position.y = clampf(position.y, limit_top + half.y, maxf(limit_bottom - half.y, limit_top + half.y))


func move_to(p: Vector2) -> void:
	position = p
	pan(Vector2.ZERO)


## Glides to `p` if it's off screen (enemy phase playback).
func follow(p: Vector2, tile_size: float) -> void:
	var half := get_viewport_rect().size / (2.0 * zoom.x)
	var view_rect := Rect2(position - half, half * 2).grow(-tile_size * 0.75)
	if view_rect.has_point(p):
		return
	var tw := create_tween()
	tw.tween_method(move_to, position, p, follow_seconds)
	await tw.finished
