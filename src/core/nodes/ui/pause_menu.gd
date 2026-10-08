class_name PauseMenu
extends Control

## The battle's pause overlay: Resume, the volume slider and Return to Missions.
##
## It shows and hides itself and reports what happened. What pausing means (which
## things stop) is the battle's business, so `BattleRoot` answers `opened` and
## `closed`, and decides what leaving the battle costs.

signal opened
signal closed
signal main_menu_requested

@export var resume_button: Button
@export var main_menu_button: Button
@export var volume_slider: HSlider
@export var volume_value: Label

## Shown in place of a percentage when the audio bus is missing.
@export var volume_unavailable_text := "Unavailable"

var _audio: AudioSettings


func _ready() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_ALWAYS
	resume_button.pressed.connect(close)
	main_menu_button.pressed.connect(main_menu_requested.emit)
	volume_slider.value_changed.connect(_on_volume_changed)


func setup(audio: AudioSettings) -> void:
	_audio = audio
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


func _on_volume_changed(value: float) -> void:
	_audio.set_volume(value / 100.0)
	_update_label()


func _update_label() -> void:
	if _audio == null or not _audio.is_available():
		volume_value.text = volume_unavailable_text
	else:
		volume_value.text = "%d%%" % roundi(volume_slider.value)


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()
