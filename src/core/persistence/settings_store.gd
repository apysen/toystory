class_name SettingsStore
extends RefCounted

## The file the player's choices live in between sessions. The only thing that
## knows `settings.cfg` exists or that it is a `ConfigFile`. Callers hand over names
## and values; the meaning of a key, and any clamping beyond 0..1, stays with them.

const PATH := "user://settings.cfg"
const AUDIO_SECTION := "audio"
const DISPLAY_SECTION := "display"
const GAMEPLAY_SECTION := "gameplay"


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


static func read_number(key: String, fallback: float) -> float:
	var config := ConfigFile.new()
	if config.load(PATH) != OK:
		return fallback
	return float(config.get_value(GAMEPLAY_SECTION, key, fallback))


static func write_number(key: String, value: float) -> void:
	var config := ConfigFile.new()
	config.load(PATH)
	config.set_value(GAMEPLAY_SECTION, key, value)
	config.save(PATH)


static func read_flag(key: String, fallback: bool) -> bool:
	var config := ConfigFile.new()
	if config.load(PATH) != OK:
		return fallback
	return bool(config.get_value(DISPLAY_SECTION, key, fallback))


static func write_flag(key: String, value: bool) -> void:
	var config := ConfigFile.new()
	config.load(PATH)
	config.set_value(DISPLAY_SECTION, key, value)
	config.save(PATH)
