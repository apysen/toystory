class_name DialogueBox
extends Control
## Bottom-of-screen conversation box with a portrait slot. Click or press
## accept to advance. `await play(lines)`; each line is {speaker, text}.

signal finished

var _lines: Array = []
var _index := 0
var _panel: PanelContainer
var _name: Label
var _text: RichTextLabel
var _portrait: TextureRect
var _portrait_fallback: ColorRect


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_panel.offset_top = -170
	_panel.offset_left = 24
	_panel.offset_right = -24
	_panel.offset_bottom = -16
	add_child(_panel)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	_panel.add_child(row)
	var frame := Control.new()
	frame.custom_minimum_size = Vector2(128, 128)
	row.add_child(frame)
	_portrait_fallback = ColorRect.new()
	_portrait_fallback.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame.add_child(_portrait_fallback)
	_portrait = TextureRect.new()
	_portrait.set_anchors_preset(Control.PRESET_FULL_RECT)
	_portrait.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	frame.add_child(_portrait)
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(col)
	_name = Label.new()
	_name.add_theme_font_size_override("font_size", 20)
	col.add_child(_name)
	_text = RichTextLabel.new()
	_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_text.add_theme_font_size_override("normal_font_size", 18)
	_text.fit_content = true
	col.add_child(_text)
	var hint := Label.new()
	hint.text = "Click to continue"
	hint.modulate = Color(1, 1, 1, 0.5)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	col.add_child(hint)


func play(lines: Array) -> void:
	if lines.is_empty():
		return
	_lines = lines
	_index = 0
	visible = true
	_show()
	await finished


func _show() -> void:
	var line: Dictionary = _lines[_index]
	_name.text = line.speaker
	_text.text = line.text
	var tex := Portraits.get_portrait(line.get("portrait", line.speaker))
	_portrait.texture = tex
	_portrait_fallback.visible = tex == null
	_portrait_fallback.color = Portraits.fallback_color(line.speaker)


func _advance() -> void:
	_index += 1
	if _index >= _lines.size():
		visible = false
		finished.emit()
	else:
		_show()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_advance()
		accept_event()


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_accept"):
		_advance()
		get_viewport().set_input_as_handled()
