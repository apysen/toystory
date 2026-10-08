class_name BattleView
extends Node2D
## Battle screen: board rendering, input, movement forecast, combat forecast,
## HUD, and playback of Battle events. Art falls back to graybox when the
## sprites aren't in the project yet.

signal battle_finished(result: Dictionary)

const T := Defs.TILE_SIZE
const MAP_ORIGIN := Vector2(16, 48)
const NONE := Vector2i(-99, -99)

enum Mode { IDLE, SELECTED, MENU, TARGET, BUSY, DONE }

var battle: Battle
var mode := Mode.IDLE
var selected: Unit = null
var hover := NONE
var target_kind := "" # "attack", "art:<id>", "talk"
var target_options: Array = []
var hover_target: Variant = null
var move_set := {}
var forecast := {}
var inspected_enemy: Unit = null
var flash_tiles := {} # tile -> Color, short-lived area effects

var _views := {} # unit id -> UnitView
var _floor: Node2D
var _overlay: Node2D
var _units_layer: Node2D
var _top: Node2D
var _hud: BattleHud
var _dialogue: DialogueBox
var _env: Dictionary = {}
var _props: Array = []
var destroyed_cover := {} # tile -> kind
var _camera: Camera2D
var sfx: Sfx
## Playtest metrics (vertical_slice_plan.md section 26).
var metrics := {"threat_inspections": 0, "hp_errors": [], "vacuum_blocked": 0, "started_ms": 0}


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_env = EnvArt.load_all()
	sfx = Sfx.new()
	add_child(sfx)
	_floor = _layer("Floor", _draw_floor)
	_overlay = _layer("Overlay", _draw_overlay)
	_units_layer = Node2D.new()
	_units_layer.name = "Units"
	_units_layer.y_sort_enabled = true
	add_child(_units_layer)
	_top = _layer("Top", _draw_top)
	var ui := CanvasLayer.new()
	add_child(ui)
	_hud = BattleHud.new()
	_hud.view = self
	ui.add_child(_hud)
	_dialogue = DialogueBox.new()
	ui.add_child(_dialogue)


func _layer(n: String, fn: Callable) -> Node2D:
	var node := Node2D.new()
	node.name = n
	node.draw.connect(fn.bind(node))
	add_child(node)
	return node


## Starts a fresh battle. `intro` plays before the first Player Phase.
func start(seed_value := 0, intro: Array = []) -> void:
	battle = Battle.new(UnderTheDesk.build_board(), seed_value)
	for u in battle.board.units:
		var v := UnitView.new()
		v.setup(u)
		_units_layer.add_child(v)
		_views[u.id] = v
		_place(v, u.pos)
	battle.start()
	battle.take_events()
	metrics.started_ms = Time.get_ticks_msec()
	_sync_props()
	_setup_camera()
	_sync_all()
	mode = Mode.BUSY
	if not intro.is_empty():
		await _dialogue.play(intro)
	await _hud.banner("Player Phase  -  Turn %d" % battle.turn)
	mode = Mode.IDLE
	_refresh()


func _setup_camera() -> void:
	_camera = Camera2D.new()
	var map := Rect2(MAP_ORIGIN, Vector2(battle.board.width, battle.board.height) * T)
	_camera.limit_left = int(map.position.x - 48)
	_camera.limit_top = int(map.position.y - 64)
	_camera.limit_right = int(map.end.x + BattleHud.PANEL_W + 32)
	_camera.limit_bottom = int(map.end.y + 48)
	_camera.position = tile_center(Vector2i(4, 3))
	add_child(_camera)
	_camera.make_current()


func _process(dt: float) -> void:
	if _camera == null or mode == Mode.DONE:
		return
	var dir := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		dir.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		dir.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		dir.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		dir.y += 1
	if dir != Vector2.ZERO:
		_pan(dir * 900.0 * dt / _camera.zoom.x)


func _pan(delta: Vector2) -> void:
	_camera.position += delta
	var half := get_viewport_rect().size / (2.0 * _camera.zoom.x)
	_camera.position.x = clampf(_camera.position.x, _camera.limit_left + half.x, maxf(_camera.limit_right - half.x, _camera.limit_left + half.x))
	_camera.position.y = clampf(_camera.position.y, _camera.limit_top + half.y, maxf(_camera.limit_bottom - half.y, _camera.limit_top + half.y))


func _set_camera_pos(p: Vector2) -> void:
	_camera.position = p
	_pan(Vector2.ZERO)


## Centre the camera on a unit if it's off screen (enemy phase playback).
func _follow(u: Unit) -> void:
	if _camera == null:
		return
	var p := unit_center(u, u.pos)
	var half := get_viewport_rect().size / (2.0 * _camera.zoom.x)
	var view_rect := Rect2(_camera.position - half, half * 2).grow(-T * 0.75)
	if not view_rect.has_point(p):
		var tw := create_tween()
		tw.tween_method(_set_camera_pos, _camera.position, p, 0.25)
		await tw.finished


# --- Coordinates ----------------------------------------------------------------

func tile_rect(t: Vector2i) -> Rect2:
	return Rect2(MAP_ORIGIN + Vector2((t.x - 1) * T, (battle.board.height - t.y) * T), Vector2(T, T))


func tile_center(t: Vector2i) -> Vector2:
	return tile_rect(t).get_center()


func unit_center(u: Unit, anchor: Vector2i) -> Vector2:
	var a := tile_rect(anchor)
	var s := u.size * T
	return Vector2(a.position.x + s / 2.0, a.end.y - s / 2.0)


## Bottom-centre of the footprint: where the unit's feet go.
func foot_point(u: Unit, anchor: Vector2i) -> Vector2:
	var a := tile_rect(anchor)
	return Vector2(a.position.x + u.size * T / 2.0, a.end.y - 4)


func px_to_tile(p: Vector2) -> Vector2i:
	var local := p - MAP_ORIGIN
	if local.x < 0 or local.y < 0:
		return NONE
	var t := Vector2i(int(local.x / T) + 1, battle.board.height - int(local.y / T))
	return t if battle.board.in_bounds(t) else NONE


func _place(v: UnitView, anchor: Vector2i) -> void:
	v.position = foot_point(v.unit, anchor)


# --- Input ------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if battle == null or mode == Mode.DONE:
		return
	if _camera != null:
		if event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			_pan(-event.relative / _camera.zoom.x)
			return
		if event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			var z := _camera.zoom.x + (0.25 if event.button_index == MOUSE_BUTTON_WHEEL_UP else -0.25)
			z = clampf(z, 0.5, 1.0)
			_camera.zoom = Vector2(z, z)
			_pan(Vector2.ZERO)
			return
	if mode == Mode.BUSY:
		return
	if event is InputEventMouseMotion:
		var t := px_to_tile(get_global_mouse_position())
		if t != hover:
			hover = t
			if mode == Mode.SELECTED and move_set.has(t):
				sfx.play("ui_move", -14.0)
			_on_hover()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_on_click(px_to_tile(get_global_mouse_position()))
		elif event.button_index == MOUSE_BUTTON_RIGHT:
			cancel()
	elif event.is_action_pressed("ui_cancel"):
		cancel()


func _on_hover() -> void:
	hover_target = null
	match mode:
		Mode.SELECTED:
			if move_set.has(hover):
				forecast = Forecast.for_destination(battle, selected, hover)
			else:
				forecast = {}
		Mode.TARGET:
			hover_target = _target_at(hover)
	_refresh()


func _on_click(t: Vector2i) -> void:
	match mode:
		Mode.IDLE:
			if t == NONE:
				return
			var u := battle.board.unit_at(t)
			if u != null and u.can_activate():
				select(u)
			elif u != null and u.faction == Defs.Faction.ENEMY:
				inspected_enemy = null if inspected_enemy == u else u
				metrics.threat_inspections += 1
				_refresh()
			else:
				inspected_enemy = null
				_refresh()
		Mode.SELECTED:
			if t == NONE:
				return
			var u := battle.board.unit_at(t)
			if u != null and u != selected and u.can_activate() and not move_set.has(t):
				select(u)
				return
			if move_set.has(t):
				_move_to(t)
		Mode.TARGET:
			var tgt: Variant = _target_at(t)
			if tgt != null:
				_execute_target(tgt)
		Mode.MENU:
			pass


func select(u: Unit) -> void:
	sfx.play("ui_select")
	selected = u
	inspected_enemy = null
	move_set.clear()
	for a in battle.move_options(u):
		move_set[a] = true
	if u.is_large() and move_set.size() <= 3:
		metrics.vacuum_blocked += 1
	forecast = Forecast.for_destination(battle, u, u.pos)
	mode = Mode.SELECTED
	_refresh()


func cancel() -> void:
	sfx.play("ui_cancel")
	match mode:
		Mode.SELECTED:
			selected = null
			forecast = {}
			mode = Mode.IDLE
		Mode.MENU:
			if selected.moved and not selected.acted:
				battle.undo_move(selected)
				battle.take_events()
				_place(_views[selected.id], selected.pos)
			select(selected)
			return
		Mode.TARGET:
			_open_menu()
			return
	_refresh()


func _move_to(t: Vector2i) -> void:
	mode = Mode.BUSY
	if t != selected.pos:
		battle.commit_move(selected, t)
	else:
		selected.moved = true
		battle._move_origin[selected.id] = selected.pos
	await _play(battle.take_events())
	_open_menu()


func _open_menu() -> void:
	mode = Mode.MENU
	forecast = Forecast.for_destination(battle, selected, selected.pos)
	_hud.show_actions(selected, _action_list(selected))
	_refresh()


## [{id, label, enabled, tooltip}]
func _action_list(u: Unit) -> Array:
	var out: Array = []
	var atk := battle.basic_targets(u)
	var objs := battle.object_targets(u)
	out.append({"id": "attack", "label": "Attack", "enabled": not atk.is_empty() or not objs.is_empty(),
		"tooltip": "Basic Attack, %d Noise" % 0 if true else ""})
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
	var talk := battle.talk_targets(u)
	if not talk.is_empty():
		out.append({"id": "talk", "label": "Talk", "enabled": true, "tooltip": "Recruit Umbrella. Uses the Action."})
	out.append({"id": "wait", "label": "Wait", "enabled": true, "tooltip": "End this unit's activation."})
	return out


func on_action(id: String) -> void:
	if mode != Mode.MENU:
		return
	_hud.hide_actions()
	match id:
		"wait":
			battle.wait(selected)
			await _after_action()
		"item":
			battle.use_item(selected)
			await _after_action()
		"attack":
			target_kind = "attack"
			target_options = battle.basic_targets(selected)
			target_options.append_array(battle.object_targets(selected))
			mode = Mode.TARGET
		"talk":
			target_kind = "talk"
			target_options = battle.talk_targets(selected)
			mode = Mode.TARGET
		_:
			var art_id := id.substr(4)
			var art := Arts.get_art(art_id)
			if art.target == "self":
				battle.use_art(selected, art_id, selected)
				await _after_action()
				return
			target_kind = id
			target_options = battle.art_targets(selected, art_id)
			mode = Mode.TARGET
	_refresh()


## Maps a hovered tile to a target option: a Unit, a cover tile, or a direction.
func _target_at(t: Vector2i) -> Variant:
	if t == NONE:
		return null
	for o in target_options:
		if o is Unit and o.occupies(t):
			return o
		if o is Vector2i and target_kind != "attack" and _is_direction_kind():
			if Arts.cone_tiles(selected, selected.pos, o).has(t):
				return o
		elif o is Vector2i and o == t:
			return o
	return null


func _is_direction_kind() -> bool:
	if not target_kind.begins_with("art:"):
		return false
	return Arts.get_art(target_kind.substr(4)).target == "direction"


func _execute_target(tgt: Variant) -> void:
	mode = Mode.BUSY
	match target_kind:
		"attack":
			if tgt is Unit:
				battle.attack(selected, tgt)
			else:
				battle.attack_object(selected, tgt)
		"talk":
			battle.talk(selected, tgt)
		_:
			battle.use_art(selected, target_kind.substr(4), tgt)
	await _after_action()


func _after_action() -> void:
	mode = Mode.BUSY
	await _play(battle.take_events())
	selected = null
	forecast = {}
	target_options = []
	hover_target = null
	if await _check_finished():
		return
	mode = Mode.IDLE
	_refresh()
	if battle.all_player_done():
		_hud.pulse_end_turn()


func end_turn() -> void:
	if mode != Mode.IDLE and mode != Mode.SELECTED:
		return
	selected = null
	forecast = {}
	mode = Mode.BUSY
	_refresh()
	await _hud.banner("Enemy Phase")
	var predicted := {}
	for u in battle.player_units():
		if not u.frozen:
			predicted[u] = Forecast.for_destination(battle, u, u.pos).predicted_hp
	battle.end_player_phase()
	for u in predicted:
		metrics.hp_errors.append(absi(int(predicted[u]) - u.hp))
	await _play(battle.take_events())
	if await _check_finished():
		return
	mode = Mode.IDLE
	_refresh()


func _check_finished() -> bool:
	if battle.phase != Defs.Phase.VICTORY and battle.phase != Defs.Phase.DEFEAT:
		return false
	mode = Mode.DONE
	_refresh()
	var result := {
		"victory": battle.phase == Defs.Phase.VICTORY,
		"turns": battle.turn,
		"stars": battle.stars(),
		"stats": battle.stats.duplicate(),
		"broken": battle.board.units.filter(func(u): return u.faction == Defs.Faction.PLAYER and u.broken).map(func(u): return u.name),
		"recruited": battle.recruited,
		"metrics": _metrics_summary(),
	}
	sfx.play("victory" if result.victory else "defeat", 0.0)
	await _hud.banner("Victory" if result.victory else "Defeat")
	battle_finished.emit(result)
	return true


func _metrics_summary() -> Dictionary:
	var errs: Array = metrics.hp_errors
	var avg := 0.0
	for e in errs:
		avg += e
	if not errs.is_empty():
		avg /= errs.size()
	var out := battle.stats.duplicate()
	out.merge({
		"turns": battle.turn,
		"duration_s": (Time.get_ticks_msec() - metrics.started_ms) / 1000.0,
		"avg_predicted_hp_error": snappedf(avg, 0.01),
		"threat_inspections": metrics.threat_inspections,
		"recruitment_skipped": not battle.recruited,
		"vacuum_path_blocked": metrics.vacuum_blocked,
		"victory": battle.phase == Defs.Phase.VICTORY,
	})
	return out


# --- Event playback -----------------------------------------------------------------

func _play(events: Array) -> void:
	for e in events:
		match e.type:
			"move", "displace":
				if battle.phase == Defs.Phase.ENEMY:
					await _follow(e.unit)
				var v: UnitView = _views[e.unit.id]
				var tw := create_tween()
				var dur := 0.11 if e.type == "move" else 0.07
				for p in e.path.slice(1):
					tw.tween_property(v, "position", foot_point(e.unit, p), dur)
				if e.type == "move":
					v.set_moving(true)
					v.apply_facing()
				await tw.finished
				v.set_moving(false)
			"teleport":
				_place(_views[e.unit.id], e.unit.pos)
			"strike":
				var tv: UnitView = _views[e.target.id]
				var av: UnitView = _views[e.attacker.id]
				sfx.play(Sfx.attack_sound(e.attacker), -10.0)
				var lunge := (tv.position - av.position).normalized() * 10.0
				if av.sprite != null and av.sprite.sprite_frames.has_animation("attack"):
					await av.play_once("attack")
				var tw := create_tween()
				tw.tween_property(av, "position", av.position + lunge, 0.08)
				tw.tween_property(av, "position", av.position, 0.08)
				await tw.finished
				var dist: int = e.attacker.distance_to_unit(e.attacker.pos, e.target, e.target.pos)
				var proj: String = {"stapler": "staple_shot", "toaster": "toast", "teacup": "steam_curl"}.get(e.attacker.id, "")
				if dist >= 2 and proj != "":
					await projectile(proj, av.position + Vector2(0, -60), tv.position + Vector2(0, -50))
				sfx.play("miss" if not e.hit else ("crit" if e.crit else "hit"))
				if e.hit:
					vfx("crit_burst" if e.crit else "hit_spark", tv.position + Vector2(0, -56))
					tv.play_once("hurt")
				var txt := "Miss"
				if e.hit:
					txt = ("CRIT %d" if e.crit else "%d") % e.damage
				if e.get("intercepted", false):
					_hud.log_line("Lamp intercepts the hit (Watchful).")
				_float_text(tv.position + Vector2(0, -90), txt, Color("ffe070") if e.crit else Color.WHITE)
				_hud.log_line("%s %s %s: %s" % [e.attacker.name, "counters" if e.get("counter", false) else "hits", e.target.name, txt])
				await get_tree().create_timer(0.18).timeout
			"damage":
				var v: UnitView = _views[e.unit.id]
				v.shown_hp = e.hp
				v.queue_redraw()
				# The hurt animation has its own baked flash; tint only units without one.
				if v.has_anim("hurt"):
					if v.sprite.animation != "hurt":
						v.play_once("hurt")
				else:
					var tw := create_tween()
					tw.tween_property(v, "modulate", Color(1, 0.4, 0.4), 0.06)
					tw.tween_property(v, "modulate", Color.WHITE, 0.12)
					await tw.finished
			"heal":
				var v: UnitView = _views[e.unit.id]
				v.shown_hp = e.hp
				v.queue_redraw()
				sfx.play("heal")
				vfx("heal_sparkle", v.position + Vector2(0, -56))
				_float_text(v.position + Vector2(0, -90), "+%d" % e.amount, Color("80ff90"))
				_hud.log_line("%s recovers %d HP." % [e.unit.name, e.amount])
				await get_tree().create_timer(0.25).timeout
			"broken":
				var v: UnitView = _views[e.unit.id]
				_hud.log_line("%s is Broken." % e.unit.name)
				sfx.play("broken")
				var tw := create_tween()
				tw.tween_property(v, "modulate:a", 0.0, 0.35)
				await tw.finished
				v.refresh()
			"collision":
				_hud.log_line("%s collides!" % e.unit.name)
				sfx.play("collision")
			"art":
				_hud.log_line("%s uses %s." % [e.unit.name, e.name])
				sfx.play(Sfx.ART_SOUNDS.get(e.art, ""))
				var cv: UnitView = _views[e.unit.id]
				cv.play_once("art")
				if e.art == "suction":
					vfx("suction_swirl", cv.position + Vector2(cv.unit.facing * 90, -80), cv.unit.facing < 0)
				await _hud.toast(e.name)
			"area":
				var col := Color(1, 0.6, 0.2, 0.45)
				if e.kind == "blowback":
					col = Color(0.6, 0.9, 1, 0.4)
				elif e.kind == "cutting_line":
					col = Color(1, 0.15, 0.15, 0.55)
					for t in e.tiles:
						vfx("cutting_line", tile_center(t))
				for t in e.tiles:
					flash_tiles[t] = col
				_overlay.queue_redraw()
				await get_tree().create_timer(0.3).timeout
				flash_tiles.clear()
				_overlay.queue_redraw()
			"object_hit":
				_float_text(tile_center(e.tile) + Vector2(0, -20), "%d" % e.amount, Color.WHITE)
				if e.destroyed:
					_hud.log_line("Cover destroyed.")
					destroyed_cover[e.tile] = e.get("kind", "box")
				_sync_props()
				_floor.queue_redraw()
			"noise":
				_hud.refresh()
			"gaze":
				_hud.log_line("Human Gaze! The human looks down.")
				sfx.play("gaze", 0.0)
				for fu in e.frozen:
					_poof(_views[fu.id])
				_sync_all()
				await _hud.banner("Human Gaze")
			"gaze_end":
				_hud.log_line("The human looks away.")
				sfx.play("gaze_end")
				for fu in e.thawed:
					_poof(_views[fu.id])
				_sync_all()
			"talk":
				await _dialogue.play(SliceDialogue.RECRUIT)
				_hud.log_line("Umbrella will join next Player Phase.")
			"telegraph":
				_hud.log_line("Paper Cutter marks a Cutting Line!")
				sfx.play("telegraph")
				_overlay.queue_redraw()
				await get_tree().create_timer(0.35).timeout
			"telegraph_cancel":
				_hud.log_line("Cutting Line cancelled.")
			"tape":
				_hud.log_line("%s is taped down." % e.unit.name)
				_floor.queue_redraw()
			"item":
				_hud.log_line("%s uses %s." % [e.unit.name, e.item])
			"phase":
				_sync_all()
				if e.phase == Defs.Phase.PLAYER:
					sfx.play("phase")
					await _hud.banner("Player Phase  -  Turn %d" % e.turn)
		_sync_all()


## Plays a one-shot effect centred at `p`. Returns immediately; the node frees itself.
func vfx(name: String, p: Vector2, flip := false, scale_by := 1.0) -> void:
	var sf := SpriteLib.load_vfx(name)
	if sf == null:
		return
	var s := AnimatedSprite2D.new()
	s.sprite_frames = sf
	s.position = p
	s.flip_h = flip
	s.scale = Vector2(scale_by, scale_by)
	s.z_index = 50
	add_child(s)
	s.play(sf.get_animation_names()[0])
	s.animation_finished.connect(s.queue_free)


## Moves a projectile sprite from a to b (no-op without art).
func projectile(name: String, a: Vector2, b: Vector2) -> void:
	var sf := SpriteLib.load_vfx(name)
	if sf == null:
		return
	var s := AnimatedSprite2D.new()
	s.sprite_frames = sf
	s.position = a
	s.flip_h = b.x < a.x
	s.z_index = 50
	add_child(s)
	var anim: String = sf.get_animation_names()[0]
	sf.set_animation_loop(anim, true)
	s.play(anim)
	var tw := create_tween()
	tw.tween_property(s, "position", b, clampf(a.distance_to(b) / 1400.0, 0.08, 0.3))
	await tw.finished
	s.queue_free()


## Quick squash-and-flash used for the Gaze transformation in both directions.
func _poof(v: UnitView) -> void:
	# Sized for 128px units; doubled to cover Large ones.
	var big := v.unit.is_large()
	vfx("gaze_poof", v.position + Vector2(0, -112 if big else -56), false, 2.0 if big else 1.0)
	var tw := create_tween()
	tw.tween_property(v, "scale", Vector2(1.25, 0.7), 0.07)
	tw.tween_property(v, "modulate", Color(2, 2, 2), 0.05)
	tw.tween_callback(v.refresh)
	tw.tween_property(v, "scale", Vector2.ONE, 0.1)
	tw.parallel().tween_property(v, "modulate", Color.WHITE, 0.15)


func _float_text(p: Vector2, s: String, c: Color) -> void:
	var l := Label.new()
	l.text = s
	l.add_theme_font_size_override("font_size", 20)
	l.add_theme_color_override("font_color", c)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 5)
	l.position = p - Vector2(20, 0)
	l.z_index = 100
	add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "position:y", p.y - 30, 0.6)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.3)
	tw.tween_callback(l.queue_free)


func _sync_all() -> void:
	for id in _views:
		var v: UnitView = _views[id]
		v.shown_hp = v.unit.hp
		if not v.unit.broken:
			v.refresh()
	_refresh()


func _refresh() -> void:
	_floor.queue_redraw()
	_overlay.queue_redraw()
	_top.queue_redraw()
	if _hud != null and battle != null:
		_hud.refresh()


# --- Drawing ---------------------------------------------------------------------------

func _draw_floor(n: Node2D) -> void:
	if battle == null:
		return
	var b := battle.board
	var floor_tex: Texture2D = _env.floor
	if floor_tex != null:
		n.draw_texture(floor_tex, MAP_ORIGIN)
	for x in range(1, b.width + 1):
		for y in range(1, b.height + 1):
			var t := Vector2i(x, y)
			var r := tile_rect(t)
			if floor_tex == null:
				var c := Color("6b5544") if (x + y) % 2 == 0 else Color("735b49")
				n.draw_rect(r, c)
			if b.slow_tiles.has(t):
				var kind: String = b.slow_tiles[t]
				var over: Texture2D = EnvArt.frame(_env, "sticky_tape") if kind == "tape" else EnvArt.spill_frame(_env, t)
				if over != null:
					n.draw_texture(over, r.position)
				else:
					n.draw_rect(r.grow(-4), Color("4a8fb8", 0.75) if kind == "spill" else Color("d8c070", 0.7))
	for t in destroyed_cover:
		var kind: String = destroyed_cover[t]
		var tex := EnvArt.frame(_env, kind, "destroyed")
		if tex != null:
			var r := tile_rect(t)
			n.draw_texture(tex, Vector2(r.position.x, r.end.y) - EnvArt.offset(_env, kind))
	# Grid lines.
	for x in range(b.width + 1):
		n.draw_line(MAP_ORIGIN + Vector2(x * T, 0), MAP_ORIGIN + Vector2(x * T, b.height * T), Color(0, 0, 0, 0.18))
	for y in range(b.height + 1):
		n.draw_line(MAP_ORIGIN + Vector2(0, y * T), MAP_ORIGIN + Vector2(b.width * T, y * T), Color(0, 0, 0, 0.18))


## Props are drawn in the y-sorted unit layer so units in front overlap them.
func _sync_props() -> void:
	for c in _props:
		c.queue_free()
	_props.clear()
	var b := battle.board
	var done := {}
	for t in b.objects:
		var o: Dictionary = b.objects[t]
		if o.kind == "cabinet":
			if done.has("cabinet"):
				continue
			done["cabinet"] = true
			t = Vector2i(13, 8)
		var p := PropView.new()
		p.view = self
		p.tile = t
		p.obj = o
		p.size_tiles = 2 if o.kind == "cabinet" else 1
		var tag := ""
		if b.is_destructible(t):
			tag = "damaged" if o.hp < o.max_hp else "intact"
		elif _env.variants.has(t):
			tag = _env.variants[t]
		p.tex = EnvArt.frame(_env, o.kind, tag)
		p.offset = EnvArt.offset(_env, o.kind)
		var r := tile_rect(t)
		p.position = Vector2(r.position.x, r.end.y)
		_units_layer.add_child(p)
		_props.append(p)


func _draw_overlay(n: Node2D) -> void:
	if battle == null:
		return
	# Gaze area.
	for t in battle.gaze_tiles:
		n.draw_rect(tile_rect(t), Color(0.7, 0.55, 1.0, 0.35))
		n.draw_rect(tile_rect(t).grow(-1), Color(0.85, 0.75, 1.0, 0.9), false, 2.0)
	if battle.gaze_active():
		# A watching eye over the Attention Point.
		var c := tile_center(battle.gaze_center) + Vector2(0, -T * 1.6)
		var eye := SpriteLib.load_ui("eye")
		if eye != null:
			n.draw_texture(eye, (c - eye.get_size() / 2).round())
	if battle.gaze_active() and SpriteLib.load_ui("eye") == null:
		var c := tile_center(battle.gaze_center) + Vector2(0, -T * 1.6)
		var pts := PackedVector2Array()
		for i in 32:
			var a := TAU * i / 32.0
			pts.append(c + Vector2(cos(a) * 44, sin(a) * 20 * (1.0 if sin(a) > 0 else 1.0)))
		n.draw_colored_polygon(pts, Color(0.95, 0.92, 1.0, 0.9))
		n.draw_polyline(pts + PackedVector2Array([pts[0]]), Color(0.3, 0.2, 0.45), 3.0)
		n.draw_circle(c, 15, Color(0.45, 0.3, 0.7))
		n.draw_circle(c, 7, Color(0.08, 0.05, 0.12))
	# Telegraphed lanes are always visible.
	for tg in battle.telegraphs:
		for t in tg.tiles:
			var r := tile_rect(t)
			n.draw_rect(r, Color(1, 0.1, 0.1, 0.25))
			for i in range(-T, T, 12):
				n.draw_line(r.position + Vector2(maxf(i, 0), maxf(-i, 0)), r.position + Vector2(minf(i + T, T), minf(T - i, T)) , Color(1, 0.2, 0.2, 0.5), 2.0)
	# Inspected enemy danger.
	if inspected_enemy != null and not inspected_enemy.broken:
		var m := battle.board.reach_map(inspected_enemy, inspected_enemy.pos, battle.effective_move(inspected_enemy))
		var reach := {}
		for a in m:
			if a == inspected_enemy.pos or battle.board.can_stand(inspected_enemy, a):
				for t in inspected_enemy.tiles_at(a):
					reach[t] = true
		for t in reach:
			n.draw_rect(tile_rect(t).grow(-2), Color(1, 0.5, 0.3, 0.28))
	# Movement area.
	if mode == Mode.SELECTED and selected != null:
		for a in move_set:
			for t in selected.tiles_at(a):
				n.draw_rect(tile_rect(t).grow(-3), Color(0.35, 0.65, 1.0, 0.22))
				n.draw_rect(tile_rect(t).grow(-3), Color(0.55, 0.8, 1.0, 0.45), false, 2.0)
	# Target highlights.
	if mode == Mode.TARGET:
		for o in target_options:
			if o is Unit:
				for t in o.tiles():
					n.draw_rect(tile_rect(t).grow(-2), Color(1, 0.3, 0.3, 0.4) if target_kind != "talk" and not _is_ally_kind() else Color(0.3, 1, 0.5, 0.4))
			elif o is Vector2i and not _is_direction_kind():
				n.draw_rect(tile_rect(o).grow(-2), Color(1, 0.8, 0.3, 0.4))
		if _is_direction_kind() and hover_target != null:
			for t in battle.cone_for(selected, hover_target):
				n.draw_rect(tile_rect(t).grow(-2), Color(1, 0.6, 0.2, 0.45))
		elif _is_direction_kind():
			for d in target_options:
				for t in battle.cone_for(selected, d):
					n.draw_rect(tile_rect(t).grow(-6), Color(1, 0.6, 0.2, 0.15))
	for t in flash_tiles:
		n.draw_rect(tile_rect(t), flash_tiles[t])
	# Selected unit footprint.
	if selected != null:
		for t in selected.tiles():
			n.draw_rect(tile_rect(t).grow(-1), Color(1, 1, 1, 0.9), false, 2.0)


func _is_ally_kind() -> bool:
	if not target_kind.begins_with("art:"):
		return false
	return Arts.get_art(target_kind.substr(4)).target == "ally"


func _draw_top(n: Node2D) -> void:
	if battle == null:
		return
	# Movement forecast: path, threat lines, displacement arrows.
	if mode == Mode.SELECTED and selected != null and move_set.has(hover):
		var path := battle.path_to(selected, hover)
		for i in range(1, path.size()):
			n.draw_line(unit_center(selected, path[i - 1]), unit_center(selected, path[i]), Color(1, 1, 1, 0.7), 4.0)
		for t in selected.tiles_at(hover):
			n.draw_rect(tile_rect(t).grow(-1), Color.WHITE, false, 3.0)
	if not forecast.is_empty() and selected != null and (mode == Mode.SELECTED or mode == Mode.MENU):
		var dest: Vector2i = hover if mode == Mode.SELECTED and move_set.has(hover) else selected.pos
		var to := unit_center(selected, dest)
		for th in forecast.threats:
			var e: Unit = th.enemy
			var from := unit_center(e, e.pos)
			var pv: Dictionary = th.preview
			var col := Color(1, 0.55, 0.2)
			if pv.ranged:
				col = Color(1, 0.85, 0.3)
			if not th.displacement.is_empty():
				col = Color(0.4, 0.85, 1.0)
			col.a = 0.35 + 0.6 * pv.hit / 100.0
			var stand := unit_center(e, th.from)
			if th.from != e.pos:
				_dashed(n, from, stand, Color(col, col.a * 0.6), 2.0)
			n.draw_line(stand, to, col, 3.0)
			_arrow_head(n, stand, to, col)
			if not th.displacement.is_empty() and th.displacement.dist > 0:
				var d: Vector2i = th.displacement.dir
				var tip := to + Vector2(d.x, -d.y) * T * 0.8
				n.draw_line(to, tip, Color(0.4, 0.85, 1.0), 4.0)
				_arrow_head(n, to, tip, Color(0.4, 0.85, 1.0))
	# Cursor.
	if hover != NONE and mode != Mode.BUSY:
		var cur := SpriteLib.load_ui("cursor")
		if cur != null:
			n.draw_texture(cur, tile_rect(hover).position)
		else:
			n.draw_rect(tile_rect(hover), Color(1, 1, 0.6, 0.9), false, 2.0)


func _dashed(n: Node2D, a: Vector2, b: Vector2, c: Color, w: float) -> void:
	var len := a.distance_to(b)
	var dir := (b - a).normalized()
	var s := 0.0
	while s < len:
		n.draw_line(a + dir * s, a + dir * minf(s + 8, len), c, w)
		s += 14


func _arrow_head(n: Node2D, from: Vector2, to: Vector2, c: Color) -> void:
	var dir := (to - from).normalized()
	# Red threat arrows use the drawn arrowhead (points right in the art).
	var head := SpriteLib.load_ui("threat_arrowhead")
	if head != null and c.r > c.b:
		n.draw_set_transform(to - dir * 10, dir.angle())
		n.draw_texture(head, -head.get_size() / 2)
		n.draw_set_transform(Vector2.ZERO)
		return
	var tip := to - dir * 14
	var side := Vector2(-dir.y, dir.x) * 7
	n.draw_colored_polygon(PackedVector2Array([to - dir * 4, tip + side, tip - side]), c)
