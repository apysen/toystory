class_name EffectsLayer
extends Node2D

## Presentation-only effects over the board: sprite bursts, projectiles, floating
## numbers and the Gaze transformation puff. Nothing here feeds back into the rules;
## every node it spawns frees itself.

@export var effect_z_index := 50
@export var text_z_index := 100
@export var float_text_size := 20
## Pixels per second a projectile travels, clamped to a short flight.
@export var projectile_speed := 1400.0


## Plays a one-shot effect centred at `p`. Returns immediately.
func burst(effect: String, p: Vector2, flip := false, scale_by := 1.0) -> void:
	var sf := SpriteLib.load_vfx(effect)
	if sf == null:
		return
	var s := AnimatedSprite2D.new()
	s.sprite_frames = sf
	s.position = p
	s.flip_h = flip
	s.scale = Vector2(scale_by, scale_by)
	s.z_index = effect_z_index
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(s)
	s.play(sf.get_animation_names()[0])
	s.animation_finished.connect(s.queue_free)


## Flies a looping projectile sprite from a to b (no-op without art).
func projectile(effect: String, a: Vector2, b: Vector2) -> void:
	var sf := SpriteLib.load_vfx(effect)
	if sf == null:
		return
	var s := AnimatedSprite2D.new()
	s.sprite_frames = sf
	s.position = a
	s.flip_h = b.x < a.x
	s.z_index = effect_z_index
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(s)
	var anim: String = sf.get_animation_names()[0]
	sf.set_animation_loop(anim, true)
	s.play(anim)
	var tw := create_tween()
	tw.tween_property(s, "position", b, clampf(a.distance_to(b) / projectile_speed, 0.08, 0.3))
	await tw.finished
	s.queue_free()


func float_text(p: Vector2, text: String, c: Color) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", float_text_size)
	l.add_theme_color_override("font_color", c)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 5)
	l.position = p - Vector2(20, 0)
	l.z_index = text_z_index
	add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "position:y", p.y - 30, 0.6)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.3)
	tw.tween_callback(l.queue_free)


## Squash-and-flash used for the Gaze transformation in both directions. A unit
## being watched first squashes down ("gaze_in"); the view swaps to its new form at
## the flash and springs back out ("gaze_out") when the human looks away.
func gaze_poof(v: UnitView) -> void:
	if v.unit.frozen and v.has_anim("gaze_in"):
		await v.play_once("gaze_in", false)
	# The puff is sized for 128px units; doubled to cover Large ones.
	var big := v.unit.is_large()
	burst("gaze_poof", v.position + Vector2(0, -112 if big else -56), false, 2.0 if big else 1.0)
	var tw := create_tween()
	tw.tween_property(v, "scale", Vector2(1.25, 0.7), 0.07)
	tw.tween_property(v, "modulate", Color(2, 2, 2), 0.05)
	tw.tween_callback(v.play_transform)
	tw.tween_property(v, "scale", Vector2.ONE, 0.1)
	tw.parallel().tween_property(v, "modulate", Color.WHITE, 0.15)
