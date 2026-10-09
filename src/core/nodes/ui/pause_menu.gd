class_name PauseMenu
extends Control

## The battle's pause overlay: Resume, the volume slider, Battle Speed, Fullscreen
## and Return to Missions.
##
## It shows and hides itself and reports what happened. What pausing means (which
## things stop) is the battle's business, so `BattleRoot` answers `opened` and
## `closed`, and decides what leaving the battle costs.

signal opened
signal closed
signal main_menu_requested

@export var resume_button: Button
@export var main_menu_button: Button
@export var fullscreen_button: Button
@export var battle_speed_button: Button
@export var volume_slider: HSlider
@export var volume_value: Label

## Shown in place of a percentage when the audio bus is missing.
@export var volume_unavailable_text := "Unavailable"
@export var fullscreen_on_text := "Fullscreen: On"
@export var fullscreen_off_text := "Fullscreen: Off"
## %s is the speed, e.g. "1.5".
@export var battle_speed_text := "Battle Speed: %sx"

var _audio: AudioSettings
var _display: DisplaySettings
var _speed: BattleSpeedSettings


func _ready() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_ALWAYS
	resume_button.pressed.connect(close)
	main_menu_button.pressed.connect(main_menu_requested.emit)
	fullscreen_button.pressed.connect(_toggle_fullscreen)
	battle_speed_button.pressed.connect(func() -> void: _speed.step_up())
	volume_slider.value_changed.connect(_on_volume_changed)


func setup(audio: AudioSettings, display: DisplaySettings, speed: BattleSpeedSettings) -> void:
	_audio = audio
	_display = display
	_speed = speed
	_display.changed.connect(_update_fullscreen_label)
	_update_fullscreen_label()
	_speed.changed.connect(_update_speed_label)
	_update_speed_label()
	var available := _audio.is_available()
	volume_slider.editable = available
	volume_slider.set_value_no_signal(_audio.volume() * 100.0 if available else 0.0)
	_update_label()


func is_open() -> bool:
	return visible


func open() -> void:
	if visible:
		return
	visible = true
	resume_button.grab_focus()
	opened.emit()


func close() -> void:
	if not visible:
		return
	visible = false
	closed.emit()


func _toggle_fullscreen() -> void:
	_display.set_fullscreen(not _display.is_fullscreen())


func _update_fullscreen_label() -> void:
	fullscreen_button.text = fullscreen_on_text if _display.is_fullscreen() else fullscreen_off_text


func _update_speed_label() -> void:
	battle_speed_button.text = battle_speed_text % String.num(_speed.speed(), 2)


func _on_volume_changed(value: float) -> void:
	_audio.set_volume(value / 100.0)
	_update_label()


func _update_label() -> void:
	if _audio == null or not _audio.is_available():
		volume_value.text = volume_unavailable_text
	else:
		volume_value.text = "%d%%" % roundi(volume_slider.value)


func _unhandled_input(event: InputEvent) -> void:
	if visible and (event.is_action_pressed("cancel") or event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause")):
		close()
		get_viewport().set_input_as_handled()
