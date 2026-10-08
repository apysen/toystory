class_name Forecast
extends RefCounted
## Dynamic movement forecast (vertical_slice_plan.md section 18): "what happens
## if Enemy Phase began with the battlefield in its current state?"


## Threats against `u` if it ended its move at `anchor`.
## Returns {threats: Array, telegraph_damage, expected, predicted_hp, max_damage, risk}.
## Each threat: {enemy, from, preview, displacement: {dir, dist} or {}}.
static func for_destination(battle: Battle, u: Unit, anchor: Vector2i) -> Dictionary:
	var board := battle.board
	var saved := u.pos
	u.pos = anchor
	var threats: Array = []
	var expected := 0.0
	var max_damage := 0
	var watched := battle.gaze_active() and battle.in_gaze(u)
	if not watched and not u.frozen:
		for e in battle.enemy_units():
			if e.frozen:
				continue
			if battle.gaze_active() and (e.expected_behavior or battle.in_gaze(e)):
				continue
			if e.ai == "captain" and _captain_resolving(battle, e):
				continue # it spends its turn on the Cutting Line
			var spot := _attack_spot(battle, e, u)
			if spot == Vector2i(-99, -99):
				continue
			var spec := {"might": e.might, "type": e.dmg_type}
			var pv := Combat.preview(board, e, spot, u, anchor, spec)
			var disp := {}
			match e.ai:
				"snarer":
					disp = {"dir": Battle._straight_dir(anchor, spot), "dist": maxi(1 - u.forced_move_reduction, 0)}
				"roomba":
					disp = {"dir": Battle._straight_dir(spot, anchor), "dist": maxi(1 - u.forced_move_reduction, 0)}
			threats.append({"enemy": e, "from": spot, "preview": pv, "displacement": disp})
			expected += pv.expected
			max_damage += pv.damage * Defs.CRIT_MULT if pv.crit > 0 else pv.damage
	var tele := 0
	for tg in battle.telegraphs:
		for t in u.tiles():
			if tg.tiles.has(t):
				var pv := Combat.preview(board, tg.owner, tg.owner.pos, u, anchor,
					{"might": tg.might, "type": Defs.DmgType.PIERCE, "auto_hit": true, "no_crit": true})
				tele += pv.damage
				break
	u.pos = saved
	expected += tele
	max_damage += tele
	var predicted := maxi(int(round(u.hp - expected)), 0)
	var risk := "Safe"
	if threats.size() > 0 or tele > 0:
		risk = "Exposed"
		if predicted <= u.max_hp * 0.35:
			risk = "High Risk"
		if max_damage >= u.hp:
			risk = "Broken Risk"
	return {"threats": threats, "telegraph_damage": tele, "expected": expected,
		"predicted_hp": predicted, "max_damage": max_damage, "risk": risk}


static func _captain_resolving(battle: Battle, e: Unit) -> bool:
	for tg in battle.telegraphs:
		if tg.owner == e:
			return true
	return false


## A tile the enemy could reach this Enemy Phase and attack `target` from, or (-99,-99).
static func _attack_spot(battle: Battle, e: Unit, target: Unit) -> Vector2i:
	var board := battle.board
	if not target.is_hostile_to(e) and not e.is_hostile_to(target):
		return Vector2i(-99, -99)
	var m := board.reach_map(e, e.pos, battle.effective_move(e))
	var best := Vector2i(-99, -99)
	var best_cost := 1 << 30
	for a in m:
		if a != e.pos and not board.can_stand(e, a):
			continue
		if e.ai == "guard" and Defs.manhattan(a, e.status.get("home", e.pos)) > EnemyAI.GUARD_LEASH:
			continue
		if not Combat.in_range(e, a, target, target.pos, e.min_range, e.attack_range):
			continue
		if not board.has_los(e, a, target, target.pos):
			continue
		if m[a].cost < best_cost:
			best_cost = m[a].cost
			best = a
	return best


## Every tile some enemy could attack this phase (danger overlay).
static func danger_tiles(battle: Battle) -> Dictionary:
	var board := battle.board
	var out := {}
	for e in battle.enemy_units():
		if e.frozen or (battle.gaze_active() and e.expected_behavior):
			continue
		var m := board.reach_map(e, e.pos, battle.effective_move(e))
		for a in m:
			if a != e.pos and not board.can_stand(e, a):
				continue
			for x in range(a.x - e.attack_range, a.x + e.size + e.attack_range):
				for y in range(a.y - e.attack_range, a.y + e.size + e.attack_range):
					var t := Vector2i(x, y)
					if board.in_bounds(t) and e.distance_from(a, t) <= e.attack_range and e.distance_from(a, t) >= e.min_range:
						out[t] = true
	return out
