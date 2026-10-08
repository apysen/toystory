class_name UnitView
extends Node2D
## Visual for one Unit: sprite (or graybox placeholder), base marker, HP bar.
## Positioned at the bottom-centre of the unit's footprint.

const COLORS := {
	Defs.Faction.PLAYER: Color("4f8fe0"),
	Defs.Faction.ENEMY: Color("e0574f"),
	Defs.Faction.NEUTRAL: Color("5fc46a"),
}

var unit: Unit
var sprite: AnimatedSprite2D
var _art: Variant = null
var shown_hp := 0
var _mundane: Sprite2D


func setup(u: Unit) -> void:
	unit = u
	shown_hp = u.hp
	_art = SpriteLib.load_unit(u.sprite)
	if _art == null and u.sprite != u.id:
		_art = SpriteLib.load_unit(u.id)
	if _art != null:
		sprite = AnimatedSprite2D.new()
		sprite.sprite_frames = _art.frames
		# Frames may differ in width (e.g. a wider hurt canvas), so re-mirror per animation.
		sprite.animation_changed.connect(apply_facing)
		sprite.centered = false
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		sprite.position = -_art.pivot
		var fsize := sprite.sprite_frames.get_frame_texture("idle", 0).get_size() if sprite.sprite_frames.has_animation("idle") else Vector2(128, 128)
		if u.is_large() and fsize.x < u.size * Defs.TILE_SIZE:
			# Undersized art for a Large unit: centre it on the footprint.
			sprite.position = Vector2(-fsize.x / 2.0, -fsize.y - Defs.TILE_SIZE * (u.size - 1) * 0.5)
		if sprite.sprite_frames.has_animation("idle"):
			sprite.play("idle")
		add_child(sprite)
	_base_x = sprite.position.x if sprite != null else 0.0
	apply_facing()
	queue_redraw()


var _base_x := 0.0
var _mundane_base_x := 0.0


## Mirrors the sprite around its foot pivot when the unit faces against the art.
func apply_facing() -> void:
	var flip: bool = _art != null and unit.facing != _art.get("faces", 1)
	if sprite != null:
		var w := sprite.sprite_frames.get_frame_texture(sprite.animation, 0).get_width()
		sprite.flip_h = flip
		sprite.position.x = -(w + _base_x) if flip else _base_x
	if _mundane != null:
		var mf: Variant = SpriteLib.load_mundane(unit.sprite)
		if mf == null:
			mf = SpriteLib.load_mundane(unit.id)
		flip = mf != null and unit.facing != mf.faces
		_mundane.flip_h = flip
		var mw := _mundane.texture.get_width()
		_mundane.position.x = -(mw + _mundane_base_x) if flip else _mundane_base_x


func refresh() -> void:
	var m: Variant = SpriteLib.load_mundane(unit.sprite) if unit.frozen else null
	if m == null and unit.frozen and unit.sprite != unit.id:
		m = SpriteLib.load_mundane(unit.id)
	if m != null and _mundane == null:
		_mundane = Sprite2D.new()
		_mundane.centered = false
		_mundane.texture = m.texture
		_mundane.position = -m.pivot
		_mundane_base_x = -m.pivot.x
		add_child(_mundane)
	if _mundane != null:
		_mundane.visible = unit.frozen
	apply_facing()
	if sprite != null:
		sprite.visible = not (unit.frozen and _mundane != null)
		# Without a mundane sprite, show the Gaze as a grey tint.
		sprite.modulate = Color(0.42, 0.42, 0.5) if unit.frozen and _mundane == null else Color.WHITE
	visible = not unit.broken
	queue_redraw()


## Plays a named animation once if the sprite has it, then returns to idle.
func has_anim(anim: String) -> bool:
	return sprite != null and sprite.sprite_frames.has_animation(anim)


func play_once(anim: String) -> void:
	if sprite == null or not sprite.sprite_frames.has_animation(anim):
		return
	sprite.sprite_frames.set_animation_loop(anim, false)
	sprite.play(anim)
	await sprite.animation_finished
	sprite.play("idle")


func set_moving(on: bool) -> void:
	if sprite == null:
		return
	if on and sprite.sprite_frames.has_animation("move"):
		sprite.play("move")
	elif sprite.sprite_frames.has_animation("idle"):
		sprite.play("idle")


func _process(_dt: float) -> void:
	pass


func _draw() -> void:
	if unit == null:
		return
	var w := unit.size * Defs.TILE_SIZE
	var col: Color = COLORS[unit.faction]
	if unit.pending_join:
		col = COLORS[Defs.Faction.NEUTRAL]
	# Base marker ellipse on the footprint.
	var base_r := Vector2(w * 0.38, w * 0.14)
	_draw_ellipse(Vector2(0, -6), base_r, Color(col, 0.55))
	if _art == null and not (unit.frozen and _mundane != null):
		# Graybox placeholder: a block with the unit's initials.
		var h := Defs.TILE_SIZE * (0.55 + 0.25 * unit.size)
		var rect := Rect2(-w * 0.32, -h - 6, w * 0.64, h)
		var body := col.darkened(0.15)
		if unit.frozen:
			body = Color(0.55, 0.55, 0.6)
		draw_rect(rect, body)
		draw_rect(rect, Color.BLACK, false, 2.0)
		var font := ThemeDB.fallback_font
		var label := _initials(unit.name)
		draw_string(font, Vector2(rect.position.x, rect.position.y + h * 0.6), label,
			HORIZONTAL_ALIGNMENT_CENTER, rect.size.x, 20, Color.WHITE)
	if unit.frozen and _mundane == null:
		draw_string(ThemeDB.fallback_font, Vector2(-w * 0.5, -12), "watched",
			HORIZONTAL_ALIGNMENT_CENTER, w, 12, Color("d8c8ff"))
	# HP bar under the feet.
	var bw := w * 0.7
	var bar := Rect2(-bw / 2, -2, bw, 6)
	draw_rect(bar, Color(0, 0, 0, 0.8))
	var frac := float(shown_hp) / unit.max_hp
	draw_rect(Rect2(bar.position, Vector2(bw * frac, 6)), col.lightened(0.2))
	if unit.status.has("pinned"):
		_badge(Vector2(bw / 2 + 2, -10), "P", Color("c0c0c0"))
	if unit.status.has("taped"):
		_badge(Vector2(bw / 2 + 2, -24), "T", Color("e0c050"))
	if unit.status.has("guard_beam") or unit.status.has("canopy") or unit.status.has("steady_sip"):
		_badge(Vector2(-bw / 2 - 14, -10), "+", Color("70d0ff"))
	if unit.status.has("heated"):
		_badge(Vector2(-bw / 2 - 14, -24), "H", Color("ff8040"))


func _badge(p: Vector2, s: String, c: Color) -> void:
	draw_rect(Rect2(p, Vector2(12, 12)), c)
	draw_string(ThemeDB.fallback_font, p + Vector2(2, 10), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color.BLACK)


func _draw_ellipse(c: Vector2, r: Vector2, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 24:
		var a := TAU * i / 24.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y))
	draw_colored_polygon(pts, color)


static func _initials(n: String) -> String:
	var parts := n.split(" ")
	if parts.size() == 1:
		return n.substr(0, 3)
	var s := ""
	for p in parts:
		s += p.substr(0, 1)
	return s
