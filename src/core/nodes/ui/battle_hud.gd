class_name BattleHud
extends Control

## Minimum combat UI (vertical_slice_plan.md section 19): phase, turn, Noise,
## objectives, unit card with predicted HP, threat list, combat forecast, action
## menu and End Turn, plus the phase banner, Art toast and battle log.
##
## It reads the `Battle` and the shared `BattleSelection` it is handed in `setup()`
## and changes neither. Everything the player chooses here is reported upward.

signal end_turn_requested
signal action_chosen(action_id: String)
signal back_requested

@export_group("Top Bar")
@export var turn_label: Label
@export var noise_meter: NoiseMeter
@export var objective_label: Label

@export_group("Side Panel")
@export var unit_card: RichTextLabel
@export var forecast_text: RichTextLabel
@export var action_list: VBoxContainer
@export var end_turn_button: Button
@export var log_text: RichTextLabel

@export_group("Announcements")
@export var banner_label: Label
@export var toast_label: Label
@export var banner_hold_seconds := 0.6
@export var toast_seconds := 0.45

@export_group("Wording")
@export var idle_hint := "Click a character to move. Click an enemy to see its reach. Right-click to cancel."
@export var back_label := "Back (undo move)"
## Lines kept in the battle log.
@export var log_capacity := 40

var _battle: Battle
var _selection: BattleSelection
var _objective := ""
var _log_lines: Array[String] = []


func _ready() -> void:
	end_turn_button.pressed.connect(end_turn_requested.emit)
	banner_label.visible = false
	toast_label.visible = false


func setup(b: Battle, s: BattleSelection, objective: String) -> void:
	_battle = b
	_selection = s
	_objective = objective
	refresh()


func refresh() -> void:
	var b := _battle
	if b == null:
		return
	var phase_name := "Player Phase" if b.phase == Defs.Phase.PLAYER else ("Enemy Phase" if b.phase == Defs.Phase.ENEMY else "")
	turn_label.text = "Turn %d   %s%s" % [b.turn, phase_name, "   [HUMAN GAZE]" if b.gaze_active() else ""]
	noise_meter.show_noise(b.noise, b.gaze_active())
	var s := b.stars()
	objective_label.text = "%s     %s Recruit Umbrella   %s %d turns or fewer   %s No one Broken" % [_objective,
		Stars.glyph(s.recruit), Stars.glyph(b.turn <= Defs.STAR_TURN_TARGET), Defs.STAR_TURN_TARGET, Stars.glyph(not b.any_broken)]
	end_turn_button.disabled = not _selection.can_end_turn()
	_refresh_card()
	_refresh_forecast()


## Type name with its icon from assets/sprites/ui/type_<name>.png when present.
func _type_tag(type: int) -> String:
	var type_name: String = Defs.TYPE_NAMES[type]
	var path := "res://assets/sprites/ui/type_%s.png" % type_name.to_lower()
	if SpriteLib.load_ui("type_" + type_name.to_lower()) != null and ResourceLoader.exists(path):
		return "[img=24x24]%s[/img] %s" % [path, type_name]
	return type_name


func _refresh_card() -> void:
	var sel := _selection
	var u := sel.focus_unit(_battle.board)
	if u == null:
		unit_card.text = "[color=#aaa]%s[/color]" % idle_hint
		return
	var t := "[b]%s[/b]  %s%s\n" % [u.name, _type_tag(u.dmg_type), "  (Large)" if u.is_large() else ""]
	var hp_line := "HP %d / %d" % [u.hp, u.max_hp]
	if u == sel.selected and not sel.forecast.is_empty() and u.faction == Defs.Faction.PLAYER:
		var f: Dictionary = sel.forecast
		var col: String = {"Safe": "#8f8", "Exposed": "#fd6", "High Risk": "#f94", "Broken Risk": "#f55"}[f.risk]
		hp_line += "  ->  ~%d   [color=%s]%s[/color]" % [f.predicted_hp, col, f.risk]
	t += hp_line + "\n"
	t += "Pow %d  Def %d  Skl %d  Spd %d  Move %d\n" % [u.power, u.defense, u.skill, u.speed, _battle.effective_move(u)]
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
	unit_card.text = t


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
	var sel := _selection
	var t := ""
	if sel.mode == BattleSelection.Mode.TARGET and sel.hover_target != null:
		t = _combat_forecast(sel.hover_target)
	elif not sel.forecast.is_empty() and sel.selected != null:
		var f: Dictionary = sel.forecast
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
	elif sel.mode == BattleSelection.Mode.TARGET:
		t = "Pick a target. Right-click to go back."
	if _battle.gaze_active() and sel.selected != null:
		t += "\n[color=#c9f]Human Gaze active: Noise Arts are unavailable everywhere.[/color]"
	forecast_text.text = t


func _combat_forecast(tgt: Variant) -> String:
	var sel := _selection
	var u: Unit = sel.selected
	var b := _battle
	if tgt is Vector2i and sel.target_kind == "attack":
		var o: Dictionary = b.board.objects[tgt]
		return "[b]%s[/b]\nDeals %d to cover (%d HP left)." % [o.kind.replace("_", " "), u.power + u.might, maxi(o.hp - u.power - u.might, 0)]
	if tgt is Vector2i:
		var hits := b.units_in_tiles(b.cone_for(u, tgt)).filter(func(o): return b.can_target(u, o))
		var art := Arts.get_art(sel.target_kind.substr(4))
		var s := "[b]%s[/b]\n" % art.name
		for o in hits:
			if art.has("might"):
				var pv := Combat.preview(b.board, u, u.pos, o, o.pos, {"might": art.might, "type": art.type})
				s += "%s: %d dmg, %d%% hit\n" % [o.name, pv.damage, pv.hit]
			else:
				s += "%s: pushed 2 tiles\n" % o.name
		return s if not hits.is_empty() else s + "Nothing in the area."
	var target: Unit = tgt
	if sel.target_kind == "talk":
		return "[b]Talk[/b] to %s.\nIt joins next Player Phase." % target.name
	var spec := {"might": u.might, "type": u.dmg_type}
	var title := "Basic Attack"
	if sel.target_kind.begins_with("art:"):
		var art := Arts.get_art(sel.target_kind.substr(4))
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
	s += "%s (%s vs %s)%s\n" % [rel, _type_tag(spec.type), _type_tag(target.dmg_type), "   [color=#9cf]Target in cover -25 Hit[/color]" if pv.cover else ""]
	s += "%s HP %d -> %d\n" % [target.name, target.hp, maxi(target.hp - pv.damage, 0)]
	if sel.target_kind == "attack":
		var c := b.counter_preview(u, u.pos, target)
		if c.is_empty():
			s += "No counter."
		else:
			s += "Counter: %d dmg, %d%% hit" % [c.damage, c.hit]
	else:
		s += "Arts don't trigger counters."
	return s


## Shows the unit's action menu: [{id, label, enabled, tooltip}].
func show_actions(u: Unit, actions: Array) -> void:
	hide_actions()
	var head := Label.new()
	head.text = u.name
	action_list.add_child(head)
	for a in actions:
		var btn := Button.new()
		btn.text = a.label
		btn.disabled = not a.enabled
		btn.tooltip_text = a.tooltip
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		btn.pressed.connect(action_chosen.emit.bind(a.id))
		action_list.add_child(btn)
	var back := Button.new()
	back.text = back_label
	back.pressed.connect(back_requested.emit)
	action_list.add_child(back)


func hide_actions() -> void:
	for c in action_list.get_children():
		c.queue_free()


func log_line(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > log_capacity:
		_log_lines.pop_front()
	log_text.text = "\n".join(_log_lines)


func banner(s: String) -> void:
	banner_label.text = s
	banner_label.visible = true
	banner_label.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(banner_label, "modulate:a", 1.0, 0.15)
	tw.tween_interval(banner_hold_seconds)
	tw.tween_property(banner_label, "modulate:a", 0.0, 0.2)
	await tw.finished
	banner_label.visible = false


func toast(s: String) -> void:
	toast_label.text = s
	toast_label.visible = true
	await get_tree().create_timer(toast_seconds).timeout
	toast_label.visible = false


func pulse_end_turn() -> void:
	var tw := create_tween()
	tw.tween_property(end_turn_button, "modulate", Color(1.4, 1.4, 0.8), 0.25)
	tw.tween_property(end_turn_button, "modulate", Color.WHITE, 0.25)
