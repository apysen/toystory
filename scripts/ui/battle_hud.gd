class_name BattleHud
extends Control
## Minimum combat UI (vertical_slice_plan.md section 19): phase, turn, Noise,
## objectives, unit card with predicted HP, threat list, combat forecast,
## action menu and End Turn.

const PANEL_W := 340

var view: BattleView
var _top: Label
var _noise: NoiseMeter
var _objective: Label
var _card: RichTextLabel
var _forecast: RichTextLabel
var _actions: VBoxContainer
var _end_turn: Button
var _log: RichTextLabel
var _banner: Label
var _toast: Label
var _log_lines: Array[String] = []


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	var bar := PanelContainer.new()
	bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	bar.offset_bottom = 40
	bar.mouse_filter = Control.MOUSE_FILTER_STOP
	bar.add_theme_stylebox_override("panel", panel_style())
	add_child(bar)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 24)
	bar.add_child(row)
	_top = Label.new()
	_top.add_theme_font_size_override("font_size", 18)
	row.add_child(_top)
	var nl := Label.new()
	nl.text = "Noise"
	row.add_child(nl)
	_noise = NoiseMeter.new()
	_noise.custom_minimum_size = Vector2(6 * 22, 24)
	row.add_child(_noise)
	_objective = Label.new()
	_objective.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_objective.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(_objective)

	var side := PanelContainer.new()
	side.set_anchors_preset(Control.PRESET_RIGHT_WIDE)
	side.offset_left = -PANEL_W
	side.offset_top = 44
	side.mouse_filter = Control.MOUSE_FILTER_STOP
	side.add_theme_stylebox_override("panel", panel_style())
	add_child(side)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 8)
	side.add_child(col)
	_card = _rich(col, 150)
	_forecast = _rich(col, 200)
	_actions = VBoxContainer.new()
	col.add_child(_actions)
	_end_turn = Button.new()
	_end_turn.text = "End Turn"
	_end_turn.pressed.connect(func(): view.end_turn())
	col.add_child(_end_turn)
	_log = _rich(col, 120)
	_log.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_log.scroll_following = true

	_banner = Label.new()
	_banner.set_anchors_preset(Control.PRESET_CENTER)
	_banner.add_theme_font_size_override("font_size", 40)
	_banner.add_theme_color_override("font_outline_color", Color.BLACK)
	_banner.add_theme_constant_override("outline_size", 8)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_banner.visible = false
	add_child(_banner)
	_toast = Label.new()
	_toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_toast.offset_top = 56
	_toast.add_theme_font_size_override("font_size", 24)
	_toast.add_theme_color_override("font_outline_color", Color.BLACK)
	_toast.add_theme_constant_override("outline_size", 6)
	_toast.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.visible = false
	add_child(_toast)


static func panel_style() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("1d1a22f0")
	sb.border_color = Color("4a4256")
	sb.set_border_width_all(2)
	sb.set_content_margin_all(10)
	return sb


func _rich(parent: Node, min_h: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.custom_minimum_size = Vector2(PANEL_W - 16, min_h)
	r.fit_content = false
	r.add_theme_font_size_override("normal_font_size", 14)
	r.add_theme_font_size_override("bold_font_size", 15)
	parent.add_child(r)
	return r


func refresh() -> void:
	var b := view.battle
	if b == null:
		return
	var phase_name := "Player Phase" if b.phase == Defs.Phase.PLAYER else ("Enemy Phase" if b.phase == Defs.Phase.ENEMY else "")
	_top.text = "Turn %d   %s%s" % [b.turn, phase_name, "   [HUMAN GAZE]" if b.gaze_active() else ""]
	_noise.value = b.noise
	_noise.gaze = b.gaze_active()
	_noise.queue_redraw()
	var s := b.stars()
	_objective.text = "Defeat the Paper Cutter Captain     %s Recruit Umbrella   %s %d turns or fewer   %s No one Broken" % [
		_star(s.recruit), _star(b.turn <= Defs.STAR_TURN_TARGET), Defs.STAR_TURN_TARGET, _star(not b.any_broken)]
	_end_turn.disabled = view.mode != BattleView.Mode.IDLE and view.mode != BattleView.Mode.SELECTED
	_refresh_card()
	_refresh_forecast()


func _star(on: bool) -> String:
	return "★" if on else "☆"


func _refresh_card() -> void:
	var u: Unit = view.selected
	if u == null and view.hover != BattleView.NONE:
		u = view.battle.board.unit_at(view.hover)
	if u == null:
		u = view.inspected_enemy
	if u == null:
		_card.text = "[color=#aaa]Click a character to move. Click an enemy to see its reach. Right-click to cancel.[/color]"
		return
	var t := "[b]%s[/b]  %s%s\n" % [u.name, Defs.TYPE_NAMES[u.dmg_type], "  (Large)" if u.is_large() else ""]
	var hp_line := "HP %d / %d" % [u.hp, u.max_hp]
	if u == view.selected and not view.forecast.is_empty() and u.faction == Defs.Faction.PLAYER:
		var f: Dictionary = view.forecast
		var col: String = {"Safe": "#8f8", "Exposed": "#fd6", "High Risk": "#f94", "Broken Risk": "#f55"}[f.risk]
		hp_line += "  ->  ~%d   [color=%s]%s[/color]" % [f.predicted_hp, col, f.risk]
	t += hp_line + "\n"
	t += "Pow %d  Def %d  Skl %d  Spd %d  Move %d\n" % [u.power, u.defense, u.skill, u.speed, view.battle.effective_move(u)]
	t += "Basic: range %d%s, Might %d\n" % [u.attack_range, "" if u.min_range == 1 else " (min %d)" % u.min_range, u.might]
	if u.faction == Defs.Faction.PLAYER:
		var arts: Array[String] = []
		for a in u.arts:
			arts.append("%s +%d" % [Arts.get_art(a).name, Arts.noise_of(a)])
		t += "Arts: " + ", ".join(arts) + "\n"
		t += "Item: %s\n" % (Arts.ITEMS[u.item].name if u.item != "" else "-")
	else:
		t += _enemy_trait(u) + "\n"
	var st := u.status.keys().filter(func(k): return k not in ["home", "watchful_used"])
	if not st.is_empty():
		t += "[color=#9cf]Status: %s[/color]" % ", ".join(st)
	if u.frozen:
		t += "\n[color=#c9f]Watched by a human: can't act or be attacked.[/color]"
	_card.text = t


func _enemy_trait(u: Unit) -> String:
	match u.ai:
		"pencil": return "Trait: Charge. +20% damage after moving 3+ tiles."
		"snarer": return "Trait: Snap pulls the target 1 tile."
		"guard": return "Trait: Holds the central lane. Hard to displace."
		"tape": return "Trait: Tape Lash makes the target's tile sticky."
		"roomba": return "Expected Behavior: moves while watched, can't attack."
		"captain": return "Technique: Cutting Line (telegraphed 1x5). Heavy Frame."
	if u.faction == Defs.Faction.NEUTRAL:
		return "Neutral. Lamp can Talk to recruit."
	return ""


func _refresh_forecast() -> void:
	var b := view.battle
	var t := ""
	if view.mode == BattleView.Mode.TARGET and view.hover_target != null:
		t = _combat_forecast(view.hover_target)
	elif not view.forecast.is_empty() and view.selected != null:
		var f: Dictionary = view.forecast
		if f.threats.is_empty() and f.telegraph_damage == 0:
			t = "[color=#8f8]No enemy can reach this tile.[/color]"
		else:
			t = "[b]Threats here[/b]  (expected -%d HP)\n" % roundi(f.expected)
			for th in f.threats:
				var pv: Dictionary = th.preview
				var rel: String = ["[color=#f88]weak[/color]", "", "[color=#8f8]strong[/color]"][pv.type_rel + 1]
				t += "%s: %d dmg, %d%% hit, %d%% crit %s%s%s\n" % [th.enemy.name, pv.damage, pv.hit, pv.crit,
					rel, " [color=#9cf]cover[/color]" if pv.cover else "",
					" [color=#6df]pull/push[/color]" if not th.displacement.is_empty() else ""]
			if f.telegraph_damage > 0:
				t += "[color=#f55]Cutting Line lane: %d damage, certain[/color]\n" % f.telegraph_damage
	elif view.mode == BattleView.Mode.TARGET:
		t = "Pick a target. Right-click to go back."
	if b.gaze_active() and view.selected != null:
		t += "\n[color=#c9f]Human Gaze active: Noise Arts are unavailable everywhere.[/color]"
	_forecast.text = t


func _combat_forecast(tgt: Variant) -> String:
	var u: Unit = view.selected
	var b := view.battle
	if tgt is Vector2i and view.target_kind == "attack":
		var o: Dictionary = b.board.objects[tgt]
		return "[b]%s[/b]\nDeals %d to cover (%d HP left)." % [o.kind.replace("_", " "), u.power + u.might, maxi(o.hp - u.power - u.might, 0)]
	if tgt is Vector2i:
		var hits := b.units_in_tiles(b.cone_for(u, tgt)).filter(func(o): return b.can_target(u, o))
		var art := Arts.get_art(view.target_kind.substr(4))
		var s := "[b]%s[/b]\n" % art.name
		for o in hits:
			if art.has("might"):
				var pv := Combat.preview(b.board, u, u.pos, o, o.pos, {"might": art.might, "type": art.type})
				s += "%s: %d dmg, %d%% hit\n" % [o.name, pv.damage, pv.hit]
			else:
				s += "%s: pushed 2 tiles\n" % o.name
		return s if not hits.is_empty() else s + "Nothing in the area."
	var target: Unit = tgt
	if view.target_kind == "talk":
		return "[b]Talk[/b] to %s.\nIt joins next Player Phase." % target.name
	var spec := {"might": u.might, "type": u.dmg_type}
	var title := "Basic Attack"
	if view.target_kind.begins_with("art:"):
		var art := Arts.get_art(view.target_kind.substr(4))
		title = art.name
		if not art.has("might"):
			return "[b]%s[/b] on %s\n%s" % [art.name, target.name, art.desc]
		spec = {"might": art.might, "type": art.type}
	if u.status.has("heated"):
		spec["power_bonus"] = 2
	if u.id == "stapler" and (b.has_movement_penalty(target) or target.displaced_this_phase):
		spec["dmg_mult"] = 1.2
	var pv := Combat.preview(b.board, u, u.pos, target, target.pos, spec)
	var rel: String = ["[color=#f88]Disadvantage[/color]", "Neutral", "[color=#8f8]Advantage[/color]"][pv.type_rel + 1]
	var s := "[b]%s[/b] -> %s\n" % [title, target.name]
	s += "Damage %d   Hit %d%%   Crit %d%%\n" % [pv.damage, pv.hit, pv.crit]
	s += "%s (%s vs %s)%s\n" % [rel, Defs.TYPE_NAMES[spec.type], Defs.TYPE_NAMES[target.dmg_type], "   [color=#9cf]Target in cover -25 Hit[/color]" if pv.cover else ""]
	s += "%s HP %d -> %d\n" % [target.name, target.hp, maxi(target.hp - pv.damage, 0)]
	if view.target_kind == "attack":
		var c := b.counter_preview(u, u.pos, target)
		if c.is_empty():
			s += "No counter."
		else:
			s += "Counter: %d dmg, %d%% hit" % [c.damage, c.hit]
	else:
		s += "Arts don't trigger counters."
	return s


func show_actions(u: Unit, actions: Array) -> void:
	hide_actions()
	var head := Label.new()
	head.text = u.name
	_actions.add_child(head)
	for a in actions:
		var btn := Button.new()
		btn.text = a.label
		btn.disabled = not a.enabled
		btn.tooltip_text = a.tooltip
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		var id: String = a.id
		btn.pressed.connect(func(): view.on_action(id))
		_actions.add_child(btn)
	var back := Button.new()
	back.text = "Back (undo move)"
	back.pressed.connect(func(): view.cancel())
	_actions.add_child(back)


func hide_actions() -> void:
	for c in _actions.get_children():
		c.queue_free()


func log_line(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > 40:
		_log_lines.pop_front()
	_log.text = "\n".join(_log_lines)


func banner(s: String) -> void:
	_banner.text = s
	_banner.visible = true
	_banner.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(_banner, "modulate:a", 1.0, 0.15)
	tw.tween_interval(0.6)
	tw.tween_property(_banner, "modulate:a", 0.0, 0.2)
	await tw.finished
	_banner.visible = false


func toast(s: String) -> void:
	_toast.text = s
	_toast.visible = true
	await get_tree().create_timer(0.45).timeout
	_toast.visible = false


func pulse_end_turn() -> void:
	var tw := create_tween()
	tw.tween_property(_end_turn, "modulate", Color(1.4, 1.4, 0.8), 0.25)
	tw.tween_property(_end_turn, "modulate", Color.WHITE, 0.25)
