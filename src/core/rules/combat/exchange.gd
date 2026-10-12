class_name Exchange
extends RefCounted
## The head-to-head preview of one action before it is confirmed: every strike in
## order with its hit chance, damage and crit chance, the counter if there is one,
## and HP before and after if every strike lands. A strike that would Break its
## target is marked `lethal`, and nothing after it is shown for that unit.
## Pure: reads the Battle and changes nothing.


## `action` is "attack", "art:<id>" or "talk". `target` is a Unit, an aim
## direction (cones), a centre point (areas) or a cover object id (attack).
## Returns {title, user, strikes: [{by, on, hit, damage, crit, lethal, counter}],
##          sides: [{unit, hp_before, hp_after}], effect: String}.
static func preview(battle: Battle, u: Unit, action: String, target: Variant) -> Dictionary:
	var out := {"title": "", "user": u, "strikes": [], "sides": [], "effect": ""}
	var hp := {} # Unit -> running HP
	if action == "talk":
		out.title = "Talk"
		out.effect = "%s joins your side next Player Phase." % (target as Unit).name
		_side(out, hp, u)
		_side(out, hp, target)
		return _finish(out, hp)
	if action == "attack":
		out.title = "Attack"
		if target is String:
			var o: Dictionary = battle.field.objects[target]
			out.effect = "Deals %d to the %s (%d HP left)." % [u.power + u.might, o.kind.replace("_", " "), maxi(o.hp - u.power - u.might, 0)]
			_side(out, hp, u)
			return _finish(out, hp)
		var t: Unit = target
		_side(out, hp, u)
		_side(out, hp, t)
		_add_strike(battle, out, hp, u, u.pos, t, player_spec(battle, u, t, {"might": u.might, "type": u.dmg_type}), false)
		if hp[t] > 0:
			var c := battle.counter_preview(u, u.pos, t)
			if not c.is_empty():
				_push(out, hp, t, u, c, true)
		return _finish(out, hp)
	var art_id := action.substr(4)
	var art := Arts.get_art(art_id)
	out.title = art.name
	_side(out, hp, u)
	match art.target:
		"direction":
			var cone := battle.cone_for(u, art_id, target)
			for o in battle.units_in_cone(u, cone):
				if not battle.can_target(u, o):
					continue
				_side(out, hp, o)
				if art.has("might"):
					var spec := {"might": art.might, "type": art.type}
					if art_id == "flash_bake" and u.status.has("heated"):
						spec["power_bonus"] = 2
					_add_strike(battle, out, hp, u, u.pos, o, spec, false)
			out.effect = art.desc
		"lunge":
			var t: Unit = target
			var path := battle.lunge_stop(u, t, art.dash)
			var from: Vector2 = path[path.size() - 1] if not path.is_empty() else u.pos
			_side(out, hp, t)
			_add_strike(battle, out, hp, u, from, t, player_spec(battle, u, t, {"might": art.might, "type": art.type}), false)
		"enemy":
			var t: Unit = target
			_side(out, hp, t)
			if art.has("might"):
				var spec := player_spec(battle, u, t, {"might": art.might, "type": art.type})
				_add_strike(battle, out, hp, u, u.pos, t, spec, false)
				if art_id == "staple_burst" and hp[t] > 0:
					_add_strike(battle, out, hp, u, u.pos, t, spec, false)
				if art_id == "eject":
					out.effect = "On hit: pushed 2 m."
				elif art_id == "pin":
					out.effect = "On hit: can't move next Enemy Phase."
			else:
				out.effect = art.desc
		"ally":
			var t: Unit = target
			_side(out, hp, t)
			if art_id == "warm_pour":
				hp[t] = mini(t.hp + ceili(t.max_hp * 0.3), t.max_hp)
			out.effect = art.desc
		"area":
			for o in battle.units_in_area(battle.area_for(u, art_id, target)):
				if o.faction == u.faction and not o.frozen:
					_side(out, hp, o)
			out.effect = art.desc
		"self":
			if art.has("radius") and art.has("might"):
				for o in battle.storm_targets(u, battle.around(u, art_id)):
					_side(out, hp, o)
					_add_strike(battle, out, hp, u, u.pos, o, player_spec(battle, u, o, {"might": art.might, "type": art.type}), false)
			if art_id == "overheat":
				hp[u] -= battle.overheat_burn(u)
			if art_id == "tea_break":
				for o in battle.allies_in(u, battle.around(u, art_id)):
					_side(out, hp, o)
					hp[o] = mini(o.hp + ceili(o.max_hp * 0.2), o.max_hp)
			out.effect = art.desc
	return _finish(out, hp)


## The spec a player attack would use, without consuming Hot Coils.
static func player_spec(battle: Battle, u: Unit, target: Unit, spec: Dictionary) -> Dictionary:
	if u.status.has("heated"):
		spec["power_bonus"] = 2
	if u.id == "stapler" and (battle.has_movement_penalty(target) or target.displaced_this_phase):
		spec["dmg_mult"] = 1.2 # Opportunist
	return spec


static func _side(out: Dictionary, hp: Dictionary, u: Unit) -> void:
	if hp.has(u):
		return
	hp[u] = u.hp
	out.sides.append({"unit": u, "hp_before": u.hp, "hp_after": u.hp})


static func _add_strike(battle: Battle, out: Dictionary, hp: Dictionary, by: Unit, from: Vector2, on: Unit, spec: Dictionary, counter: bool) -> void:
	if hp[on] <= 0:
		return
	var pv := Combat.preview(battle.field, by, from, on, on.pos, spec)
	_push(out, hp, by, on, pv, counter)


static func _push(out: Dictionary, hp: Dictionary, by: Unit, on: Unit, pv: Dictionary, counter: bool) -> void:
	_side(out, hp, by)
	_side(out, hp, on)
	var after := maxi(hp[on] - pv.damage, 0)
	out.strikes.append({"by": by, "on": on, "hit": pv.hit, "damage": pv.damage, "crit": pv.crit,
		"type_rel": pv.type_rel, "cover": pv.cover, "lethal": after == 0, "counter": counter})
	hp[on] = after


static func _finish(out: Dictionary, hp: Dictionary) -> Dictionary:
	for s in out.sides:
		s.hp_after = hp[s.unit]
	return out
