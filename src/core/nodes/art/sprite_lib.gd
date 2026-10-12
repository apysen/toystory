class_name SpriteLib
extends RefCounted
## Loads character art from assets/sprites when present. Returns null when a
## sprite is missing so callers can draw a graybox placeholder instead.
##
## Animated: assets/sprites/<group>/<name>/<name>_sheet.png + _sheet.json
##   (Aseprite "hash" export with frameTags).
## Static:   assets/sprites/<group>/<name>/<name>.png
## Pivot:    <name>_meta.json "foot_pivot": [x, y] (pixel under the feet).

const GROUPS := ["player", "enemies"]
## Art drawn facing left (from the Aseprite pass). Everything else faces right.
const NATIVE_LEFT := ["lamp"]

static var _cache := {}


## {frames: SpriteFrames, pivot: Vector2} or null.
static func load_unit(name: String) -> Variant:
	if _cache.has(name):
		return _cache[name]
	var result: Variant = null
	for g in GROUPS:
		var dir := "res://assets/sprites/%s/%s/" % [g, name]
		var frames := _load_sheet(dir, name)
		if frames == null:
			frames = _load_static(dir, name)
		if frames != null:
			_add_drafts(frames, name)
			result = {"frames": frames, "pivot": _load_pivot(dir, name), "faces": _load_native_facing(dir, name)}
			break
	_cache[name] = result
	return result


## One-shot effect sheet: assets/sprites/vfx/<name>/<name>_sheet.* (SpriteFrames or null).
## A sheet drawn smooth at several times the battle's pixel density (vector art such
## as tools/draw_vfx.py draws, its JSON meta "scale" above 1) carries that
## density as the SpriteFrames' "density" meta, so it is shown smoothly at its size.
static func load_vfx(name: String) -> SpriteFrames:
	var key := "vfx:" + name
	if not _cache.has(key):
		var dir := "res://assets/sprites/vfx/%s/" % name
		var sf := _load_sheet(dir, name)
		if sf != null:
			for a in sf.get_animation_names():
				sf.set_animation_loop(a, false)
			var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(dir + name + "_sheet.json"))
			var density := float(String(data.get("meta", {}).get("scale", "1"))) if data is Dictionary else 1.0
			sf.set_meta("density", maxf(density, 1.0))
		_cache[key] = sf
	return _cache[key]


## Mundane (Human Gaze) form: assets/sprites/mundane/<name>.png. {texture, pivot} or null.
static func load_mundane(name: String) -> Variant:
	var key := "mundane:" + name
	if _cache.has(key):
		return _cache[key]
	var dir := "res://assets/sprites/mundane/"
	var tex := _texture(dir + name + ".png")
	var result: Variant = null
	if tex != null:
		result = {"texture": tex, "pivot": _load_pivot(dir, name), "faces": _load_native_facing(dir, name)}
	_cache[key] = result
	return result


## UI icon: assets/sprites/ui/<name>.png, or null so callers draw a fallback.
static func load_ui(name: String) -> Texture2D:
	var key := "ui:" + name
	if not _cache.has(key):
		_cache[key] = _texture("res://assets/sprites/ui/%s.png" % name)
	return _cache[key]


static func _texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		return load(path)
	var abs_path := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return null
	var img := Image.load_from_file(abs_path)
	if img == null:
		return null
	return ImageTexture.create_from_image(img)


## Draft animations awaiting review live in assets/sprites/drafts/<name>_<anim>/.
## They're used in game until a final version lands in the main sheet.
const DRAFT_ANIMS := ["move", "attack", "art", "hurt", "broken", "gaze_in", "gaze_out"]


static func _add_drafts(sf: SpriteFrames, name: String) -> void:
	for anim in DRAFT_ANIMS:
		if sf.has_animation(anim):
			continue
		var base := "%s_%s" % [name, anim]
		_load_sheet("res://assets/sprites/drafts/%s/" % base, base, sf, name)


static func _load_sheet(dir: String, name: String, into: SpriteFrames = null, prefix := "") -> SpriteFrames:
	var json_path := dir + name + "_sheet.json"
	if not FileAccess.file_exists(json_path):
		return null
	var tex := _texture(dir + name + "_sheet.png")
	if tex == null:
		return null
	if prefix == "":
		prefix = name
	var data = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(data) != TYPE_DICTIONARY or not data.has("frames"):
		return null
	var frame_list: Array = []
	if typeof(data.frames) == TYPE_DICTIONARY:
		for k in data.frames:
			frame_list.append(data.frames[k])
	else:
		frame_list = data.frames
	var sf := into
	if sf == null:
		sf = SpriteFrames.new()
		sf.remove_animation("default")
	var tags: Array = data.get("meta", {}).get("frameTags", [])
	if tags.is_empty():
		tags = [{"name": "idle", "from": 0, "to": frame_list.size() - 1}]
	for tag in tags:
		# Tags may be prefixed with the sprite name ("lamp_idle" -> "idle").
		var anim: String = tag.name.trim_prefix(prefix + "_")
		if sf.has_animation(anim):
			continue
		sf.add_animation(anim)
		sf.set_animation_loop(anim, true)
		var first_ms := 100.0
		for i in range(int(tag.from), int(tag.to) + 1):
			var f: Dictionary = frame_list[i]
			var r: Dictionary = f.frame
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(r.x, r.y, r.w, r.h)
			var ms := float(f.get("duration", 100))
			if i == int(tag.from):
				first_ms = ms
			sf.add_frame(anim, at, ms / first_ms)
		sf.set_animation_speed(anim, 1000.0 / first_ms)
	return sf


static func _load_static(dir: String, name: String) -> SpriteFrames:
	var tex := _texture(dir + name + ".png")
	if tex == null:
		return null
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	sf.add_animation("idle")
	sf.add_frame("idle", tex)
	return sf


## Which way the art faces as drawn: meta "faces": "left" | "right" (default right).
static func _load_native_facing(dir: String, name: String) -> int:
	var path := dir + name + "_meta.json"
	if FileAccess.file_exists(path):
		var data = JSON.parse_string(FileAccess.get_file_as_string(path))
		if typeof(data) == TYPE_DICTIONARY:
			var f: String = data.get("faces", data.get("base_facing", ""))
			if f == "left":
				return -1
			if f == "right":
				return 1
	return -1 if name in NATIVE_LEFT else 1


static func _load_pivot(dir: String, name: String) -> Vector2:
	var path := dir + name + "_meta.json"
	if FileAccess.file_exists(path):
		var data = JSON.parse_string(FileAccess.get_file_as_string(path))
		if typeof(data) == TYPE_DICTIONARY and data.has("foot_pivot"):
			return Vector2(data.foot_pivot[0], data.foot_pivot[1])
	return Vector2(64, 120)
