class_name UnitCard
extends Node3D

## One unit in the diorama: its pixel-art sprite on a camera-facing card, a shadow
## caster, a silhouette that shows it through furniture, and a faction ring on the
## floor. Plays the sprite's animations, swaps to its object form under a Human
## Gaze, and mirrors to face its last direction of travel relative to the camera.
##
## A unit with a 3D model (UnitModel.MODELS) shows the model instead of the sprite
## card: the same calls play the model's clips, and it turns to face its heading.
## The Gaze object form is still a sprite card.
##
## The node's position is the unit's feet. It never changes the Unit it shows.

const CARD_SHADER := preload("res://assets/shaders/unit_card.gdshader")
const SHADOW_SHADER := preload("res://assets/shaders/unit_card_shadow.gdshader")
const SILHOUETTE_SHADER := preload("res://assets/shaders/unit_card_silhouette.gdshader")

const FACTION_COLORS := {
	Defs.Faction.PLAYER: Color("4f9be8"),
	Defs.Faction.ENEMY: Color("e8574f"),
	Defs.Faction.NEUTRAL: Color("5fc46a"),
}

signal animation_done(anim: String)
## A floating model's feet leave or touch the floor (UnitModel.kicked_dust).
signal kicked_dust(at: Vector3)

## How far the card leans back toward the camera (see unit_card.gdshaderinc).
@export_range(0.0, 1.0) var lean := 0.75

var unit: Unit
var shown_hp := 0
## Last direction of travel in the world; decides which way the card is mirrored.
var heading := Vector3.RIGHT

var _art: Variant = null
var _mundane: Variant = null
var _frames: SpriteFrames
var _anim := "idle"
var _loop := true
var _return_to_idle := true
var _time := 0.0
var _frame := -1
var _flip := false
var _card: MeshInstance3D
var _shadow: MeshInstance3D
var _silhouette: MeshInstance3D
var _ring: MeshInstance3D
var _materials: Array[ShaderMaterial] = []
var _showing_object := false
var _model: UnitModel
## Set while the model stands guard away from its spot (Watchful).
var _guarding := false
## A hit the guard clip already showed landing; its damage skips the flinch.
var absorbed_hit := false
## Whether the card shows the unit as watched by a human. Follows playback (the
## Gaze events), not the rules' end state, so a unit isn't turned into its object
## before the strikes that happened earlier have been shown.
var shows_frozen := false


func setup(u: Unit) -> void:
	unit = u
	shown_hp = u.hp
	heading = Vector3(float(u.facing), 0, 0)
	_art = SpriteLib.load_unit(u.sprite)
	if _art == null and u.sprite != u.id:
		_art = SpriteLib.load_unit(u.id)
	_mundane = SpriteLib.load_mundane(u.sprite)
	if _mundane == null:
		_mundane = SpriteLib.load_mundane(u.id)
	_frames = _art.frames if _art != null else null
	shows_frozen = u.frozen
	_build()
	_model = UnitModel.for_unit(u)
	if _model != null:
		add_child(_model)
		_model.heading = heading
		_model.face_now()
		_model.animation_done.connect(_emit_done)
		_model.kicked_dust.connect(kicked_dust.emit)
	position = BattleSpace.to_world(u.pos)
	refresh()


func _build() -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	# Vertices are placed in the shader; give culling a box that covers any frame.
	var big := unit.size * 2.2
	quad.custom_aabb = AABB(Vector3(-big, -0.2, -big), Vector3(big * 2, big * 1.6, big * 2))
	_card = _mesh("Card", quad, CARD_SHADER, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
	_shadow = _mesh("ShadowCaster", quad, SHADOW_SHADER, GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY)
	_silhouette = _mesh("Silhouette", quad, SILHOUETTE_SHADER, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
	_silhouette.material_override.render_priority = 10
	var anchor := 0.35 if unit.size == 1 else 0.8
	for m in _materials:
		# The shadow caster stays upright so the shadow keeps the figure's height.
		m.set_shader_parameter("lean", 0.0 if m == _shadow.material_override else lean)
		m.set_shader_parameter("pixels_per_metre", BattleSpace.PIXELS_PER_METRE)
		m.set_shader_parameter("anchor_height", anchor)
		m.set_shader_parameter("anchor_toward_camera", unit.radius + 0.1)
	var col: Color = FACTION_COLORS[unit.faction]
	_silhouette.set_instance_shader_parameter("silhouette_color", Color(col, 0.55))
	# Faction ring on the floor.
	_ring = MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = unit.radius * 0.82
	torus.outer_radius = unit.radius * 1.05
	torus.rings = 32
	_ring.mesh = torus
	_ring.scale = Vector3(1, 0.05, 1)
	_ring.position.y = 0.03
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_color = Color(col, 0.75)
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_ring.material_override = rm
	_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_ring)


func _mesh(n: String, quad: QuadMesh, shader: Shader, shadows: int) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	m.name = n
	m.mesh = quad
	var mat := ShaderMaterial.new()
	mat.shader = shader
	m.material_override = mat
	m.cast_shadow = shadows
	add_child(m)
	_materials.append(mat)
	return m


func _process(delta: float) -> void:
	if unit == null:
		return
	_time += delta
	_update_frame(false)
	_update_flip()


## Re-reads the unit: faction colour and Broken; shows the Gaze form per `shows_frozen`.
func refresh() -> void:
	var col: Color = FACTION_COLORS[Defs.Faction.NEUTRAL if unit.pending_join else unit.faction]
	(_ring.material_override as StandardMaterial3D).albedo_color = Color(col, 0.75)
	_silhouette.set_instance_shader_parameter("silhouette_color", Color(col, 0.55))
	_showing_object = shows_frozen and _mundane != null
	if _showing_object and not _loop:
		# A one-shot can't finish on an object; release whoever is waiting for it.
		_loop = true
		_anim = "idle"
		_emit_done.call_deferred("")
	var grey := shows_frozen and _mundane == null
	_set_param("tint", Color(0.5, 0.5, 0.58) if grey else Color.WHITE)
	_ring.visible = not shows_frozen
	visible = not unit.broken
	if _model != null:
		# The model stands in for the sprite; the object form stays a card.
		_model.visible = not _showing_object
		for m in [_card, _shadow, _silhouette]:
			m.visible = _showing_object
		if _model.fire() != null:
			_model.fire().hot = unit.status.has("heated")  # Hot Coils: the vents smoulder
	_frame = -1
	_update_frame(true)


func has_anim(anim: String) -> bool:
	if _model != null:
		return _model.has_anim(anim)
	return _frames != null and _frames.has_animation(anim)


## Starts a looping animation ("idle", "move").
func play(anim: String) -> void:
	if not has_anim(anim):
		anim = "idle"
	if _model != null:
		_model.play(anim)
		return
	if anim == _anim and _loop:
		return
	_anim = anim
	_loop = true
	_time = 0.0
	_frame = -1


## Plays an animation once, then returns to idle unless `return_to_idle` is false
## (the Broken transition holds its last frame).
func play_once(anim: String, return_to_idle := true) -> void:
	if not has_anim(anim) or _showing_object or not visible:
		return
	if _model != null:
		_model.play(anim, return_to_idle)
		while await animation_done != anim:
			pass
		return
	_anim = anim
	_loop = false
	_return_to_idle = return_to_idle
	_time = 0.0
	_frame = -1
	await animation_done


## Seconds into `anim` at which its strike connects, or NAN when the unit has no
## timed clip (sprite cards: the hit follows the whole animation and a lunge).
func contact_time(anim: String) -> float:
	return _model.event_time(anim, "hit") if _model != null else NAN


## Seconds into an Art's own clip at which `event` happens (Flashbulb's "flash"),
## or NAN when the unit has no such clip.
func art_time(art_id: String, event: String) -> float:
	return _model.event_time(art_id, event) if _model != null else NAN


## A point on one of the model's bones, `offset` in the bone's frame (Y runs down
## it): the lamp's "head" and "lantern", Stapler's "gun_R" and "gun_L". A point
## `fallback_height` above the card when there is no model or no such bone.
func bone_point(bone: String, fallback_height: float, offset := Vector3.ZERO) -> Vector3:
	var p := _model.bone_position(bone, offset) if _model != null else Vector3.INF
	return p if p != Vector3.INF else global_position + Vector3(0, fallback_height, 0)


## The fire burning on the model (the Toaster's palms and vents), or null.
func fire() -> UnitFire:
	return _model.fire() if _model != null else null


## The tea in the model's cup (the Teacup's), or null.
func tea() -> UnitTea:
	return _model.tea() if _model != null else null


## Hides or browns one of the Toaster's toast slices ("front", "back"); see
## UnitModel.set_slice. Does nothing without a model.
func set_slice(slot: String, hidden: bool, brown := -1.0) -> void:
	if _model != null:
		_model.set_slice(slot, hidden, brown)


## Whether one of the Toaster's slices is hidden (launched and not back yet).
func slice_hidden(slot: String) -> bool:
	return _model != null and _model.slice_hidden(slot)


## Brings the model's glow from `from` to `to` over `seconds` (Overheat's vents
## building to white-hot).
func ramp_glow(from: float, to: float, seconds: float) -> void:
	if _model == null:
		return
	var tw := create_tween()
	tw.tween_method(_model.set_glow, from, to, seconds)


## Flares the model's glow to `peak` and lets it die back over `seconds`.
func flare_glow(peak: float, seconds: float) -> void:
	if _model == null:
		return
	var tw := create_tween()
	tw.tween_method(_model.set_glow, peak, 1.0, seconds).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)


## Plays the clip for one of the unit's Arts: its own clip when the art has one
## (the model's "spotlight"), otherwise the shared "art".
func play_art(art_id: String) -> void:
	await play_once(art_id if has_anim(art_id) else "art")


## Took damage; shows the flinch unless the guard clip already showed the hit.
func play_hurt() -> void:
	if absorbed_hit:
		absorbed_hit = false
		return
	if has_anim("hurt"):
		play_once("hurt")


func set_moving(on: bool) -> void:
	play("move" if on else "idle")


## Seconds the model's clip runs, or 0 without one.
func clip_length(anim: String) -> float:
	return _model.clip_length(anim) if _model != null else 0.0


## A floating model (Umbrella) lands now instead of hovering on; nothing otherwise.
func land_now() -> void:
	if _model != null:
		_model.land_now()


## Whether the unit's model is off the floor, floating.
func is_aloft() -> bool:
	return _model != null and _model.is_aloft()


## Points the card along a direction of travel on the floor.
func face_along(d: Vector2) -> void:
	if d.length() > 0.001:
		heading = BattleSpace.dir_to_world(d).normalized()
		if _model != null:
			_model.heading = heading


## Watchful, shown on a model that has the clips: sprints in front of `ally_at`
## toward `attacker_at` (world positions), turns to face the attacker and raises
## the shield. Returns once it is in place; `stand_down` walks it back home.
## Sprite-only units have no such clips and are left where they are.
func intercept(ally_at: Vector3, attacker_at: Vector3) -> void:
	if _model == null or not _model.has_anim("intercept_run") or _showing_object:
		return
	var to_attacker := attacker_at - ally_at
	to_attacker.y = 0.0
	var spot := ally_at + to_attacker.normalized() * (unit.radius * 2.0 + 0.05)
	face_along(BattleSpace.to_floor(spot - global_position))
	_guarding = true
	_model.play("intercept_run", false)
	var tw := create_tween()
	tw.tween_property(self, "global_position", spot, _model.clip_length("intercept_run"))
	await tw.finished
	face_along(BattleSpace.to_floor(attacker_at - spot))
	var brace := _model.event_time("intercept_guard", "brace")
	if is_nan(brace):
		_model.play("intercept_guard", false)
	else:
		_model.hold("intercept_guard", brace)  # braced, waiting for the blow


## The blow lands on a Watchful guard: the guard clip carries on so its impact
## jolt lands on this frame.
func take_guarded_hit() -> void:
	if not _guarding or _model == null:
		return
	var impact := _model.event_time("intercept_guard", "impact")
	if not is_nan(impact):
		_model.resume_from(maxf(impact - 0.02, 0.0))


## After a Watchful intercept: walks back to the unit's own spot and faces
## `look_at` again.
func stand_down(look_at: Vector3) -> void:
	if not _guarding:
		return
	_guarding = false
	var home := BattleSpace.to_world(unit.pos)
	face_along(BattleSpace.to_floor(home - global_position))
	play("move")
	var tw := create_tween()
	tw.tween_property(self, "position", home, maxf(global_position.distance_to(home) / 3.5, 0.05))
	await tw.finished
	face_along(BattleSpace.to_floor(look_at - global_position))
	play("idle")


## Broken transition: the "broken" animation when the art has one, then a fade out.
func play_broken() -> void:
	if _model != null:
		_model.go_cold()
	if has_anim("broken"):
		await play_once("broken", false)
	var tw := create_tween()
	if _model != null:
		tw.tween_method(_model.set_opacity, 1.0, 0.0, 0.4)
	else:
		tw.tween_method(func(v: float) -> void: _set_param("fade", v), 1.0, 0.0, 0.4)
	await tw.finished
	refresh()


## Squashes down before the Gaze puff turns the unit into its object.
func play_gaze_in() -> void:
	if has_anim("gaze_in") and not shows_frozen:
		await play_once("gaze_in", false)


## Called at the flash of the Gaze puff: swaps to the object form, or springs
## back out of it when the human looks away.
func play_transform(to_object: bool) -> void:
	shows_frozen = to_object
	refresh()
	if not to_object and has_anim("gaze_out"):
		play_once("gaze_out")
	elif to_object and _model != null:
		_model.play("idle")  # ready for when it springs back out


func _update_frame(force: bool) -> void:
	if _showing_object:
		if force:
			var tex: Texture2D = _mundane.texture
			_show_texture(tex, Rect2(Vector2.ZERO, tex.get_size()), _mundane.pivot)
		return
	if _model != null or _frames == null or not _frames.has_animation(_anim):
		return
	var count := _frames.get_frame_count(_anim)
	var fps := _frames.get_animation_speed(_anim)
	var total := 0.0
	for i in count:
		total += _frames.get_frame_duration(_anim, i) / fps
	var t := _time
	if _loop:
		t = fposmod(t, maxf(total, 0.001))
	elif t >= total:
		var finished := _anim
		if _return_to_idle and has_anim("idle"):
			_anim = "idle"
			_loop = true
			_time = 0.0
			t = 0.0
		else:
			t = total - 0.0001
		_emit_done.call_deferred(finished)
	var f := 0
	var acc := 0.0
	for i in count:
		acc += _frames.get_frame_duration(_anim, i) / fps
		if t < acc:
			f = i
			break
	if f == _frame and not force:
		return
	_frame = f
	var tex := _frames.get_frame_texture(_anim, f)
	if tex is AtlasTexture:
		_show_texture(tex.atlas, tex.region, _art.pivot)
	else:
		_show_texture(tex, Rect2(Vector2.ZERO, tex.get_size()), _art.pivot)


func _emit_done(anim: String) -> void:
	animation_done.emit(anim)


func _show_texture(tex: Texture2D, region: Rect2, pivot: Vector2) -> void:
	for m in _materials:
		if m.get_shader_parameter("sheet") != tex:
			m.set_shader_parameter("sheet", tex)
	_set_param("region", Vector4(region.position.x, region.position.y, region.size.x, region.size.y))
	_set_param("pivot", pivot)


## Mirrors the card when the unit's heading points the other way from its art,
## as seen from the current camera. A heading straight along the view keeps the
## last choice so the card doesn't flicker.
func _update_flip() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var right := cam.global_transform.basis.x
	right.y = 0.0
	var side := heading.dot(right.normalized())
	if absf(side) < 0.15:
		return
	var native: int = _art.get("faces", 1) if _art != null else 1
	if _showing_object and _mundane != null:
		native = _mundane.faces
	var flip := (1 if side > 0 else -1) != native
	if flip != _flip:
		_flip = flip
		_set_param("flip", 1.0 if flip else 0.0)


func _set_param(p: String, v: Variant) -> void:
	for m in [_card, _shadow, _silhouette]:
		if m != null:
			m.set_instance_shader_parameter(p, v)
