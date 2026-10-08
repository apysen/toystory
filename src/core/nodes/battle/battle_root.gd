class_name BattleRoot
extends Node2D

## Composition root of one tactical battle. It owns the player's turn flow (select,
## move, choose an action, pick a target, end the phase) and coordinates the peers
## that do the work: `Battle` resolves the rules, `BoardView` draws, `EventPlayer`
## plays back what happened, `BattleHud` and `DialogueBox` present, and
## `PlaytestMetrics` records. It implements none of their rules.
##
## The battle reports upward: `battle_finished` after the closing conversation has
## played, or `battle_abandoned` when the player leaves from the pause menu.

signal battle_finished(result: Dictionary)
signal battle_abandoned

const Mode := BattleSelection.Mode
const NONE := BattleSelection.NONE

@export_group("Mission")
## The map to fight on.
@export var mission: MissionDefinition
## The combatants: squad, neutral recruit and opposition.
@export var unit_profiles: UnitProfiles

@export_group("Gameplay Components")
@export var metrics: PlaytestMetrics
@export var audio_settings: AudioSettings
@export var audio: BattleAudio

@export_group("Presentation")
@export var board_view: BoardView
@export var camera: BattleCamera
@export var event_player: EventPlayer
@export var effects: EffectsLayer

@export_group("Interface")
@export var hud: BattleHud
@export var dialogue: DialogueBox
@export var pause_menu: PauseMenu

var battle: Battle
var selection := BattleSelection.new()


func _ready() -> void:
	hud.end_turn_requested.connect(end_turn)
	hud.action_chosen.connect(on_action)
	hud.back_requested.connect(cancel)
	hud.pause_requested.connect(open_pause)
	pause_menu.setup(audio_settings)
	pause_menu.opened.connect(_set_paused.bind(true))
	pause_menu.closed.connect(_set_paused.bind(false))
	pause_menu.main_menu_requested.connect(_abandon)


func _exit_tree() -> void:
	# Never leave the tree paused behind a battle that is going away.
	if get_tree().paused and pause_menu.is_open():
		get_tree().paused = false


# --- Pause ------------------------------------------------------------------------

## Pausing stops the whole battle: input, camera, playback and tweens. The pause
## menu and the music keep running.
func open_pause() -> void:
	if selection.mode != Mode.DONE:
		pause_menu.open()


func _set_paused(on: bool) -> void:
	get_tree().paused = on


func _abandon() -> void:
	pause_menu.close()
	audio.stop_music(0.0)
	battle_abandoned.emit()


## Starts a fresh battle. `intro` plays before the first Player Phase.
func start(seed_value := 0, intro: Array = []) -> void:
	battle = Battle.new(MissionSetup.build_board(mission, unit_profiles.definitions()), seed_value)
	battle.start()
	battle.take_events()
	board_view.setup(battle, selection)
	event_player.setup(battle)
	hud.setup(battle, selection, mission.objective_text)
	metrics.begin()
	camera.frame_map(board_view.map_rect(), board_view.tile_center(mission.camera_start_tile))
	audio.start_music()
	_refresh()
	selection.mode = Mode.BUSY
	if not intro.is_empty():
		await dialogue.play(intro)
	await hud.banner("Player Phase  -  Turn %d" % battle.turn)
	selection.mode = Mode.IDLE
	_refresh()


func _refresh() -> void:
	board_view.redraw()
	hud.refresh()


# --- Input ------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if battle == null or selection.mode == Mode.DONE:
		return
	# Esc with nothing to back out of opens the pause menu, even mid-playback.
	if event.is_action_pressed("ui_cancel") and selection.mode in [Mode.IDLE, Mode.BUSY]:
		open_pause()
		get_viewport().set_input_as_handled()
		return
	if selection.mode == Mode.BUSY:
		return
	if event is InputEventMouseMotion:
		var t := board_view.px_to_tile(get_global_mouse_position())
		if t != selection.hover:
			selection.hover = t
			if selection.mode == Mode.SELECTED and selection.move_set.has(t):
				audio.play("ui_move", -14.0)
			_on_hover()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_on_click(board_view.px_to_tile(get_global_mouse_position()))
		elif event.button_index == MOUSE_BUTTON_RIGHT:
			cancel()
	elif event.is_action_pressed("ui_cancel"):
		cancel()


## Re-reads the hovered tile (tools set `selection.hover` directly, then call this).
func refresh_hover() -> void:
	_on_hover()


func _on_hover() -> void:
	selection.hover_target = null
	match selection.mode:
		Mode.SELECTED:
			if selection.move_set.has(selection.hover):
				selection.forecast = Forecast.for_destination(battle, selection.selected, selection.hover)
			else:
				selection.forecast = {}
		Mode.TARGET:
			selection.hover_target = _target_at(selection.hover)
	_refresh()


func _on_click(t: Vector2i) -> void:
	match selection.mode:
		Mode.IDLE:
			if t == NONE:
				return
			var u := battle.board.unit_at(t)
			if u != null and u.can_activate():
				select(u)
			elif u != null and u.faction == Defs.Faction.ENEMY:
				selection.inspected_enemy = null if selection.inspected_enemy == u else u
				metrics.threat_inspections += 1
				_refresh()
			else:
				selection.inspected_enemy = null
				_refresh()
		Mode.SELECTED:
			if t == NONE:
				return
			var u := battle.board.unit_at(t)
			if u != null and u != selection.selected and u.can_activate() and not selection.move_set.has(t):
				select(u)
				return
			if selection.move_set.has(t):
				move_to(t)
		Mode.TARGET:
			var tgt: Variant = _target_at(t)
			if tgt != null:
				execute_target(tgt)


# --- Turn flow ----------------------------------------------------------------------

func select(u: Unit) -> void:
	audio.play("ui_select")
	selection.selected = u
	selection.inspected_enemy = null
	selection.move_set.clear()
	for a in battle.move_options(u):
		selection.move_set[a] = true
	metrics.record_selection(u, selection.move_set.size())
	selection.forecast = Forecast.for_destination(battle, u, u.pos)
	selection.mode = Mode.SELECTED
	_refresh()


func cancel() -> void:
	audio.play("ui_cancel")
	match selection.mode:
		Mode.SELECTED:
			selection.selected = null
			selection.forecast = {}
			selection.mode = Mode.IDLE
		Mode.MENU:
			var u := selection.selected
			if u.moved and not u.acted:
				battle.undo_move(u)
				battle.take_events()
				board_view.place(u)
			hud.hide_actions()
			select(u)
			return
		Mode.TARGET:
			_open_menu()
			return
	_refresh()


func move_to(t: Vector2i) -> void:
	var u := selection.selected
	selection.mode = Mode.BUSY
	if t != u.pos:
		battle.commit_move(u, t)
	else:
		battle.stay(u)
	await event_player.play(battle.take_events())
	_open_menu()


func _open_menu() -> void:
	selection.mode = Mode.MENU
	selection.forecast = Forecast.for_destination(battle, selection.selected, selection.selected.pos)
	hud.show_actions(selection.selected, _action_list(selection.selected))
	_refresh()


## [{id, label, enabled, tooltip}]
func _action_list(u: Unit) -> Array:
	var out: Array = []
	var can_attack := not battle.basic_targets(u).is_empty() or not battle.object_targets(u).is_empty()
	out.append({"id": "attack", "label": "Attack", "enabled": can_attack, "tooltip": "Basic Attack, 0 Noise"})
	for a in u.arts:
		var art := Arts.get_art(a)
		var chk := battle.art_check(u, a)
		var label := "%s  (+%d)" % [art.name, art.noise]
		var tip: String = art.desc if chk.ok else "%s\n%s" % [chk.reason, art.desc]
		if chk.ok and art.noise > 0 and battle.noise + art.noise >= Defs.NOISE_THRESHOLD:
			label += "  TRIGGERS GAZE"
			tip += "\nNoise reaches %d: the human looks at a 3x3 area around %s." % [Defs.NOISE_THRESHOLD, u.name]
		out.append({"id": "art:" + a, "label": label, "enabled": chk.ok, "tooltip": tip})
	if u.item != "":
		var it: Dictionary = Arts.ITEMS[u.item]
		out.append({"id": "item", "label": it.name, "enabled": u.hp < u.max_hp, "tooltip": it.desc})
	if not battle.talk_targets(u).is_empty():
		out.append({"id": "talk", "label": "Talk", "enabled": true, "tooltip": "Recruit Umbrella. Uses the Action."})
	out.append({"id": "wait", "label": "Wait", "enabled": true, "tooltip": "End this unit's activation."})
	return out


func on_action(id: String) -> void:
	if selection.mode != Mode.MENU:
		return
	var u := selection.selected
	hud.hide_actions()
	match id:
		"wait":
			battle.wait(u)
			await _after_action()
		"item":
			battle.use_item(u)
			await _after_action()
		"attack":
			selection.target_kind = "attack"
			selection.target_options = battle.basic_targets(u)
			selection.target_options.append_array(battle.object_targets(u))
			selection.mode = Mode.TARGET
		"talk":
			selection.target_kind = "talk"
			selection.target_options = battle.talk_targets(u)
			selection.mode = Mode.TARGET
		_:
			var art_id := id.substr(4)
			if Arts.get_art(art_id).target == "self":
				battle.use_art(u, art_id, u)
				await _after_action()
				return
			selection.target_kind = id
			selection.target_options = battle.art_targets(u, art_id)
			selection.mode = Mode.TARGET
	_refresh()


## Maps a hovered tile to a target option: a Unit, a cover tile, or a direction.
func _target_at(t: Vector2i) -> Variant:
	if t == NONE:
		return null
	var directional := selection.is_art_kind("direction")
	for o in selection.target_options:
		if o is Unit and o.occupies(t):
			return o
		if o is Vector2i and directional:
			if Arts.cone_tiles(selection.selected, selection.selected.pos, o).has(t):
				return o
		elif o is Vector2i and o == t:
			return o
	return null


func execute_target(tgt: Variant) -> void:
	var u := selection.selected
	selection.mode = Mode.BUSY
	match selection.target_kind:
		"attack":
			if tgt is Unit:
				battle.attack(u, tgt)
			else:
				battle.attack_object(u, tgt)
		"talk":
			battle.talk(u, tgt)
		_:
			battle.use_art(u, selection.target_kind.substr(4), tgt)
	await _after_action()


func _after_action() -> void:
	selection.mode = Mode.BUSY
	await event_player.play(battle.take_events())
	selection.clear_action()
	if await _check_finished():
		return
	selection.mode = Mode.IDLE
	_refresh()
	if battle.all_player_done():
		hud.pulse_end_turn()


func end_turn() -> void:
	if not selection.can_end_turn():
		return
	selection.clear_action()
	selection.mode = Mode.BUSY
	_refresh()
	await hud.banner("Enemy Phase")
	var predicted := {}
	for u in battle.player_units():
		if not u.frozen:
			predicted[u] = Forecast.for_destination(battle, u, u.pos).predicted_hp
	battle.end_player_phase()
	metrics.record_predictions(predicted)
	await event_player.play(battle.take_events())
	if await _check_finished():
		return
	selection.mode = Mode.IDLE
	_refresh()


func _check_finished() -> bool:
	if battle.phase != Defs.Phase.VICTORY and battle.phase != Defs.Phase.DEFEAT:
		return false
	selection.mode = Mode.DONE
	camera.input_enabled = false
	_refresh()
	var victory := battle.phase == Defs.Phase.VICTORY
	var result := {
		"victory": victory,
		"turns": battle.turn,
		"stars": battle.stars(),
		"stats": battle.stats.duplicate(),
		"broken": battle.board.units.filter(func(u): return u.faction == Defs.Faction.PLAYER and u.broken).map(func(u): return u.name),
		"recruited": battle.recruited,
		"metrics": metrics.summary(battle),
	}
	audio.stop_music()
	audio.play("victory" if victory else "defeat", 0.0)
	await hud.banner("Victory" if victory else "Defeat")
	await dialogue.play(_closing_lines(result))
	metrics.save(result.metrics)
	battle_finished.emit(result)
	return true


func _closing_lines(result: Dictionary) -> Array:
	if not result.victory:
		return SliceDialogue.DEFEAT
	var lines: Array = SliceDialogue.VICTORY.duplicate()
	if result.recruited and result.stars.recruit:
		lines.append_array(SliceDialogue.VICTORY_WITH_UMBRELLA)
	return lines
