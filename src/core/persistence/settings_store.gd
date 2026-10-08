class_name SettingsStore
extends RefCounted

## The file the player's choices live in between sessions. The only thing that
## knows `settings.cfg` exists or that it is a `ConfigFile`. Callers hand over names
## and values; the meaning of a key, and any clamping beyond 0..1, stays with them.

const PATH := "user://settings.cfg"
const AUDIO_SECTION := "audio"


static func read_volume(key: String, fallback: float) -> float:
	var config := ConfigFile.new()
	if config.load(PATH) != OK:
		return fallback
	return clampf(float(config.get_value(AUDIO_SECTION, key, fallback)), 0.0, 1.0)


## Reads the file back first so writing one value never discards the others.
static func write_volume(key: String, value: float) -> void:
	var config := ConfigFile.new()
	config.load(PATH)
	config.set_value(AUDIO_SECTION, key, clampf(value, 0.0, 1.0))
	config.save(PATH)
