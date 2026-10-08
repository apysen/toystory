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
			result = {"frames": frames, "pivot": _load_pivot(dir, name)}
			break
	_cache[name] = result
	return result


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


static func _load_sheet(dir: String, name: String) -> SpriteFrames:
	var json_path := dir + name + "_sheet.json"
	if not FileAccess.file_exists(json_path):
		return null
	var tex := _texture(dir + name + "_sheet.png")
	if tex == null:
		return null
	var data = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(data) != TYPE_DICTIONARY or not data.has("frames"):
		return null
	var frame_list: Array = []
	if typeof(data.frames) == TYPE_DICTIONARY:
		for k in data.frames:
			frame_list.append(data.frames[k])
	else:
		frame_list = data.frames
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	var tags: Array = data.get("meta", {}).get("frameTags", [])
	if tags.is_empty():
		tags = [{"name": "idle", "from": 0, "to": frame_list.size() - 1}]
	for tag in tags:
		var anim: String = tag.name
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


static func _load_pivot(dir: String, name: String) -> Vector2:
	var path := dir + name + "_meta.json"
	if FileAccess.file_exists(path):
		var data = JSON.parse_string(FileAccess.get_file_as_string(path))
		if typeof(data) == TYPE_DICTIONARY and data.has("foot_pivot"):
			return Vector2(data.foot_pivot[0], data.foot_pivot[1])
	return Vector2(64, 120)
