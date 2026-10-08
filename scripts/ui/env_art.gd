class_name EnvArt
extends RefCounted
## Loads map art from assets/sprites/environment (props.json schema written by
## the Aseprite pass). Missing files leave the graybox look in place.

const DIR := "res://assets/sprites/environment/"


## {"floor": Texture2D?, "props": {kind: {frames: Array[Texture2D], tags, offset: Vector2}},
##  "variants": {Vector2i: tag}}
static func load_all() -> Dictionary:
	var out := {"floor": SpriteLib._texture(DIR + "under_the_desk_floor.png"), "props": {}, "variants": {}}
	var path := DIR + "props.json"
	if not FileAccess.file_exists(path):
		return out
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY:
		return out
	for kind in data:
		if kind.begins_with("_") or kind == "floor":
			continue
		var p: Dictionary = data[kind]
		var tex := SpriteLib._texture(DIR + p.image)
		if tex == null:
			continue
		var cw: int = p.canvas[0]
		var ch: int = p.canvas[1]
		var frames: Array[Texture2D] = []
		for i in int(p.get("frames", 1)):
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(i * cw, 0, cw, ch)
			frames.append(at)
		out.props[kind] = {
			"frames": frames,
			"tags": p.get("tags", {}),
			"offset": Vector2(p.footprint_bottom_left_px[0], p.footprint_bottom_left_px[1]),
			"tiles": p.get("tiles", []),
		}
	var placements: Dictionary = data.get("_placements", {})
	for kind in placements:
		for entry in placements[kind]:
			if entry.size() >= 3:
				out.variants[Vector2i(entry[0], entry[1])] = entry[2]
	return out


static func frame(env: Dictionary, kind: String, tag := "") -> Texture2D:
	if not env.props.has(kind):
		return null
	var p: Dictionary = env.props[kind]
	var i := 0
	if tag != "" and p.tags.has(tag):
		i = int(p.tags[tag][0])
	return p.frames[i]


static func spill_frame(env: Dictionary, t: Vector2i) -> Texture2D:
	if not env.props.has("spill"):
		return null
	var p: Dictionary = env.props.spill
	for i in p.tiles.size():
		if Vector2i(p.tiles[i][0], p.tiles[i][1]) == t:
			return p.frames[i]
	return p.frames[0]


static func offset(env: Dictionary, kind: String) -> Vector2:
	return env.props[kind].offset if env.props.has(kind) else Vector2.ZERO
