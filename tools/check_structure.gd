extends SceneTree

## Fails when a directory exists that `docs/project_structure.md` does not describe.
##
## The document is a target: some of the tree it draws has not been built yet, so it
## cannot be checked by asking whether everything in it is on disk. The direction that
## can be enforced is the other one: nothing should exist that the document does not
## describe. A folder nobody wrote a line for is a decision nobody recorded.
##
## Scanned: `src`, `scenes`, `data`, `tests`, `tools`, `scripts` - the folders that hold
## code and composition. `assets/` is left out: it is imported art organised by
## whoever exports it.
##
## Run: godot --headless --path . --script res://tools/check_structure.gd

const DOCUMENT := "res://docs/project_structure.md"
const SCANNED_ROOTS := ["res://src", "res://scenes", "res://data", "res://tests", "res://tools", "res://scripts"]
## Godot's own import cache and anything a tool drops beside it. Not source.
const IGNORED := [".godot", ".import"]


func _initialize() -> void:
	var described := _described_names()
	if described.is_empty():
		push_error("STRUCTURE: %s has no layout block to check against" % DOCUMENT)
		quit(1)
		return
	var undescribed := PackedStringArray()
	for root in SCANNED_ROOTS:
		for path in _directories(root):
			var name := path.get_file()
			if not described.has(name):
				undescribed.append(path)
	for path in undescribed:
		push_error(
			"UNDESCRIBED: %s exists and docs/project_structure.md does not say what belongs in it"
				% path
		)
	if undescribed.is_empty():
		print("STRUCTURE: PASS (every source directory is described)")
	else:
		print("STRUCTURE: FAIL (%d)" % undescribed.size())
	quit(0 if undescribed.is_empty() else 1)


## Every folder name the layout block names, as a set.
##
## Matched by name rather than by full path on purpose. The document draws one tree and
## the same name means the same thing wherever it appears - `progression/` under
## `models`, `nodes` and `rules` is one line of intent each - and a check that demanded
## exact paths would fail on a folder that moved to a correct new home before anyone
## had rewritten the tree around it. What is being caught is a name nobody described at
## all, which is the case that hides a decision.
func _described_names() -> Dictionary:
	var file := FileAccess.open(DOCUMENT, FileAccess.READ)
	if file == null:
		return {}
	var names := {}
	var inside_block := false
	while not file.eof_reached():
		var line := file.get_line()
		if line.begins_with("```"):
			# The layout block is the first fenced block in the document.
			if inside_block:
				break
			inside_block = line.contains("text")
			continue
		if not inside_block:
			continue
		var stripped := line.strip_edges()
		var space := stripped.find(" ")
		var entry := stripped.substr(0, space) if space > 0 else stripped
		if not entry.ends_with("/"):
			continue
		for segment in entry.trim_suffix("/").split("/"):
			if not segment.is_empty():
				names[segment] = true
	file.close()
	return names


func _directories(root: String) -> PackedStringArray:
	var found := PackedStringArray()
	var directory := DirAccess.open(root)
	if directory == null:
		return found
	directory.list_dir_begin()
	var entry := directory.get_next()
	while entry != "":
		if directory.current_is_dir() and not IGNORED.has(entry):
			var path := "%s/%s" % [root, entry]
			found.append(path)
			found.append_array(_directories(path))
		entry = directory.get_next()
	directory.list_dir_end()
	return found
