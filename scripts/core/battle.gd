class_name Battle
extends RefCounted
## Battle rules and state: phases, actions, Noise, Human Gaze, telegraphs,
## objectives. Presentation reads `events` (see take_events) and never mutates.

var board: Board
var rng := RandomNumberGenerator.new()
var turn := 0
var phase := Defs.Phase.PLAYER
var noise := 0
var gaze_tiles := {} # tile -> true while a Gaze is active
var gaze_center := Vector2i.ZERO
var telegraphs: Array = [] # {owner, tiles: Array[Vector2i], dir, might}
var events: Array = []
var recruited := false
var any_broken := false
var victory_turn := 0

# Per-activation bookkeeping for move undo.
var _move_origin := {} # unit id -> Vector2i
var _gaze_count := 0
var stats := {"gaze_triggers": 0, "arts_used": 0, "quiet_arts_in_gaze": 0, "enemies_caught": 0, "allies_caught": 0}


func _init(b: Board, seed_value := 0) -> void:
	board = b
	if seed_value != 0:
		rng.seed = seed_value
	else:
		rng.randomize()


func start() -> void:
	begin_player_phase()


func take_events() -> Array:
	var out := events
	events = []
	return out


func _emit(e: Dictionary) -> void:
	events.append(e)


# --- Queries -----------------------------------------------------------------

func player_units() -> Array[Unit]:
	return _units_of(Defs.Faction.PLAYER)


func enemy_units() -> Array[Unit]:
	return _units_of(Defs.Faction.ENEMY)


func _units_of(f: int) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in board.living_units():
		if u.faction == f:
			out.append(u)
	return out


func gaze_active() -> bool:
	return not gaze_tiles.is_empty()


func in_gaze_at(u: Unit, anchor: Vector2i) -> bool:
	for t in u.tiles_at(anchor):
		if gaze_tiles.has(t):
			return true
	return false


func in_gaze(u: Unit) -> bool:
	return in_gaze_at(u, u.pos)


func effective_move(u: Unit) -> int:
	if u.status.has("pinned"):
		return 0
	var m := u.move
	if u.status.has("taped"):
		m = maxi(m - 2, 0)
	return m


func has_movement_penalty(u: Unit) -> bool:
	return u.status.has("pinned") or u.status.has("taped")


## Whether `attacker` may attack `target` at all right now (ignoring range).
func can_target(attacker: Unit, target: Unit) -> bool:
	if target.broken or target.frozen or not attacker.is_hostile_to(target):
		return false
	if gaze_active():
		# The watched area is neutral to fantasy combat.
		if in_gaze(target) or in_gaze(attacker):
			return false
		if attacker.expected_behavior:
			return false
	return true


func move_options(u: Unit) -> Array[Vector2i]:
	if u.moved:
		return [u.pos]
	return board.reachable(u, u.pos, effective_move(u))


func path_to(u: Unit, anchor: Vector2i) -> Array[Vector2i]:
	var m := board.reach_map(u, u.pos, effective_move(u))
	return Board.path_from(m, anchor)


func basic_targets(u: Unit, anchor := Vector2i(-99, -99)) -> Array:
	if anchor == Vector2i(-99, -99):
		anchor = u.pos
	var out: Array = []
	for o in board.living_units():
		if can_target(u, o) and Combat.in_range(u, anchor, o, o.pos, u.min_range, u.attack_range) \
				and board.has_los(u, anchor, o, o.pos):
			out.append(o)
	return out


## Destructible cover the unit can hit with a Basic Attack.
func object_targets(u: Unit) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	if gaze_active() and in_gaze(u):
		return out
	for t in board.objects:
		if not board.is_destructible(t):
			continue
		var d := u.distance_from(u.pos, t)
		if d >= u.min_range and d <= u.attack_range and board.has_los_to_tile(u, u.pos, t):
			out.append(t)
	return out


func talk_targets(u: Unit) -> Array:
	var out: Array = []
	for o in board.living_units():
		if o.faction == Defs.Faction.NEUTRAL and o.recruiter == u.id and not o.frozen \
				and u.distance_to_unit(u.pos, o, o.pos) == 1 and not (gaze_active() and (in_gaze(u) or in_gaze(o))):
			out.append(o)
	return out


func art_check(u: Unit, art_id: String) -> Dictionary:
	var art := Arts.get_art(art_id)
	if gaze_active() and art.noise > 0:
		return {"ok": false, "reason": "Unavailable while Human Gaze is active"}
	if art_targets(u, art_id).is_empty():
		return {"ok": false, "reason": "No valid target"}
	return {"ok": true, "reason": ""}


## Returns Units, or direction Vector2i for cones.
func art_targets(u: Unit, art_id: String) -> Array:
	var art := Arts.get_art(art_id)
	var out: Array = []
	match art.target:
		"self":
			out.append(u)
		"direction":
			for d in Defs.DIRS:
				out.append(d)
		"ally":
			for o in board.living_units():
				if o.faction != u.faction or o.frozen or o.pending_join:
					continue
				var dist := u.distance_to_unit(u.pos, o, o.pos) if o != u else 0
				if dist >= art.min and dist <= art.max and not (gaze_active() and in_gaze(o)):
					out.append(o)
		"enemy":
			for o in board.living_units():
				if not can_target(u, o):
					continue
				if Combat.in_range(u, u.pos, o, o.pos, art.min, art.max) and board.has_los(u, u.pos, o, o.pos):
					if art_id == "suction" and o.is_large():
						continue
					out.append(o)
		"lunge":
			for d in Defs.DIRS:
				for k in range(1, 4):
					var dash_to: Vector2i = u.pos + d * k
					if not board.can_stand(u, dash_to):
						break
					var o := board.unit_at(dash_to + d)
					if o != null and can_target(u, o) and not out.has(o):
						out.append(o)
	return out


func cone_for(u: Unit, dir: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for t in Arts.cone_tiles(u, u.pos, dir):
		if board.in_bounds(t) and board.has_los_to_tile(u, u.pos, t):
			out.append(t)
	return out


func units_in_tiles(tiles: Array) -> Array[Unit]:
	var out: Array[Unit] = []
	for t in tiles:
		var o := board.unit_at(t)
		if o != null and not out.has(o):
			out.append(o)
	return out


# --- Player actions -----------------------------------------------------------

func commit_move(u: Unit, anchor: Vector2i) -> bool:
	if not u.can_activate() or u.moved:
		return false
	if not move_options(u).has(anchor):
		return false
	var path := path_to(u, anchor)
	_move_origin[u.id] = u.pos
	u.pos = anchor
	u.moved = true
	_emit({"type": "move", "unit": u, "path": path})
	return true


func undo_move(u: Unit) -> void:
	if u.acted or not _move_origin.has(u.id):
		return
	u.pos = _move_origin[u.id]
	u.moved = false
	_move_origin.erase(u.id)
	_emit({"type": "teleport", "unit": u})


func attack(u: Unit, target: Unit) -> Dictionary:
	if not basic_targets(u).has(target):
		return {}
	var spec := _player_spec(u, target, {"might": u.might, "type": u.dmg_type})
	var res := _strike(u, target, spec, true)
	_finish_action(u)
	return res


func attack_object(u: Unit, t: Vector2i) -> void:
	if not object_targets(u).has(t):
		return
	_hit_object(t, u.power + u.might, u)
	_finish_action(u)


func _hit_object(t: Vector2i, amount: int, by: Unit) -> void:
	var kind: String = board.objects[t].kind
	var destroyed := board.damage_object(t, amount)
	_emit({"type": "object_hit", "tile": t, "kind": kind, "amount": amount, "destroyed": destroyed, "by": by})


func wait(u: Unit) -> void:
	_finish_action(u)


func use_item(u: Unit) -> void:
	if u.item == "" or not u.can_activate():
		return
	var item: Dictionary = Arts.ITEMS[u.item]
	_heal(u, ceili(u.max_hp * item.heal_pct))
	_emit({"type": "item", "unit": u, "item": item.name})
	u.item = ""
	_finish_action(u)


func talk(u: Unit, target: Unit) -> void:
	if not talk_targets(u).has(target):
		return
	target.faction = Defs.Faction.PLAYER
	target.pending_join = true
	target.acted = true
	recruited = true
	_emit({"type": "talk", "unit": u, "target": target})
	_finish_action(u)


func use_art(u: Unit, art_id: String, target) -> bool:
	if not u.can_activate() or not u.arts.has(art_id):
		return false
	if not art_check(u, art_id).ok:
		return false
	if not art_targets(u, art_id).has(target):
		return false
	var art := Arts.get_art(art_id)
	stats.arts_used += 1
	if gaze_active() and art.noise == 0:
		stats.quiet_arts_in_gaze += 1
	_emit({"type": "art", "unit": u, "art": art_id, "name": art.name, "target": target})
	match art_id:
		"guard_beam":
			target.status["guard_beam"] = true
		"flashbulb", "flash_bake":
			var tiles := cone_for(u, target)
			_emit({"type": "area", "tiles": tiles, "kind": art_id})
			var spec_base := {"might": art.might, "type": art.type}
			if art_id == "flash_bake" and u.status.has("heated"):
				spec_base["power_bonus"] = 2
			for o in units_in_tiles(tiles):
				if can_target(u, o):
					var r := _strike(u, o, spec_base.duplicate(), false)
					if art_id == "flashbulb" and r.get("hit", false) and not o.broken:
						o.status["dazzled"] = true
			for t in tiles:
				if board.is_destructible(t):
					_hit_object(t, u.power + int(art.might), u)
			if art_id == "flash_bake":
				u.status.erase("heated")
		"pin":
			var r := _strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
			if r.get("hit", false) and not target.broken:
				target.status["pinned"] = true
		"staple_burst":
			var spec := _player_spec(u, target, {"might": art.might, "type": art.type})
			_strike(u, target, spec, false)
			var second: Unit = target
			if target.broken:
				second = null
				for o in art_targets(u, "staple_burst"):
					second = o
					break
			if second != null:
				_strike(u, second, _player_spec(u, second, {"might": art.might, "type": art.type}), false)
		"eject":
			var r := _strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
			if r.get("hit", false) and not target.broken:
				forced_move(target, _away_dir(u, target), 2)
		"warm_pour":
			_heal(target, ceili(target.max_hp * 0.3))
		"steady_sip":
			for s in ["dazzled", "pinned", "taped"]:
				if target.status.has(s):
					target.status.erase(s)
					break
			target.status["steady_sip"] = true
		"suction":
			pull_toward(target, u, 3)
		"blowback":
			var tiles := cone_for(u, target)
			_emit({"type": "area", "tiles": tiles, "kind": art_id})
			# Push the farthest units first so near ones don't collide with them needlessly.
			var hit_units := units_in_tiles(tiles)
			hit_units.sort_custom(func(a, b): return u.distance_to_unit(u.pos, a, a.pos) > u.distance_to_unit(u.pos, b, b.pos))
			for o in hit_units:
				if can_target(u, o):
					forced_move(o, target, 2)
		"lunge":
			var d := _straight_dir(u.pos, target.pos)
			var dash_to: Vector2i = target.pos - d
			var path: Array[Vector2i] = [u.pos]
			var at := u.pos
			while at != dash_to:
				at += d
				path.append(at)
			u.pos = dash_to
			_emit({"type": "move", "unit": u, "path": path})
			_strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
		"canopy":
			for o in board.living_units():
				if o != u and o.faction == u.faction and u.distance_to_unit(u.pos, o, o.pos) == 1:
					o.status["canopy"] = true
	if art.noise >= 2 and u.id == "toaster" and not u.broken:
		u.status["heated"] = turn # Hot Coils
	_finish_action(u, art.noise)
	return true


func _player_spec(u: Unit, target: Unit, spec: Dictionary) -> Dictionary:
	if u.status.has("heated"):
		spec["power_bonus"] = 2
		u.status.erase("heated")
	if u.id == "stapler" and (has_movement_penalty(target) or target.displaced_this_phase):
		spec["dmg_mult"] = 1.2 # Opportunist
	return spec


func _finish_action(u: Unit, noise_gain := 0) -> void:
	u.acted = true
	u.moved = true
	_move_origin.erase(u.id)
	if noise_gain > 0:
		add_noise(noise_gain, u)
	_check_end()


func add_noise(amount: int, source: Unit) -> void:
	noise += amount
	_emit({"type": "noise", "value": noise})
	if noise >= Defs.NOISE_THRESHOLD and not gaze_active():
		noise -= Defs.NOISE_THRESHOLD # overflow is kept
		trigger_gaze(source.pos)


func trigger_gaze(center: Vector2i) -> void:
	gaze_center = center
	gaze_tiles.clear()
	for dx in range(-Defs.GAZE_RADIUS, Defs.GAZE_RADIUS + 1):
		for dy in range(-Defs.GAZE_RADIUS, Defs.GAZE_RADIUS + 1):
			var t := center + Vector2i(dx, dy)
			if board.in_bounds(t):
				gaze_tiles[t] = true
	stats.gaze_triggers += 1
	var frozen: Array = []
	for u in board.living_units():
		if in_gaze(u) and not u.expected_behavior:
			u.frozen = true
			frozen.append(u)
			if u.faction == Defs.Faction.ENEMY:
				stats.enemies_caught += 1
			elif u.faction == Defs.Faction.PLAYER:
				stats.allies_caught += 1
				u.acted = true
	_emit({"type": "gaze", "tiles": gaze_tiles.keys(), "center": center, "frozen": frozen, "noise": noise})


func end_gaze() -> void:
	if not gaze_active():
		return
	var thawed: Array = []
	for u in board.units:
		if u.frozen:
			u.frozen = false
			thawed.append(u)
	gaze_tiles.clear()
	_emit({"type": "gaze_end", "thawed": thawed})


# --- Resolution ----------------------------------------------------------------

## One attack, with optional counter. Returns {hit, crit, damage, ...}.
func _strike(att: Unit, def: Unit, spec: Dictionary, allow_counter: bool) -> Dictionary:
	var target := def
	var intercepted := false
	# Lamp's Watchful: once per Enemy Phase, take a hit meant for an adjacent ally.
	if att.faction == Defs.Faction.ENEMY and def.id != "lamp" and def.faction == Defs.Faction.PLAYER:
		var lamp := board.find_unit("lamp")
		if lamp != null and not lamp.broken and not lamp.frozen and not lamp.status.has("watchful_used") \
				and lamp.distance_to_unit(lamp.pos, def, def.pos) == 1 and can_target(att, lamp):
			var pv := Combat.preview(board, att, att.pos, lamp, lamp.pos, spec)
			if pv.damage * 2 < lamp.hp:
				target = lamp
				intercepted = true
				lamp.status["watchful_used"] = true
				spec = spec.duplicate()
				spec["dmg_mult"] = float(spec.get("dmg_mult", 1.0)) * 0.8
	var pv := Combat.preview(board, att, att.pos, target, target.pos, spec)
	var roll := rng.randi_range(0, 99)
	var hit: bool = roll < pv.hit
	var crit: bool = hit and rng.randi_range(0, 99) < pv.crit
	var dmg := 0
	if hit:
		dmg = pv.damage * (Defs.CRIT_MULT if crit else 1)
		target.status.erase("guard_beam")
	if att.status.has("dazzled"):
		att.status.erase("dazzled")
	_emit({"type": "strike", "attacker": att, "target": target, "hit": hit, "crit": crit,
		"damage": dmg, "intercepted": intercepted, "original": def})
	if hit:
		_damage(target, dmg)
	var res := {"hit": hit, "crit": crit, "damage": dmg, "target": target}
	if allow_counter and not target.broken and not att.broken and _can_counter(target, att):
		var cspec := {"might": target.might, "type": target.dmg_type}
		var cpv := Combat.preview(board, target, target.pos, att, att.pos, cspec)
		var chit: bool = rng.randi_range(0, 99) < cpv.hit
		var ccrit: bool = chit and rng.randi_range(0, 99) < cpv.crit
		var cdmg: int = cpv.damage * (Defs.CRIT_MULT if ccrit else 1) if chit else 0
		if chit:
			att.status.erase("guard_beam")
		_emit({"type": "strike", "attacker": target, "target": att, "hit": chit, "crit": ccrit,
			"damage": cdmg, "counter": true})
		if chit:
			_damage(att, cdmg)
		res["counter"] = {"hit": chit, "damage": cdmg}
	return res


func _can_counter(defender: Unit, attacker: Unit) -> bool:
	if defender.frozen or defender.broken:
		return false
	if not can_target(defender, attacker):
		return false
	return Combat.in_range(defender, defender.pos, attacker, attacker.pos, defender.min_range, defender.attack_range) \
		and board.has_los(defender, defender.pos, attacker, attacker.pos)


## Counter preview for the forecast window.
func counter_preview(attacker: Unit, att_anchor: Vector2i, defender: Unit) -> Dictionary:
	if defender.frozen:
		return {}
	var saved := attacker.pos
	attacker.pos = att_anchor
	var ok := _can_counter(defender, attacker)
	var out := {}
	if ok:
		out = Combat.preview(board, defender, defender.pos, attacker, att_anchor, {"might": defender.might, "type": defender.dmg_type})
	attacker.pos = saved
	return out


func _damage(u: Unit, amount: int) -> void:
	u.hp = maxi(u.hp - amount, 0)
	_emit({"type": "damage", "unit": u, "amount": amount, "hp": u.hp})
	if u.hp == 0:
		u.broken = true
		if u.faction == Defs.Faction.PLAYER:
			any_broken = true
		telegraphs = telegraphs.filter(func(t): return t.owner != u)
		_emit({"type": "broken", "unit": u})


func _heal(u: Unit, amount: int) -> void:
	var before := u.hp
	u.hp = mini(u.hp + amount, u.max_hp)
	_emit({"type": "heal", "unit": u, "amount": u.hp - before, "hp": u.hp})


func _away_dir(from: Unit, target: Unit) -> Vector2i:
	return _straight_dir(from.pos, target.pos)


## Dominant cardinal direction from a to b.
static func _straight_dir(a: Vector2i, b: Vector2i) -> Vector2i:
	var d := b - a
	if absi(d.x) >= absi(d.y):
		return Vector2i(signi(d.x), 0) if d.x != 0 else Vector2i(0, signi(d.y))
	return Vector2i(0, signi(d.y))


## Push in `dir` up to `dist` tiles. Collision: 10% max HP (rounded up), ignores
## Defense; hitting a unit damages both; at most one collision per unit.
func forced_move(u: Unit, dir: Vector2i, dist: int) -> void:
	if u.status.has("guard_beam"):
		u.status.erase("guard_beam")
		dist = 0
	dist = maxi(dist - u.forced_move_reduction, 0)
	var path: Array[Vector2i] = [u.pos]
	var collided: Unit = null
	var hit_wall := false
	for i in dist:
		var nxt := u.pos + dir
		var blocked := false
		for t in u.tiles_at(nxt):
			if not board.in_bounds(t) or board.is_blocking_terrain(t):
				hit_wall = true
				blocked = true
				break
			var o := board.unit_at(t)
			if o != null and o != u:
				collided = o
				blocked = true
				break
		if blocked:
			break
		u.pos = nxt
		path.append(nxt)
	if path.size() > 1:
		u.displaced_this_phase = true
		_emit({"type": "displace", "unit": u, "path": path})
	if hit_wall or collided != null:
		_emit({"type": "collision", "unit": u, "other": collided})
		_damage(u, Combat.collision_damage(u))
		if collided != null and not collided.frozen:
			_damage(collided, Combat.collision_damage(collided))


## Pull `u` toward `puller` up to `dist` tiles, stopping when adjacent.
func pull_toward(u: Unit, puller: Unit, dist: int) -> void:
	dist = maxi(dist - u.forced_move_reduction, 0)
	var path: Array[Vector2i] = [u.pos]
	for i in dist:
		if puller.distance_to_unit(puller.pos, u, u.pos) <= 1:
			break
		var d := _pull_step(u, puller)
		if d == Vector2i.ZERO:
			break
		u.pos += d
		path.append(u.pos)
	if path.size() > 1:
		u.displaced_this_phase = true
		_emit({"type": "displace", "unit": u, "path": path})


func _pull_step(u: Unit, puller: Unit) -> Vector2i:
	var best := Vector2i.ZERO
	var best_d := puller.distance_to_unit(puller.pos, u, u.pos)
	# Prefer the dominant axis, fall back to the other one around obstacles.
	var target := puller.pos
	var diff := target - u.pos
	var order: Array[Vector2i] = []
	if absi(diff.x) >= absi(diff.y):
		order = [Vector2i(signi(diff.x), 0), Vector2i(0, signi(diff.y))]
	else:
		order = [Vector2i(0, signi(diff.y)), Vector2i(signi(diff.x), 0)]
	for d in order:
		if d == Vector2i.ZERO:
			continue
		var nxt := u.pos + d
		if board.can_stand(u, nxt):
			var nd := puller.distance_to_unit(puller.pos, u, nxt)
			if nd < best_d:
				return d
	return best


# --- Phases --------------------------------------------------------------------

func begin_player_phase() -> void:
	turn += 1
	phase = Defs.Phase.PLAYER
	end_gaze()
	for u in board.living_units():
		u.displaced_this_phase = false
		for s in ["guard_beam", "steady_sip", "canopy", "pinned", "watchful_used"]:
			u.status.erase(s)
		if u.status.has("heated") and int(u.status.heated) < turn - 1:
			u.status.erase("heated")
		if u.faction == Defs.Faction.PLAYER:
			u.moved = false
			u.acted = false
			u.pending_join = false
	_move_origin.clear()
	_emit({"type": "phase", "phase": phase, "turn": turn})
	_comforting_presence()


func _comforting_presence() -> void:
	var cup := board.find_unit("teacup")
	if cup == null or cup.broken or cup.faction != Defs.Faction.PLAYER:
		return
	var best: Unit = null
	for o in player_units():
		if o != cup and o.hp < o.max_hp and cup.distance_to_unit(cup.pos, o, o.pos) == 1:
			if best == null or o.hp * best.max_hp < best.hp * o.max_hp:
				best = o
	if best != null:
		_heal(best, ceili(best.max_hp * 0.1))


func end_player_phase() -> void:
	if phase != Defs.Phase.PLAYER:
		return
	# Tape slows a unit for one activation; that activation just ended.
	for u in player_units():
		u.status.erase("taped")
	phase = Defs.Phase.ENEMY
	_emit({"type": "phase", "phase": phase, "turn": turn})
	for u in board.living_units():
		u.displaced_this_phase = false
	EnemyAI.new(self).run_phase()
	if _check_end():
		return
	begin_player_phase()


func all_player_done() -> bool:
	for u in player_units():
		if u.can_activate():
			return false
	return true


func _check_end() -> bool:
	if phase == Defs.Phase.VICTORY or phase == Defs.Phase.DEFEAT:
		return true
	var cutter := board.find_unit("cutter")
	if cutter != null and cutter.broken:
		phase = Defs.Phase.VICTORY
		victory_turn = turn
		_emit({"type": "end", "victory": true})
		return true
	var lamp := board.find_unit("lamp")
	if (lamp != null and lamp.broken) or player_units().is_empty():
		phase = Defs.Phase.DEFEAT
		_emit({"type": "end", "victory": false})
		return true
	return false


func stars() -> Dictionary:
	return {
		"recruit": recruited and not board.find_unit("umbrella").broken,
		"turns": phase == Defs.Phase.VICTORY and victory_turn <= Defs.STAR_TURN_TARGET,
		"unbroken": not any_broken,
	}


# --- Enemy helpers used by EnemyAI --------------------------------------------

func enemy_move(u: Unit, anchor: Vector2i, path: Array[Vector2i]) -> void:
	if anchor == u.pos:
		return
	u.pos = anchor
	u.move_path_len = path.size() - 1
	_emit({"type": "move", "unit": u, "path": path})


func enemy_attack(u: Unit, target: Unit) -> Dictionary:
	var spec := {"might": u.might, "type": u.dmg_type}
	if u.ai == "pencil" and u.move_path_len >= 3:
		spec["dmg_mult"] = 1.2 # charge
	var res := _strike(u, target, spec, true)
	var victim: Unit = res.target
	if res.hit and not victim.broken:
		match u.ai:
			"snarer":
				pull_toward(victim, u, 1)
			"roomba":
				forced_move(victim, _away_dir(u, victim), 1)
			"tape":
				board.slow_tiles[victim.pos] = "tape"
				victim.status["taped"] = true
				_emit({"type": "tape", "tile": victim.pos, "unit": victim})
	return res


func add_telegraph(owner: Unit, tiles: Array, dir: Vector2i, might: int) -> void:
	telegraphs.append({"owner": owner, "tiles": tiles, "dir": dir, "might": might, "origin": owner.pos})
	_emit({"type": "telegraph", "unit": owner, "tiles": tiles})


func resolve_telegraph(owner: Unit) -> void:
	for tg in telegraphs.duplicate():
		if tg.owner != owner:
			continue
		telegraphs.erase(tg)
		# Cancelled if the Captain was displaced or is watched.
		if owner.broken or owner.frozen or owner.pos != tg.origin:
			_emit({"type": "telegraph_cancel", "unit": owner})
			continue
		_emit({"type": "art", "unit": owner, "art": "cutting_line", "name": "Cutting Line", "target": tg.dir})
		_emit({"type": "area", "tiles": tg.tiles, "kind": "cutting_line"})
		for t in tg.tiles:
			if board.is_destructible(t):
				_hit_object(t, 99, owner)
		for o in units_in_tiles(tg.tiles):
			if can_target(owner, o):
				_strike(owner, o, {"might": tg.might, "type": Defs.DmgType.PIERCE, "auto_hit": true, "no_crit": true}, false)
