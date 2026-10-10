class_name BattleRoot
extends Node3D

## Composition root of one tactical battle. It owns the player's turn flow and
## coordinates the peers that do the work: `Battle` resolves the rules, `Diorama`
## and the unit cards show the room, `GroundOverlays` and `ThreatArcs` paint the
## forecast, `EventPlayer` plays back what happened, and the interface presents.
## It implements none of their rules.
##
## The flow (Mario + Rabbids: Sparks of Hope style):
##   IDLE     free camera. Click a unit, or Tab / RB, to take control of it.
##   CONTROL  steer it anywhere inside its movement area (WASD / left stick, or
##            click a spot). Enemy arcs and the predicted HP follow it. Z / X undoes
##            the move, Esc / B lets go, Space / A opens the action ring.
##   MENU     the action ring above the unit.
##   TARGET   pick a target (left/right, or click) or aim a cone; the battle preview
##            shows the whole exchange. Confirm to act; any action ends the turn.
##
## The battle reports upward: `battle_finished` after the closing conversation, or
## `battle_abandoned` when the player leaves from the pause menu.

signal battle_finished(result: Dictionary)
signal battle_abandoned

const Mode := BattleSelection.Mode

@export_group("Mission")
@export var mission: MissionDefinition
@export var unit_profiles: UnitProfiles

@export_group("Gameplay Components")
@export var metrics: PlaytestMetrics
@export var audio: BattleAudio
@export var audio_settings: AudioSettings
@export var display_settings: DisplaySettings
@export var speed_settings: BattleSpeedSettings

@export_group("World")
@export var camera: BattleCamera
@export var diorama: Diorama
@export var units_root: Node3D
@export var overlays: GroundOverlays
@export var arcs: ThreatArcs
@export var effects: EffectsLayer
@export var event_player: EventPlayer

@export_group("Interface")
@export var hud: BattleHud
@export var plates: UnitPlates
@export var ring: ActionRing
@export var preview: BattlePreview
@export var dialogue: DialogueBox
@export var pause_menu: PauseMenu

@export_group("Control")
## Metres per second a controlled unit moves: the pace the run clips are authored
## for, so feet match the floor.
@export var move_speed := 1.8
## Degrees a cone turns per left/right press while aiming with keys or the D-pad.
@export var aim_step_degrees := 20.0
## Extra metres around a unit's body that still count as clicking it.
@export var click_slack := 0.25

var battle: Battle
var selection := BattleSelection.new()
var cards: Dictionary = {} # unit id -> UnitCard

var _threats: Forecast.ThreatMap
var _forecast_at := Vector2.INF
var _walk_path: Array[Vector2] = []
var _was_moving := false


func _ready() -> void:
	hud.end_turn_requested.connect(end_turn)
	hud.minimap.focus_requested.connect(func(p: Vector2) -> void: camera.look_at_point(BattleSpace.to_world(p)))
	ring.chosen.connect(choose_action)
	ring.cancelled.connect(_close_menu)
	ring.hovered.connect(_show_action_reach)
	preview.shown_changed.connect(func(on: bool) -> void: hud.set_bottom_visible(not on))
	pause_menu.setup(audio_settings, display_settings, speed_settings)
	pause_menu.opened.connect(_set_paused.bind(true))
	pause_menu.closed.connect(_set_paused.bind(false))
	pause_menu.main_menu_requested.connect(_abandon)


func _exit_tree() -> void:
	if get_tree().paused and pause_menu.is_open():
		get_tree().paused = false


## Starts a fresh battle. `intro` plays before the first Player Phase.
func start(seed_value := 0, intro: Array = []) -> void:
	battle = Battle.new(MissionSetup.build_field(mission, unit_profiles.definitions()), seed_value)
	battle.start()
	battle.take_events()
	diorama.setup(battle.field, mission)
	for u in battle.field.units:
		var c := UnitCard.new()
		c.name = u.id
		units_root.add_child(c)
		c.setup(u)
		cards[u.id] = c
	overlays.setup(battle)
	event_player.setup(battle, cards)
	hud.setup(battle, mission.objective_text)
	hud.minimap.setup(battle, camera)
	plates.setup(cards)
	metrics.begin()
	camera.frame_map(battle.field.size, BattleSpace.to_world(MissionSetup.tile_center(mission.camera_start_tile)))
	camera.set_room(diorama.room_bounds())
	audio.start_music()
	selection.mode = Mode.BUSY
	_update_hint()
	if not intro.is_empty():
		await dialogue.play(intro)
	await hud.banner("Player Phase  -  Turn %d" % battle.turn)
	selection.mode = Mode.IDLE
	_update_hint()


func card_of(u: Unit) -> UnitCard:
	return cards[u.id]


# --- Pause ------------------------------------------------------------------------

func open_pause() -> void:
	if selection.mode != Mode.DONE:
		pause_menu.open()


func _set_paused(on: bool) -> void:
	get_tree().paused = on


func _abandon() -> void:
	pause_menu.close()
	audio.stop_music(0.0)
	battle_abandoned.emit()


# --- Per frame ----------------------------------------------------------------------

func _process(delta: float) -> void:
	if battle == null or selection.mode != Mode.CONTROL:
		return
	var u := selection.controlled
	var c := card_of(u)
	var from := u.pos
	var stick := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var want := from
	if stick.length() > 0.05:
		_walk_path.clear()
		want = from + camera.floor_direction(stick).normalized() * move_speed * delta * minf(stick.length(), 1.0)
	elif not _walk_path.is_empty():
		var next := _walk_path[0]
		var step := move_speed * delta
		if from.distance_to(next) <= step:
			want = next
			_walk_path.remove_at(0)
		else:
			want = from + (next - from).normalized() * step
	var moving := false
	if want != from:
		var to := _slide(u, from, want)
		if to.distance_to(from) > 0.0005 and battle.move_unit(u, to):
			c.position = BattleSpace.to_world(to)
			c.face_along(to - from)
			moving = true
		else:
			_walk_path.clear()
	if moving != _was_moving:
		c.set_moving(moving)
		_was_moving = moving
	if u.pos.distance_to(_forecast_at) > 0.05:
		_refresh_forecast()


## Moves as far toward `want` as the area allows, sliding along its edge.
func _slide(u: Unit, from: Vector2, want: Vector2) -> Vector2:
	var r := battle.reach(u)
	if r.can_reach(want):
		return want
	for alt in [Vector2(want.x, from.y), Vector2(from.x, want.y)]:
		if alt != from and r.can_reach(alt):
			return alt
	return r.clamp_step(from, want)


func _refresh_forecast() -> void:
	var u := selection.controlled
	if u == null:
		return
	if _threats == null or _threats.unit != u or not _threats.is_current():
		_threats = Forecast.ThreatMap.new(battle, u)
	selection.forecast = Forecast.for_destination(battle, u, u.pos, _threats)
	_forecast_at = u.pos
	arcs.show_forecast(selection.forecast, u, u.pos)
	plates.set_prediction(u, selection.forecast.predicted_hp, selection.forecast.risk)
	overlays.show_trail(battle.reach(u).path_to(u.pos))


# --- Input ------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if battle == null or selection.mode == Mode.DONE:
		return
	if event.is_action_pressed("pause") or (event.is_action_pressed("cancel") and selection.mode in [Mode.IDLE, Mode.BUSY]):
		open_pause()
		get_viewport().set_input_as_handled()
		return
	if selection.mode == Mode.BUSY or selection.mode == Mode.MENU:
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var p := _floor_under_mouse(event.position)
		if p != Vector2.INF:
			_on_click(p)
		return
	if event is InputEventMouseMotion and selection.mode == Mode.TARGET:
		var p := _floor_under_mouse(event.position)
		if p != Vector2.INF:
			_on_target_hover(p)
		return
	var handled := true
	match selection.mode:
		Mode.IDLE:
			if event.is_action_pressed("next_unit") or event.is_action_pressed("confirm"):
				_cycle_unit(1)
			elif event.is_action_pressed("prev_unit"):
				_cycle_unit(-1)
			elif event.is_action_pressed("end_turn"):
				end_turn()
			else:
				handled = false
		Mode.CONTROL:
			if event.is_action_pressed("confirm"):
				open_menu()
			elif event.is_action_pressed("cancel"):
				release()
			elif event.is_action_pressed("undo_move"):
				undo()
			elif event.is_action_pressed("next_unit"):
				_cycle_unit(1)
			elif event.is_action_pressed("prev_unit"):
				_cycle_unit(-1)
			elif event.is_action_pressed("end_turn"):
				end_turn()
			else:
				handled = false
		Mode.TARGET:
			if event.is_action_pressed("confirm"):
				execute()
			elif event.is_action_pressed("cancel"):
				_back_to_menu()
			elif event.is_action_pressed("ring_left") or (event is InputEventJoypadMotion and event.is_action_pressed("move_left")):
				_step_target(-1)
			elif event.is_action_pressed("ring_right") or (event is InputEventJoypadMotion and event.is_action_pressed("move_right")):
				_step_target(1)
			else:
				handled = false
	if handled:
		get_viewport().set_input_as_handled()


func _floor_under_mouse(screen: Vector2) -> Vector2:
	var cam := camera.camera
	var origin := cam.project_ray_origin(screen)
	var dir := cam.project_ray_normal(screen)
	if absf(dir.y) < 0.0001:
		return Vector2.INF
	var t := -origin.y / dir.y
	if t < 0.0:
		return Vector2.INF
	return BattleSpace.to_floor(origin + dir * t)


func _unit_near(p: Vector2) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u in battle.field.living_units():
		var d := u.pos.distance_to(p) - u.radius
		if d <= click_slack and d < best_d:
			best = u
			best_d = d
	return best


func _on_click(p: Vector2) -> void:
	var u := _unit_near(p)
	match selection.mode:
		Mode.IDLE, Mode.CONTROL:
			if u != null and u == selection.controlled:
				open_menu()
			elif u != null and u.can_activate():
				control(u)
			elif u != null and u.faction == Defs.Faction.ENEMY:
				_inspect(u)
			elif selection.mode == Mode.CONTROL:
				var c := selection.controlled
				if battle.reach(c).can_reach(p):
					# Walk there from where the unit stands now; each step is still
					# checked against the area measured from where its move began.
					var from_here := ReachField.compute(battle.field, c, c.pos, battle.field.size.length())
					_walk_path = from_here.path_to(p)
					if not _walk_path.is_empty():
						_walk_path.remove_at(0)
		Mode.TARGET:
			if selection.is_aiming():
				execute()
				return
			if selection.is_placing():
				selection.spot = battle.area_for(selection.controlled, selection.action.substr(4), p).center
				execute()
				return
			for k in selection.targets.size():
				var t: Variant = selection.targets[k]
				var hit: bool = (t is Unit and t == u) or (t is String and battle.field.objects.has(t) and battle.field.objects[t].rect.grow(0.2).has_point(p))
				if hit:
					if k == selection.target_index:
						execute()
					else:
						selection.target_index = k
						_refresh_target()
					return


func _on_target_hover(p: Vector2) -> void:
	if selection.is_aiming():
		var d := p - selection.controlled.pos
		if d.length() > 0.2:
			selection.aim = d.normalized()
			_refresh_target()
		return
	if selection.is_placing():
		selection.spot = p
		_refresh_target()
		return
	var u := _unit_near(p)
	if u != null and selection.targets.has(u):
		var k := selection.targets.find(u)
		if k != selection.target_index:
			selection.target_index = k
			_refresh_target()


# --- Control ------------------------------------------------------------------------

func control(u: Unit) -> void:
	if not u.can_activate():
		return
	if selection.mode == Mode.CONTROL and selection.controlled != null:
		card_of(selection.controlled).set_moving(false)
	audio.play("ui_select")
	selection.controlled = u
	selection.inspected_enemy = null
	selection.mode = Mode.CONTROL
	_walk_path.clear()
	_was_moving = false
	overlays.hide_enemy_reach()
	var r := battle.reach(u)
	overlays.show_move_area(r, u.turn_start, u.radius)
	metrics.record_selection(u, r.standing_spots(0.5).size())
	camera.follow = card_of(u)
	camera.free_pan = false
	hud.minimap.set_controlled(u)
	_threats = null
	_forecast_at = Vector2.INF
	_refresh_forecast()
	_update_hint()


func release() -> void:
	if selection.controlled != null:
		card_of(selection.controlled).set_moving(false)
	selection.controlled = null
	selection.mode = Mode.IDLE
	selection.clear_action()
	_walk_path.clear()
	arcs.clear()
	plates.set_prediction(null)
	overlays.hide_all()
	preview.hide_preview()
	ring.close()
	camera.follow = null
	camera.free_pan = true
	hud.minimap.set_controlled(null)
	_update_hint()


func undo() -> void:
	var u := selection.controlled
	if u == null or u.acted:
		return
	audio.play("ui_cancel")
	_walk_path.clear()
	battle.undo_move(u)
	battle.take_events()
	card_of(u).position = BattleSpace.to_world(u.pos)
	_refresh_forecast()


func _cycle_unit(step: int) -> void:
	var ready := battle.player_units().filter(func(o: Unit) -> bool: return o.can_activate())
	if ready.is_empty():
		hud.pulse_end_turn()
		return
	var k := ready.find(selection.controlled)
	k = 0 if k < 0 and step > 0 else posmod(k + step, ready.size())
	control(ready[k])


func _inspect(e: Unit) -> void:
	if selection.inspected_enemy == e:
		selection.inspected_enemy = null
		overlays.hide_enemy_reach()
		return
	selection.inspected_enemy = e
	metrics.threat_inspections += 1
	overlays.show_enemy_reach(ReachField.compute(battle.field, e, e.pos, battle.effective_move(e)))


# --- Action ring ------------------------------------------------------------------

func open_menu() -> void:
	var u := selection.controlled
	if u == null:
		return
	_walk_path.clear()
	card_of(u).set_moving(false)
	_was_moving = false
	selection.mode = Mode.MENU
	var actions := _action_list(u)
	ring.open(card_of(u), 1.9 if u.is_large() else 1.05, actions, selection.ring_memory.get(u.id, 0))
	audio.play("ui_select")
	_update_hint()


## While an action is hovered on the ring, its reach is drawn around the unit.
## Actions with no reach to speak of (Wait, items, Talk, self-only Arts) show none.
func _show_action_reach(id: String) -> void:
	var u := selection.controlled
	if u == null or not _has_reach(id):
		overlays.hide_reach_ring()
		return
	var friendly: bool = id.begins_with("art:") and Arts.get_art(id.substr(4)).target == "ally"
	overlays.show_reach_ring(u.pos, _reach_radius(u, id), friendly)


func _has_reach(id: String) -> bool:
	if id == "attack":
		return true
	if not id.begins_with("art:"):
		return false
	var art := Arts.get_art(id.substr(4))
	return art.target != "self" or art.has("radius")


func _close_menu() -> void:
	overlays.hide_reach_ring()
	ring.close()
	audio.play("ui_cancel")
	selection.mode = Mode.CONTROL
	_update_hint()


## [{id, label, enabled, tooltip, icon, noise?, reason?, triggers_gaze?}]
func _action_list(u: Unit) -> Array:
	var out: Array = []
	var can_attack := not battle.basic_targets(u).is_empty() or not battle.object_targets(u).is_empty()
	out.append({"id": "attack", "label": "Attack", "icon": "attack", "enabled": can_attack, "noise": 0,
		"reason": "Nothing within reach", "tooltip": "Basic Attack. Reach %.1f m, Might %d. Makes no Noise." % [u.attack_range, u.might]})
	for a in u.arts:
		var art := Arts.get_art(a)
		var chk := battle.art_check(u, a)
		out.append({"id": "art:" + a, "label": art.name, "icon": a, "enabled": chk.ok, "noise": art.noise,
			"reason": chk.reason, "tooltip": art.desc,
			"triggers_gaze": chk.ok and art.noise > 0 and battle.noise + art.noise >= Defs.NOISE_THRESHOLD})
	if u.item != "":
		var it: Dictionary = Arts.ITEMS[u.item]
		out.append({"id": "item", "label": it.name, "icon": "item", "enabled": u.hp < u.max_hp,
			"reason": "Already at full HP", "tooltip": it.desc})
	if not battle.talk_targets(u).is_empty():
		out.append({"id": "talk", "label": "Talk", "icon": "talk", "enabled": true, "tooltip": "Recruit Umbrella. Uses the Action."})
	out.append({"id": "wait", "label": "Wait", "icon": "wait", "enabled": true, "tooltip": "End this unit's turn where it stands."})
	return out


## What happens when an action is picked on the ring (tests call this directly).
func choose_action(id: String) -> void:
	var u := selection.controlled
	selection.ring_memory[u.id] = _action_list(u).map(func(a): return a.id).find(id)
	ring.close()
	match id:
		"wait":
			battle.wait(u)
			await _after_action()
			return
		"item":
			battle.use_item(u)
			await _after_action()
			return
	if id.begins_with("art:") and Arts.get_art(id.substr(4)).target == "self" and not Arts.get_art(id.substr(4)).has("radius"):
		battle.use_art(u, id.substr(4), u)
		await _after_action()
		return
	selection.action = id
	selection.target_index = 0
	match id:
		"attack":
			selection.targets = battle.basic_targets(u)
			selection.targets.append_array(battle.object_targets(u))
		"talk":
			selection.targets = battle.talk_targets(u)
		_:
			var art := Arts.get_art(id.substr(4))
			if art.target == "direction":
				selection.targets = []
				selection.aim = _default_aim(u)
			elif art.target == "self":
				selection.targets = [u]  # a circle round the user: shown, then confirmed
			elif art.target == "area":
				selection.targets = battle.art_targets(u, id.substr(4))
				# start on the nearest ally rather than on the user
				selection.target_index = 1 if selection.targets.size() > 1 else 0
				selection.spot = selection.targets[selection.target_index]
			else:
				selection.targets = battle.art_targets(u, id.substr(4))
	selection.mode = Mode.TARGET
	audio.play("ui_select")
	_refresh_target()
	_update_hint()


func _default_aim(u: Unit) -> Vector2:
	var best := Vector2.RIGHT * float(u.facing)
	var bd := INF
	for e in battle.enemy_units():
		if battle.can_target(u, e) and u.gap_to(e) < bd:
			bd = u.gap_to(e)
			best = (e.pos - u.pos).normalized()
	return best


func _back_to_menu() -> void:
	selection.clear_action()
	overlays.hide_reach_ring()
	overlays.hide_cone()
	overlays.hide_area()
	overlays.clear_targets()
	preview.hide_preview()
	open_menu()


func _step_target(step: int) -> void:
	if selection.is_aiming():
		selection.aim = selection.aim.rotated(deg_to_rad(aim_step_degrees) * -step)
	elif not selection.targets.is_empty():
		selection.target_index = posmod(selection.target_index + step, selection.targets.size())
		if selection.is_placing():
			selection.spot = selection.targets[selection.target_index]
	audio.play("ui_move", -12.0)
	_refresh_target()


func _refresh_target() -> void:
	var u := selection.controlled
	var id := selection.action
	var friendly := selection.is_friendly_action()
	overlays.show_reach_ring(u.pos, _reach_radius(u, id), friendly)
	var target: Variant
	if selection.is_aiming():
		var cone := battle.cone_for(u, id.substr(4), selection.aim)
		overlays.show_cone(cone)
		overlays.show_targets(battle.units_in_cone(u, cone).filter(func(o): return battle.can_target(u, o)), null)
		target = selection.aim
	elif selection.is_self_area():
		var around := battle.around(u, id.substr(4))
		overlays.show_area(around)
		overlays.show_targets(battle.storm_targets(u, around), null)
		target = u
	elif selection.is_placing():
		var area := battle.area_for(u, id.substr(4), selection.spot)
		selection.spot = area.center
		overlays.show_area(area)
		overlays.show_targets(battle.units_in_area(area).filter(func(o): return o.faction == u.faction and not o.frozen), null, true)
		target = selection.spot
		if selection.spot.distance_to(u.pos) > 0.05:
			card_of(u).face_along(selection.spot - u.pos)
	else:
		overlays.hide_cone()
		overlays.hide_area()
		target = selection.current_target()
		overlays.show_targets(selection.targets, target, friendly)
	if target == null:
		preview.hide_preview()
		return
	if target is Unit:
		card_of(u).face_along(target.pos - u.pos)
	preview.show_exchange(Exchange.preview(battle, u, id, target))


func _reach_radius(u: Unit, id: String) -> float:
	if id == "attack":
		return u.radius + u.attack_range
	if id == "talk":
		return u.radius + Defs.ADJACENT_GAP
	var art := Arts.get_art(id.substr(4))
	if art.target == "self" and art.has("radius"):
		return float(art.radius)
	match art.target:
		"direction":
			return u.radius + float(art.length)
		"lunge":
			return u.radius + float(art.dash)
	return u.radius + float(art.get("max", 0.0))


func execute() -> void:
	var u := selection.controlled
	var target: Variant = selection.current_target()
	if selection.is_aiming():
		target = selection.aim
	elif selection.is_placing():
		target = selection.spot
	if target == null:
		return
	selection.mode = Mode.BUSY
	overlays.hide_all()
	preview.hide_preview()
	arcs.clear()
	plates.set_prediction(null)
	match selection.action:
		"attack":
			if target is Unit:
				battle.attack(u, target)
			else:
				battle.attack_object(u, target)
		"talk":
			battle.talk(u, target)
		_:
			battle.use_art(u, selection.action.substr(4), target)
	await _after_action()


func _after_action() -> void:
	selection.mode = Mode.BUSY
	overlays.hide_all()
	preview.hide_preview()
	arcs.clear()
	plates.set_prediction(null)
	_update_hint()
	await event_player.play(battle.take_events())
	release()
	if await _check_finished():
		return
	selection.mode = Mode.IDLE
	_update_hint()
	if battle.all_player_done():
		hud.pulse_end_turn()


# --- Phases -------------------------------------------------------------------------

func end_turn() -> void:
	if selection.mode != Mode.IDLE and selection.mode != Mode.CONTROL:
		return
	release()
	selection.mode = Mode.BUSY
	_update_hint()
	var home := camera.focus
	await hud.banner("Enemy Phase")
	var predicted := {}
	for u in battle.player_units():
		if not u.frozen:
			predicted[u] = Forecast.for_destination(battle, u, u.pos).predicted_hp
	battle.end_player_phase()
	metrics.record_predictions(predicted)
	await event_player.play(battle.take_events())
	await camera.glide_to(home)
	if await _check_finished():
		return
	selection.mode = Mode.IDLE
	_update_hint()


func _check_finished() -> bool:
	if battle.phase != Defs.Phase.VICTORY and battle.phase != Defs.Phase.DEFEAT:
		return false
	selection.mode = Mode.DONE
	camera.input_enabled = false
	_update_hint()
	var victory := battle.phase == Defs.Phase.VICTORY
	var result := {
		"victory": victory,
		"turns": battle.turn,
		"stars": battle.stars(),
		"stats": battle.stats.duplicate(),
		"broken": battle.field.units.filter(func(u): return u.faction == Defs.Faction.PLAYER and u.broken).map(func(u): return u.name),
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


func _update_hint() -> void:
	hud.set_end_turn_enabled(selection.mode == Mode.IDLE or selection.mode == Mode.CONTROL)
	match selection.mode:
		Mode.IDLE:
			hud.set_hint("Click a unit or Tab / RB to take control   ·   WASD pan   ·   Q E / right-drag orbit   ·   wheel zoom   ·   T end turn")
		Mode.CONTROL:
			hud.set_hint("WASD / stick or click to move   ·   Space / A actions   ·   Z / X undo move   ·   Tab next unit   ·   Esc let go")
		Mode.MENU:
			hud.set_hint("◀ ▶ turn the ring   ·   Space / A choose   ·   Esc / B back")
		Mode.TARGET:
			hud.set_hint("◀ ▶ or mouse to change target   ·   Space / A confirm   ·   Esc / B back")
		_:
			hud.set_hint("")
