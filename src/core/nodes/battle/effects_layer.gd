class_name EffectsLayer
extends Node3D

## Presentation-only effects in the diorama: pixel-art bursts and projectiles on
## camera-facing sprites, floating damage numbers, and the Gaze transformation
## puff. Nothing here feeds back into the rules; everything it spawns frees itself.

@export var float_text_size := 56
@export var float_text_pixel_size := 0.006
## Metres per second a projectile travels, clamped to a short flight.
@export var projectile_speed := 11.0


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
func gaze_poof(card: UnitCard) -> void:
	if card.unit.frozen:
		await card.play_gaze_in()
	var big := card.unit.is_large()
	burst("gaze_poof", card.global_position + Vector3(0, 0.9 if big else 0.45, 0), 2.0 if big else 1.0)
	var tw := create_tween()
	tw.tween_property(card, "scale", Vector3(1.25, 0.7, 1.25), 0.07)
	tw.tween_callback(card.play_transform)
	tw.tween_property(card, "scale", Vector3.ONE, 0.12)


func _sprite(sf: SpriteFrames) -> AnimatedSprite3D:
	var s := AnimatedSprite3D.new()
	s.sprite_frames = sf
	s.pixel_size = 1.0 / BattleSpace.PIXELS_PER_METRE
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	s.shaded = false
	s.no_depth_test = true
	s.render_priority = 15
	return s
