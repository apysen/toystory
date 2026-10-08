extends Node
## Minimal menu flow (vertical_slice_plan.md section 24):
## Mission Select -> Team Preview -> Battle -> Results -> Mission Select.

var _screen: Node
var _ui: CanvasLayer
var _best := {} # best star result this session


func _ready() -> void:
	_ui = CanvasLayer.new()
	_ui.layer = 5
	add_child(_ui)
	show_mission_select()


func _clear() -> void:
	if _screen != null:
		_screen.queue_free()
		_screen = null


func _panel(title: String) -> VBoxContainer:
	_clear()
	var bg := ColorRect.new()
	bg.color = Color("1e1a22")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ui.add_child(bg)
	_screen = bg
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.add_child(center)
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(720, 0)
	box.add_theme_constant_override("separation", 14)
	center.add_child(box)
	var h := Label.new()
	h.text = title
	h.add_theme_font_size_override("font_size", 34)
	box.add_child(h)
	return box


func _label(parent: Node, text: String, size := 18, color := Color.WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(l)
	return l


func _button(parent: Node, text: String, fn: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 44)
	b.pressed.connect(fn)
	parent.add_child(b)
	return b


func show_mission_select() -> void:
	var box := _panel("Missions")
	var card := PanelContainer.new()
	box.add_child(card)
	var inner := VBoxContainer.new()
	card.add_child(inner)
	_label(inner, "Under the Desk", 24)
	_label(inner, "The study floor. Hostile objects block the way, and an umbrella is trapped on the far side of the room.", 16, Color("cccccc"))
	_label(inner, "Objective: Defeat the Paper Cutter Captain.", 16)
	var stars := "Best: %s" % _stars_text(_best) if not _best.is_empty() else "Not cleared yet"
	_label(inner, "Optional: Recruit Umbrella  /  Finish in %d turns or fewer  /  No one Broken.   %s" % [Defs.STAR_TURN_TARGET, stars], 14, Color("e0d080"))
	_button(inner, "Select", show_team_preview)
	_button(box, "Quit", func(): get_tree().quit())


func show_team_preview() -> void:
	var box := _panel("Team Preview")
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 16)
	box.add_child(grid)
	for def in UnderTheDesk.unit_defs():
		if def.faction != Defs.Faction.PLAYER:
			continue
		var cell := VBoxContainer.new()
		cell.custom_minimum_size = Vector2(220, 0)
		grid.add_child(cell)
		var tex := Portraits.get_portrait(def.name)
		if tex != null:
			var tr := TextureRect.new()
			tr.texture = tex
			tr.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			tr.custom_minimum_size = Vector2(128, 128)
			tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			cell.add_child(tr)
		_label(cell, "%s  (%s%s)" % [def.name, Defs.TYPE_NAMES[def.type], ", Large" if def.get("size", 1) > 1 else ""], 18)
		_label(cell, "HP %d  Pow %d  Def %d  Move %d" % [def.hp, def.pow, def.def, def.mov], 14, Color("cccccc"))
		var arts: Array[String] = []
		for a in def.arts:
			arts.append(Arts.get_art(a).name)
		_label(cell, ", ".join(arts), 14, Color("9cc8ff"))
	_label(box, "All five deploy at the bottom-left of the map. Umbrella can join mid-battle if Lamp talks to it.", 14, Color("aaaaaa"))
	var row := HBoxContainer.new()
	box.add_child(row)
	_button(row, "Back", show_mission_select)
	_button(row, "Start Mission", start_battle)


func start_battle() -> void:
	_clear()
	var view := BattleView.new()
	add_child(view)
	_screen = view
	view.battle_finished.connect(_on_battle_finished.bind(view))
	view.start(0, SliceDialogue.PRE_BATTLE)


func _on_battle_finished(result: Dictionary, view: BattleView) -> void:
	var lines: Array = SliceDialogue.DEFEAT
	if result.victory:
		lines = SliceDialogue.VICTORY.duplicate()
		if result.recruited and result.stars.recruit:
			lines.append_array(SliceDialogue.VICTORY_WITH_UMBRELLA)
	await view._dialogue.play(lines)
	if result.victory:
		var count := _star_count(result.stars)
		if _best.is_empty() or count > _star_count(_best):
			_best = result.stars
	show_results(result)


func show_results(result: Dictionary) -> void:
	var box := _panel("Victory" if result.victory else "Defeat")
	var s: Dictionary = result.stars
	_label(box, "Turns: %d" % result.turns, 20)
	_label(box, "%s  Recruit Umbrella" % _star(s.recruit), 20)
	_label(box, "%s  Finish in %d turns or fewer" % [_star(s.turns), Defs.STAR_TURN_TARGET], 20)
	_label(box, "%s  No one Broken" % _star(s.unbroken), 20)
	if not result.broken.is_empty():
		_label(box, "Broken: %s" % ", ".join(result.broken), 16, Color("f08080"))
	var st: Dictionary = result.stats
	_label(box, "Arts used: %d   Human Gaze triggered: %d   Enemies caught in Gaze: %d   Allies caught: %d" % [
		st.arts_used, st.gaze_triggers, st.enemies_caught, st.allies_caught], 14, Color("aaaaaa"))
	var row := HBoxContainer.new()
	box.add_child(row)
	_button(row, "Retry", start_battle)
	_button(row, "Return to Missions", show_mission_select)


func _star(on: bool) -> String:
	return "★" if on else "☆"


func _star_count(s: Dictionary) -> int:
	return int(s.recruit) + int(s.turns) + int(s.unbroken)


func _stars_text(s: Dictionary) -> String:
	return "%s%s%s" % [_star(s.recruit), _star(s.turns), _star(s.unbroken)]
