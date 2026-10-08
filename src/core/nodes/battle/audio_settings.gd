class_name AudioSettings
extends Node

## The player's volume: which bus the pause-menu slider drives, how loud 100% is,
## and the saved choice. Applies the saved volume as soon as it enters the tree, so
## a battle starts at the level the player last picked.

const VOLUME_KEY := "master_volume"

## AudioServer bus the volume slider drives.
@export var bus_name: StringName = &"Master"
## Linear output reached when the slider shows 100%.
@export_range(0.0, 1.0, 0.01) var max_linear_volume := 1.0
## Slider position on the very first run, before anything is saved.
@export_range(0.0, 1.0, 0.01) var default_volume := 0.8


func _ready() -> void:
	_apply(volume())


## The slider position, 0..1.
func volume() -> float:
	return SettingsStore.read_volume(VOLUME_KEY, default_volume)


func set_volume(value: float) -> void:
	value = clampf(value, 0.0, 1.0)
	_apply(value)
	SettingsStore.write_volume(VOLUME_KEY, value)


func is_available() -> bool:
	return AudioServer.get_bus_index(bus_name) >= 0


func _apply(value: float) -> void:
	var bus := AudioServer.get_bus_index(bus_name)
	if bus < 0:
		return
	var linear := value * max_linear_volume
	AudioServer.set_bus_mute(bus, linear <= 0.0)
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(linear, 0.0001)))
