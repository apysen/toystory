class_name DialogueBox
extends Control

## Bottom-of-screen conversation box with a portrait slot. Click or press accept to
## advance. `await play(lines)`; each line is {speaker, text, portrait?}.

signal finished

@export var speaker_label: Label
@export var line_text: RichTextLabel
@export var portrait: TextureRect
## Flat colour shown when a speaker has no portrait or sprite yet.
@export var portrait_fallback: ColorRect

var _lines: Array = []
var _index := 0


func _ready() -> void:
	visible = false


func play(lines: Array) -> void:
	if lines.is_empty():
		return
	_lines = lines
	_index = 0
	visible = true
	_show()
	await finished


func is_playing() -> bool:
	return visible


func advance() -> void:
	_index += 1
	if _index >= _lines.size():
		visible = false
		finished.emit()
	else:
		_show()


func _show() -> void:
	var line: Dictionary = _lines[_index]
	speaker_label.text = line.speaker
	line_text.text = line.text
	var tex := Portraits.get_portrait(line.get("portrait", line.speaker))
	portrait.texture = tex
	portrait_fallback.visible = tex == null
	portrait_fallback.color = Portraits.fallback_color(line.speaker)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		advance()
		accept_event()


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_accept"):
		advance()
		get_viewport().set_input_as_handled()
