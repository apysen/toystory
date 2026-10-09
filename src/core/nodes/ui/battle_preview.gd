class_name BattlePreview
extends Control

## The head-to-head preview shown once an action and its target are picked
## (Fire Emblem's forecast, dressed as two toy-packaging cards joined by a strip of
## masking tape). Each card shows its unit's portrait, HP before and after, and its
## damage, hit and crit. The tape lists every strike in order; a strike that would
## Break its target gets a red X.
##
## It shows an `Exchange.preview` result and changes nothing.

## Shown or hidden, so the HUD can make room at the bottom of the screen.
signal shown_changed(is_shown: bool)

@export_group("Left Card")
@export var left_header: Panel
@export var left_name: Label
@export var left_portrait: TextureRect
@export var left_hp: Label
@export var left_bar: Control
@export var left_stats: Label

@export_group("Right Card")
@export var right_card: Control
@export var right_header: Panel
@export var right_name: Label
@export var right_portrait: TextureRect
@export var right_hp: Label
@export var right_bar: Control
@export var right_stats: Label

@export_group("Tape")
@export var title_label: Label
@export var strike_list: VBoxContainer
@export var effect_label: Label
@export var confirm_hint: Label

@export_group("Strike Columns")
@export var number_width := 18.0
@export var mark_width := 20.0
@export var stats_width := 200.0
@export var arrow_width := 48.0

@export_group("Colours")
@export var player_band := Color("4f8fd0")
@export var enemy_band := Color("d0574f")
@export var neutral_band := Color("5aa865")
@export var kill_color := Color("e0251b")

var _slide: Tween


func _ready() -> void:
	visible = false
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func show_exchange(ex: Dictionary) -> void:
	var user: Unit = ex.user
	var sides: Array = ex.sides
	var other: Dictionary = {}
	for s in sides:
		if s.unit != user:
			other = s
			break
	_fill_card(user, _side(sides, user), _strikes_by(ex, user), left_header, left_name, left_portrait, left_hp, left_bar, left_stats)
	right_card.visible = not other.is_empty()
	if not other.is_empty():
		_fill_card(other.unit, other, _strikes_by(ex, other.unit), right_header, right_name, right_portrait, right_hp, right_bar, right_stats)
	title_label.text = ex.title
	for c in strike_list.get_children():
		c.queue_free()
	var n := 1
	for st in ex.strikes:
		strike_list.add_child(_strike_row(n, st, user))
		n += 1
	if ex.strikes.is_empty():
		var none := Label.new()
		none.text = "No attacks"
		none.add_theme_color_override("font_color", Color("6a5a44"))
		none.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		strike_list.add_child(none)
	effect_label.text = ex.effect
	effect_label.visible = ex.effect != ""
	if not visible:
		visible = true
		shown_changed.emit(true)
		modulate.a = 0.0
		position.y = 40.0
		if _slide != null:
			_slide.kill()
		_slide = create_tween().set_parallel()
		_slide.tween_property(self, "modulate:a", 1.0, 0.15)
		_slide.tween_property(self, "position:y", 0.0, 0.2).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func hide_preview() -> void:
	if visible:
		visible = false
		shown_changed.emit(false)


func _side(sides: Array, u: Unit) -> Dictionary:
	for s in sides:
		if s.unit == u:
			return s
	return {}


func _strikes_by(ex: Dictionary, u: Unit) -> Array:
	return ex.strikes.filter(func(s): return s.by == u)


func _fill_card(u: Unit, side: Dictionary, strikes: Array, header: Panel, name_l: Label, portrait: TextureRect,
		hp_l: Label, bar: Control, stats: Label) -> void:
	var band := player_band if u.faction == Defs.Faction.PLAYER else (enemy_band if u.faction == Defs.Faction.ENEMY else neutral_band)
	var sb := StyleBoxFlat.new()
	sb.bg_color = band
	sb.corner_radius_top_left = 10
	sb.corner_radius_top_right = 10
	header.add_theme_stylebox_override("panel", sb)
	name_l.text = u.name
	portrait.texture = Portraits.get_portrait(u.name)
	var before: int = side.get("hp_before", u.hp)
	var after: int = side.get("hp_after", u.hp)
	hp_l.text = "HP %d" % before if before == after else "HP %d → %d" % [before, after]
	hp_l.add_theme_color_override("font_color", kill_color if after == 0 else (Color("2b2230") if after == before else Color("a8551c")))
	bar.set_meta("before", float(before) / u.max_hp)
	bar.set_meta("after", float(after) / u.max_hp)
	bar.set_meta("color", band)
	if not bar.draw.is_connected(_draw_bar):
		bar.draw.connect(_draw_bar.bind(bar))
	bar.queue_redraw()
	if strikes.is_empty():
		stats.text = "Dmg –
Hit –   Crit –"
	else:
		var s: Dictionary = strikes[0]
		var times := "  ×%d" % strikes.size() if strikes.size() > 1 else ""
		stats.text = "Dmg %d%s
Hit %d%%   Crit %d%%" % [s.damage, times, s.hit, s.crit]


func _draw_bar(bar: Control) -> void:
	var r := Rect2(Vector2.ZERO, bar.size)
	bar.draw_rect(r, Color("2b2230"))
	var before: float = bar.get_meta("before", 1.0)
	var after: float = bar.get_meta("after", 1.0)
	var col: Color = bar.get_meta("color", Color.WHITE)
	var inner := r.grow(-2)
	bar.draw_rect(Rect2(inner.position, Vector2(inner.size.x * after, inner.size.y)), col.lightened(0.15))
	var pulse := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 150.0)
	bar.draw_rect(Rect2(inner.position + Vector2(inner.size.x * after, 0), Vector2(inner.size.x * (before - after), inner.size.y)),
		Color("ffdf6b").lerp(Color("ff6a3d"), pulse))


func _process(_delta: float) -> void:
	if visible:
		left_bar.queue_redraw()
		right_bar.queue_redraw()


## One strike as fixed columns, so every row lines up:
##   number | X | the user's numbers | arrow (centred) | the other side's numbers | X | spacer
## The user's strikes put their numbers on the left, under its card, with a blue
## arrow pointing right; the other side's go on the right with a red arrow pointing left. A killing strike's X sits beside its numbers.
func _strike_row(n: int, st: Dictionary, user: Unit) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var by_user: bool = st.by == user
	var num := _cell(row, "%d" % n, number_width, HORIZONTAL_ALIGNMENT_RIGHT, Color("8a7656"))
	num.add_theme_font_size_override("font_size", 15)
	_kill_mark(row, st if by_user else {})
	var stats := "%d dmg  ·  %d%%%s" % [st.damage, st.hit, "  ·  crit %d%%" % st.crit if st.crit > 0 else ""]
	_cell(row, stats if by_user else "", stats_width, HORIZONTAL_ALIGNMENT_RIGHT, Color("2b2230"))
	# Who strikes, as an arrow pointing from the striker's card toward the target's:
	# blue for the player's side, red for the enemy's.
	var arrow_col: Color = player_band if st.by.faction == Defs.Faction.PLAYER else enemy_band
	var arrow := _cell(row, "▶" if by_user else "◀", arrow_width, HORIZONTAL_ALIGNMENT_CENTER, arrow_col)
	arrow.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	arrow.add_theme_font_size_override("font_size", 22)
	arrow.add_theme_color_override("font_outline_color", arrow_col.darkened(0.5))
	arrow.add_theme_constant_override("outline_size", 3)
	arrow.tooltip_text = st.by.name + (" (counter)" if st.get("counter", false) else "")
	arrow.mouse_filter = Control.MOUSE_FILTER_PASS
	_cell(row, "" if by_user else stats, stats_width, HORIZONTAL_ALIGNMENT_LEFT, Color("2b2230"))
	_kill_mark(row, {} if by_user else st)
	# Balances the number column, so the names sit exactly under the title.
	_cell(row, "", number_width, HORIZONTAL_ALIGNMENT_LEFT, Color.TRANSPARENT)
	return row


func _cell(row: HBoxContainer, text: String, width: float, align: HorizontalAlignment, col: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.custom_minimum_size = Vector2(width, 0)
	l.horizontal_alignment = align
	l.clip_text = true
	l.add_theme_color_override("font_color", col)
	row.add_child(l)
	return l


## The red X beside a strike that would Break its target (an empty slot otherwise,
## so the columns stay put).
func _kill_mark(row: HBoxContainer, st: Dictionary) -> void:
	var x := Label.new()
	x.custom_minimum_size = Vector2(mark_width, 0)
	x.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	if not st.is_empty() and st.lethal:
		x.text = "X"
		x.add_theme_font_size_override("font_size", 22)
		x.add_theme_color_override("font_color", kill_color)
		x.add_theme_color_override("font_outline_color", Color("3a0a08"))
		x.add_theme_constant_override("outline_size", 6)
		x.tooltip_text = "%s would be Broken" % st.on.name
		x.mouse_filter = Control.MOUSE_FILTER_PASS
	row.add_child(x)
