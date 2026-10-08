class_name DisplaySettings
extends Node

## Windowed or fullscreen, remembered between sessions. Applies the saved choice
## as soon as it enters the tree, and F11 toggles it from anywhere.

signal changed

const FULLSCREEN_KEY := "fullscreen"

## Window mode used for fullscreen: borderless fullscreen switches instantly and
## keeps alt-tab painless; exclusive can be chosen here instead.
@export var fullscreen_mode := DisplayServer.WINDOW_MODE_FULLSCREEN
## Fullscreen on the very first run, before anything is saved.
@export var default_fullscreen := false


func _ready() -> void:
	_apply(SettingsStore.read_flag(FULLSCREEN_KEY, default_fullscreen))


func is_fullscreen() -> bool:
	var mode := DisplayServer.window_get_mode()
	return mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN


func set_fullscreen(on: bool) -> void:
	_apply(on)
	SettingsStore.write_flag(FULLSCREEN_KEY, on)


func _apply(on: bool) -> void:
	# Headless runs (tests, tools) have no window to resize.
	if DisplayServer.get_name() == "headless":
		return
	if on != is_fullscreen():
		DisplayServer.window_set_mode(fullscreen_mode if on else DisplayServer.WINDOW_MODE_WINDOWED)
	changed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F11:
		set_fullscreen(not is_fullscreen())
		get_viewport().set_input_as_handled()
