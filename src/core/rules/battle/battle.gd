class_name Battle
extends RefCounted
## Battle rules and state: phases, free movement, actions, Noise, Human Gaze,
## telegraphs and objectives. Presentation reads `events` (see take_events) and
## never mutates anything here.
##
## Movement is free within a radius: a player unit may wander anywhere its
## ReachField allows from where its activation began, undo, or be left and come
## back to. Any action ends its activation.

var field: Field
var rng := RandomNumberGenerator.new()
var turn := 0
var phase := Defs.Phase.PLAYER
var noise := 0
var gaze_center := Vector2.ZERO
var _gaze_on := false
## [{owner, a: Vector2, b: Vector2, half_width, might, origin: Vector2}]
var telegraphs: Array = []
var events: Array = []
var recruited := false
var any_broken := false
var victory_turn := 0
var stats := {"gaze_triggers": 0, "arts_used": 0, "quiet_arts_in_gaze": 0, "enemies_caught": 0, "allies_caught": 0}

## Bumped whenever something other than a free player move changes the floor, so
## cached reach fields know to recompute.
var version := 0
var _reach_cache := {} # unit id -> [version, ReachField]
var _facing_at_start := {} # unit id -> facing when its activation began


func _init(f: Field, seed_value := 0) -> void:
	field = f
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


func _changed() -> void:
	version += 1


# --- Queries -----------------------------------------------------------------

func player_units() -> Array[Unit]:
	return _units_of(Defs.Faction.PLAYER)


func enemy_units() -> Array[Unit]:
	return _units_of(Defs.Faction.ENEMY)


func _units_of(f: int) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in field.living_units():
		if u.faction == f:
			out.append(u)
	return out


func gaze_active() -> bool:
	return _gaze_on


func in_gaze_at(u: Unit, p: Vector2) -> bool:
	return _gaze_on and p.distance_to(gaze_center) <= Defs.GAZE_RADIUS + u.radius * 0.5


func in_gaze(u: Unit) -> bool:
	return in_gaze_at(u, u.pos)


func effective_move(u: Unit) -> float:
	if u.status.has("pinned"):
		return 0.0
	var m := u.move
	if u.status.has("taped"):
		m = maxf(m - 2.0, 0.0)
	return m


func has_movement_penalty(u: Unit) -> bool:
	return u.status.has("pinned") or u.status.has("taped")


## Whether `attacker` may attack `target` at all right now (ignoring reach).
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


## Where `u` can move this activation, measured from where it began.
func reach(u: Unit) -> ReachField:
	var cached: Array = _reach_cache.get(u.id, [])
	if not cached.is_empty() and cached[0] == version and cached[1].start == u.turn_start:
		return cached[1]
	var r := ReachField.compute(field, u, u.turn_start, effective_move(u))
	_reach_cache[u.id] = [version, r]
	return r


func can_move_to(u: Unit, p: Vector2) -> bool:
	return u.can_activate() and reach(u).can_reach(p)


func basic_targets(u: Unit, at := Vector2.INF) -> Array:
	var from := u.pos if at == Vector2.INF else at
	var out: Array = []
	for o in field.living_units():
		if can_target(u, o) and Combat.in_range(u, from, o, o.pos, u.min_range, u.attack_range) and field.has_los(from, o.pos):
			out.append(o)
	return out


## Destructible cover the unit can hit with a Basic Attack: object ids.
func object_targets(u: Unit) -> Array:
	var out: Array = []
	if gaze_active() and in_gaze(u):
		return out
	for o in field.objects.values():
		if not o.destructible:
			continue
		var r: Rect2 = o.rect
		var nearest := Vector2(clampf(u.pos.x, r.position.x, r.end.x), clampf(u.pos.y, r.position.y, r.end.y))
		var g := u.pos.distance_to(nearest) - u.radius
		if g >= u.min_range - 0.001 and g <= u.attack_range + 0.001 and field.has_los(u.pos, r.get_center()):
			out.append(o.id)
	return out


func talk_targets(u: Unit) -> Array:
	var out: Array = []
	for o in field.living_units():
		if o.faction == Defs.Faction.NEUTRAL and o.recruiter == u.id and not o.frozen \
				and u.is_adjacent(o) and not (gaze_active() and (in_gaze(u) or in_gaze(o))):
			out.append(o)
	return out


func art_check(u: Unit, art_id: String) -> Dictionary:
	var art := Arts.get_art(art_id)
	if gaze_active() and art.noise > 0:
		return {"ok": false, "reason": "Unavailable while Human Gaze is active"}
	if art_targets(u, art_id).is_empty():
		return {"ok": false, "reason": "No valid target in reach"}
	return {"ok": true, "reason": ""}


## Units, or aim directions (unit Vector2) for cones.
func art_targets(u: Unit, art_id: String) -> Array:
	var art := Arts.get_art(art_id)
	var out: Array = []
	match art.target:
		"self":
			out.append(u)
		"direction":
			for k in 16:
				out.append(Vector2.RIGHT.rotated(TAU * k / 16.0))
		"ally":
			for o in field.living_units():
				if o.faction != u.faction or o.frozen or o.pending_join:
					continue
				if o == u:
					if art.get("self", false) and not (gaze_active() and in_gaze(o)):
						out.append(o)
					continue
				var g := u.gap_to(o)
				if g >= art.min - 0.001 and g <= art.max + 0.001 and not (gaze_active() and in_gaze(o)):
					out.append(o)
		"enemy":
			for o in field.living_units():
				if not can_target(u, o):
					continue
				if Combat.in_range(u, u.pos, o, o.pos, art.min, art.max) and field.has_los(u.pos, o.pos):
					if art_id == "suction" and o.is_large():
						continue
					out.append(o)
		"lunge":
			for o in field.living_units():
				if can_target(u, o) and not lunge_stop(u, o, art.dash).is_empty():
					out.append(o)
	return out


## Cone of a directional Art aimed along `dir`: {apex, dir, length, half_angle}.
func cone_for(u: Unit, art_id: String, dir: Vector2) -> Dictionary:
	var art := Arts.get_art(art_id)
	return {"apex": u.pos, "dir": dir.normalized(), "length": u.radius + float(art.get("length", 1.8)), "half_angle": Arts.CONE_HALF_ANGLE}


func units_in_cone(u: Unit, cone: Dictionary) -> Array[Unit]:
	var out: Array[Unit] = []
	for o in field.living_units():
		if o == u:
			continue
		if Geometry.circle_in_cone(o.pos, o.radius, cone.apex, cone.dir, cone.length, cone.half_angle) and field.has_los(u.pos, o.pos):
			out.append(o)
	return out


func objects_in_cone(u: Unit, cone: Dictionary) -> Array:
	var out: Array = []
	for o in field.objects.values():
		if not o.destructible:
			continue
		var c: Vector2 = o.rect.get_center()
		if Geometry.circle_in_cone(c, o.rect.size.length() * 0.35, cone.apex, cone.dir, cone.length, cone.half_angle) and field.has_los(u.pos, c):
			out.append(o.id)
	return out


func units_in_strip(a: Vector2, b: Vector2, half_width: float) -> Array[Unit]:
	var out: Array[Unit] = []
	for o in field.living_units():
		if Geometry.circle_hits_strip(o.pos, o.radius, a, b, half_width):
			out.append(o)
	return out


## Where a Lunge toward `target` would stop: the clear straight dash of at most
## `dash` metres that ends right in front of it. Empty if it can't be done.
func lunge_stop(u: Unit, target: Unit, dash: float) -> Array[Vector2]:
	var to := target.pos - u.pos
	var dist := to.length() - u.radius - target.radius - Defs.CONTACT_GAP
	if dist > dash or dist < 0.0:
		return []
	var dir := to.normalized()
	var end := u.pos + dir * dist
	var steps := maxi(int(ceil(dist / 0.1)), 1)
	for k in range(1, steps + 1):
		var p := u.pos.lerp(end, float(k) / steps)
		if field.blocked_by_terrain(p, u.radius):
			return []
		for o in field.living_units():
			if o != u and o != target and p.distance_to(o.pos) < u.radius + o.radius:
				return []
	return [u.pos, end]


# --- Player actions -----------------------------------------------------------

## Free movement: puts the unit at `p` if it is inside its area. Presentation calls
## this as the player steers; nothing is emitted, the view is already there.
func move_unit(u: Unit, p: Vector2) -> bool:
	if not can_move_to(u, p):
		return false
	var dx := p.x - u.pos.x
	if absf(dx) > 0.001:
		u.facing = 1 if dx > 0 else -1
	u.pos = p
	return true


## Puts the unit back where its activation began, as long as it hasn't acted.
func undo_move(u: Unit) -> void:
	if u.acted or u.pos == u.turn_start:
		return
	u.pos = u.turn_start
	u.facing = _facing_at_start.get(u.id, u.facing)
	_emit({"type": "teleport", "unit": u})


## Path length of the unit's current position from where it began.
func distance_moved(u: Unit) -> float:
	return reach(u).cost_at(u.pos)


func attack(u: Unit, target: Unit) -> Dictionary:
	if not basic_targets(u).has(target):
		return {}
	var spec := _player_spec(u, target, {"might": u.might, "type": u.dmg_type})
	var res := _strike(u, target, spec, true)
	_finish_action(u)
	return res


func attack_object(u: Unit, id: String) -> void:
	if not object_targets(u).has(id):
		return
	_hit_object(id, u.power + u.might, u)
	_finish_action(u)


func _hit_object(id: String, amount: int, by: Unit) -> void:
	var o: Dictionary = field.objects[id]
	var kind: String = o.kind
	var rect: Rect2 = o.rect
	var destroyed := field.damage_object(id, amount)
	_changed()
	_emit({"type": "object_hit", "id": id, "kind": kind, "rect": rect, "amount": amount, "destroyed": destroyed, "by": by})


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
	var art := Arts.get_art(art_id)
	if art.target == "direction":
		if not (target is Vector2) or target == Vector2.ZERO:
			return false
	elif not art_targets(u, art_id).has(target):
		return false
	stats.arts_used += 1
	if gaze_active() and art.noise == 0:
		stats.quiet_arts_in_gaze += 1
	_emit({"type": "art", "unit": u, "art": art_id, "name": art.name, "target": target})
	match art_id:
		"guard_beam":
			target.status["guard_beam"] = true
		"flashbulb", "flash_bake":
			var cone := cone_for(u, art_id, target)
			_emit({"type": "area", "shape": "cone", "cone": cone, "kind": art_id})
			var spec_base := {"might": art.might, "type": art.type}
			if art_id == "flash_bake" and u.status.has("heated"):
				spec_base["power_bonus"] = 2
			for o in units_in_cone(u, cone):
				if can_target(u, o):
					var r := _strike(u, o, spec_base.duplicate(), false)
					if art_id == "flashbulb" and r.get("hit", false) and not o.broken:
						o.status["dazzled"] = true
			for id in objects_in_cone(u, cone):
				if field.objects.has(id):
					_hit_object(id, u.power + int(art.might), u)
			if art_id == "flash_bake":
				u.status.erase("heated")
		"pin":
			var r := _strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
			if r.get("hit", false) and not target.broken:
				target.status["pinned"] = true
		"staple_burst":
			_strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
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
				forced_move(target, (target.pos - u.pos).normalized(), 2.0)
		"warm_pour":
			_heal(target, ceili(target.max_hp * 0.3))
		"steady_sip":
			for s in ["dazzled", "pinned", "taped"]:
				if target.status.has(s):
					target.status.erase(s)
					break
			target.status["steady_sip"] = true
		"suction":
			pull_toward(target, u, 3.0)
		"blowback":
			var cone := cone_for(u, art_id, target)
			_emit({"type": "area", "shape": "cone", "cone": cone, "kind": art_id})
			# Push the farthest units first so near ones don't collide with them needlessly.
			var hit_units := units_in_cone(u, cone)
			hit_units.sort_custom(func(a, b): return u.pos.distance_to(a.pos) > u.pos.distance_to(b.pos))
			for o in hit_units:
				if can_target(u, o):
					forced_move(o, (o.pos - u.pos).normalized(), 2.0)
		"lunge":
			var path := lunge_stop(u, target, art.dash)
			u.pos = path[path.size() - 1]
			u.face_along(path)
			_changed()
			_emit({"type": "move", "unit": u, "path": path})
			_strike(u, target, _player_spec(u, target, {"might": art.might, "type": art.type}), false)
		"canopy":
			for o in field.living_units():
				if o != u and o.faction == u.faction and u.is_adjacent(o):
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
	_changed()
	if noise_gain > 0:
		add_noise(noise_gain, u)
	_check_end()


func add_noise(amount: int, source: Unit) -> void:
	noise += amount
	_emit({"type": "noise", "value": noise})
	if noise >= Defs.NOISE_THRESHOLD and not gaze_active():
		noise -= Defs.NOISE_THRESHOLD # overflow is kept
		trigger_gaze(source.pos)


func trigger_gaze(center: Vector2) -> void:
	gaze_center = center
	_gaze_on = true
	stats.gaze_triggers += 1
	var frozen: Array = []
	for u in field.living_units():
		if in_gaze(u) and not u.expected_behavior:
			u.frozen = true
			frozen.append(u)
			if u.faction == Defs.Faction.ENEMY:
				stats.enemies_caught += 1
			elif u.faction == Defs.Faction.PLAYER:
				stats.allies_caught += 1
				u.acted = true
	_changed()
	_emit({"type": "gaze", "center": center, "radius": Defs.GAZE_RADIUS, "frozen": frozen, "noise": noise})


func end_gaze() -> void:
	if not gaze_active():
		return
	var thawed: Array = []
	for u in field.units:
		if u.frozen:
			u.frozen = false
			thawed.append(u)
	_gaze_on = false
	_changed()
	_emit({"type": "gaze_end", "thawed": thawed})


# --- Resolution ----------------------------------------------------------------

## One attack, with optional counter. Returns {hit, crit, damage, ...}.
func _strike(att: Unit, def: Unit, spec: Dictionary, allow_counter: bool) -> Dictionary:
	var target := def
	var intercepted := false
	var lamp := watchful_interceptor(att, def, spec)
	if lamp != null:
		target = lamp
		intercepted = true
		lamp.status["watchful_used"] = true
		spec = spec.duplicate()
		spec["dmg_mult"] = float(spec.get("dmg_mult", 1.0)) * 0.8
	var pv := Combat.preview(field, att, att.pos, target, target.pos, spec)
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
	if allow_counter and not target.broken and not att.broken and can_counter(target, att):
		var cpv := Combat.preview(field, target, target.pos, att, att.pos, {"might": target.might, "type": target.dmg_type})
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


## Lamp's Watchful: once per Enemy Phase, takes a hit meant for an ally right next
## to it, unless the hit could take half of Lamp's HP. Returns Lamp or null.
func watchful_interceptor(att: Unit, def: Unit, spec: Dictionary) -> Unit:
	if att.faction != Defs.Faction.ENEMY or def.id == "lamp" or def.faction != Defs.Faction.PLAYER:
		return null
	var lamp := field.find_unit("lamp")
	if lamp == null or lamp.broken or lamp.frozen or lamp.status.has("watchful_used") \
			or not lamp.is_adjacent(def) or not can_target(att, lamp):
		return null
	var pv := Combat.preview(field, att, att.pos, lamp, lamp.pos, spec)
	return lamp if pv.damage * 2 < lamp.hp else null


func can_counter(defender: Unit, attacker: Unit, att_pos := Vector2.INF) -> bool:
	if defender.frozen or defender.broken:
		return false
	if not can_target(defender, attacker):
		return false
	var ap := attacker.pos if att_pos == Vector2.INF else att_pos
	return Combat.in_range(defender, defender.pos, attacker, ap, defender.min_range, defender.attack_range) \
		and field.has_los(defender.pos, ap)


## The counter `defender` would make against `attacker` standing at `att_pos`.
func counter_preview(attacker: Unit, att_pos: Vector2, defender: Unit) -> Dictionary:
	if not can_counter(defender, attacker, att_pos):
		return {}
	return Combat.preview(field, defender, defender.pos, attacker, att_pos, {"might": defender.might, "type": defender.dmg_type})


func _damage(u: Unit, amount: int) -> void:
	u.hp = maxi(u.hp - amount, 0)
	_emit({"type": "damage", "unit": u, "amount": amount, "hp": u.hp})
	if u.hp == 0:
		u.broken = true
		if u.faction == Defs.Faction.PLAYER:
			any_broken = true
		telegraphs = telegraphs.filter(func(t): return t.owner != u)
		_changed()
		_emit({"type": "broken", "unit": u})


func _heal(u: Unit, amount: int) -> void:
	var before := u.hp
	u.hp = mini(u.hp + amount, u.max_hp)
	_emit({"type": "heal", "unit": u, "amount": u.hp - before, "hp": u.hp})


## Push along `dir` up to `dist` metres. Collision: 10% max HP (rounded up),
## ignores Defense; hitting a unit damages both; at most one collision per push.
func forced_move(u: Unit, dir: Vector2, dist: float) -> void:
	if u.status.has("guard_beam"):
		u.status.erase("guard_beam")
		dist = 0.0
	dist = maxf(dist - u.forced_move_reduction, 0.0)
	var start := u.pos
	var collided: Unit = null
	var hit_wall := false
	var travelled := 0.0
	var step := 0.05
	while travelled < dist - 0.0001:
		var nxt := u.pos + dir * minf(step, dist - travelled)
		if field.blocked_by_terrain(nxt, u.radius):
			hit_wall = true
			break
		var other := _overlapping(u, nxt)
		if other != null:
			collided = other
			break
		u.pos = nxt
		travelled += minf(step, dist - travelled)
	if travelled > 0.01:
		u.displaced_this_phase = true
		_changed()
		_emit({"type": "displace", "unit": u, "path": [start, u.pos]})
	if hit_wall or collided != null:
		_emit({"type": "collision", "unit": u, "other": collided})
		_damage(u, Combat.collision_damage(u))
		if collided != null and not collided.frozen:
			_damage(collided, Combat.collision_damage(collided))


## Pull `u` straight toward `puller` up to `dist` metres, stopping on contact or
## when something is in the way.
func pull_toward(u: Unit, puller: Unit, dist: float) -> void:
	dist = maxf(dist - u.forced_move_reduction, 0.0)
	var start := u.pos
	var travelled := 0.0
	var step := 0.05
	while travelled < dist - 0.0001:
		if u.gap_to(puller) <= Defs.CONTACT_GAP + step:
			break
		var dir := (puller.pos - u.pos).normalized()
		var nxt := u.pos + dir * minf(step, dist - travelled)
		if field.blocked_by_terrain(nxt, u.radius) or _overlapping(u, nxt) != null:
			break
		u.pos = nxt
		travelled += minf(step, dist - travelled)
	if travelled > 0.01:
		u.displaced_this_phase = true
		_changed()
		_emit({"type": "displace", "unit": u, "path": [start, u.pos]})


func _overlapping(u: Unit, p: Vector2) -> Unit:
	for o in field.living_units():
		if o != u and p.distance_to(o.pos) < u.radius + o.radius:
			return o
	return null


# --- Phases --------------------------------------------------------------------

func begin_player_phase() -> void:
	turn += 1
	phase = Defs.Phase.PLAYER
	end_gaze()
	for u in field.living_units():
		u.displaced_this_phase = false
		u.moved_distance = 0.0
		for s in ["guard_beam", "steady_sip", "canopy", "pinned", "watchful_used"]:
			u.status.erase(s)
		if u.status.has("heated") and int(u.status.heated) < turn - 1:
			u.status.erase("heated")
		if u.faction == Defs.Faction.PLAYER:
			u.acted = false
			u.pending_join = false
			u.turn_start = u.pos
			_facing_at_start[u.id] = u.facing
	_changed()
	_emit({"type": "phase", "phase": phase, "turn": turn})
	_comforting_presence()


func _comforting_presence() -> void:
	var cup := field.find_unit("teacup")
	if cup == null or cup.broken or cup.faction != Defs.Faction.PLAYER:
		return
	var best: Unit = null
	for o in player_units():
		if o != cup and o.hp < o.max_hp and cup.is_adjacent(o):
			if best == null or o.hp * best.max_hp < best.hp * o.max_hp:
				best = o
	if best != null:
		_heal(best, ceili(best.max_hp * 0.1))


func end_player_phase() -> void:
	if phase != Defs.Phase.PLAYER:
		return
	# Units that moved but never acted stay where they were left.
	for u in player_units():
		u.status.erase("taped")
		u.turn_start = u.pos
	phase = Defs.Phase.ENEMY
	_changed()
	_emit({"type": "phase", "phase": phase, "turn": turn})
	for u in field.living_units():
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


func check_end() -> bool:
	return _check_end()


func _check_end() -> bool:
	if phase == Defs.Phase.VICTORY or phase == Defs.Phase.DEFEAT:
		return true
	var cutter := field.find_unit("cutter")
	if cutter != null and cutter.broken:
		phase = Defs.Phase.VICTORY
		victory_turn = turn
		_emit({"type": "end", "victory": true})
		return true
	var lamp := field.find_unit("lamp")
	if (lamp != null and lamp.broken) or player_units().is_empty():
		phase = Defs.Phase.DEFEAT
		_emit({"type": "end", "victory": false})
		return true
	return false


func stars() -> Dictionary:
	return {
		"recruit": recruited and not field.find_unit("umbrella").broken,
		"turns": phase == Defs.Phase.VICTORY and victory_turn <= Defs.STAR_TURN_TARGET,
		"unbroken": not any_broken,
	}


# --- Enemy helpers used by EnemyAI --------------------------------------------

func enemy_move(u: Unit, path: Array[Vector2]) -> void:
	if path.size() < 2 or path[path.size() - 1].distance_to(u.pos) < 0.01:
		return
	u.pos = path[path.size() - 1]
	u.face_along(path)
	u.moved_distance = ReachField.path_length(path)
	_changed()
	_emit({"type": "move", "unit": u, "path": path})


func enemy_attack(u: Unit, target: Unit) -> Dictionary:
	var spec := {"might": u.might, "type": u.dmg_type}
	if u.ai == "pencil" and u.moved_distance >= 3.0:
		spec["dmg_mult"] = 1.2 # Charge
	var res := _strike(u, target, spec, true)
	var victim: Unit = res.target
	if res.hit and not victim.broken:
		match u.ai:
			"snarer":
				pull_toward(victim, u, 1.0)
			"roomba":
				forced_move(victim, (victim.pos - u.pos).normalized(), 1.0)
			"tape":
				field.add_slow_circle("tape", victim.pos, Defs.TAPE_RADIUS)
				victim.status["taped"] = true
				_changed()
				_emit({"type": "tape", "pos": victim.pos, "radius": Defs.TAPE_RADIUS, "unit": victim})
	return res


func add_telegraph(owner: Unit, a: Vector2, b: Vector2, half_width: float, might: int) -> void:
	telegraphs.append({"owner": owner, "a": a, "b": b, "half_width": half_width, "might": might, "origin": owner.pos})
	_emit({"type": "telegraph", "unit": owner, "a": a, "b": b, "half_width": half_width})


func resolve_telegraph(owner: Unit) -> void:
	for tg in telegraphs.duplicate():
		if tg.owner != owner:
			continue
		telegraphs.erase(tg)
		# Cancelled if the Captain was displaced or is watched.
		if owner.broken or owner.frozen or owner.pos.distance_to(tg.origin) > 0.01:
			_emit({"type": "telegraph_cancel", "unit": owner})
			continue
		_emit({"type": "art", "unit": owner, "art": "cutting_line", "name": "Cutting Line", "target": tg.b - tg.a})
		_emit({"type": "area", "shape": "strip", "a": tg.a, "b": tg.b, "half_width": tg.half_width, "kind": "cutting_line"})
		for o in field.objects.values().duplicate():
			if o.destructible and Geometry.segment_hits_rect(tg.a, tg.b, o.rect.grow(tg.half_width)):
				_hit_object(o.id, 99, owner)
		for o in units_in_strip(tg.a, tg.b, tg.half_width):
			if o != owner and can_target(owner, o):
				_strike(owner, o, {"might": tg.might, "type": Defs.DmgType.PIERCE, "auto_hit": true, "no_crit": true}, false)
