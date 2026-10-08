class_name EnemyAI
extends RefCounted
## Readable enemy behaviour (vertical_slice_plan.md section 14).

const CUTTING_LINE_LENGTH := 5.0
const CUTTING_LINE_HALF_WIDTH := 0.45
const CUTTING_LINE_MIGHT := 7
## Metres the Bookend Guard strays from where it started until the defence collapses.
const GUARD_LEASH := 2.0
## Spacing of the standing spots a planner considers.
const SPOT_SPACING := 0.4

var battle: Battle
var field: Field


func _init(b: Battle) -> void:
	battle = b
	field = b.field


func run_phase() -> void:
	for u in battle.enemy_units():
		if battle.phase != Defs.Phase.ENEMY:
			return
		if u.broken or u.frozen:
			continue
		u.moved_distance = 0.0
		act(u)
		if battle.check_end():
			return


func act(u: Unit) -> void:
	if u.ai == "captain":
		_captain(u)
		return
	var plan := best_plan(u)
	if plan.is_empty():
		_advance(u)
		return
	battle.enemy_move(u, plan.path)
	if plan.target != null and battle.can_target(u, plan.target):
		battle.enemy_attack(u, plan.target)


## Best (spot, target) pair by archetype score, or {} if no target is reachable.
func best_plan(u: Unit) -> Dictionary:
	var r := ReachField.compute(field, u, u.pos, battle.effective_move(u))
	var best := {}
	var best_score := -INF
	for s in r.standing_spots(SPOT_SPACING):
		if u.ai == "guard" and not guard_may_stand(battle, u, s):
			continue
		var cost := r.cost_at(s)
		for t in field.living_units():
			if not battle.can_target(u, t):
				continue
			if not Combat.in_range(u, s, t, t.pos, u.min_range, u.attack_range) or not field.has_los(s, t.pos):
				continue
			var sc := score(u, s, t, cost)
			if sc > best_score:
				best_score = sc
				best = {"spot": s, "target": t, "score": sc}
	if not best.is_empty():
		best["path"] = r.path_to(best.spot)
		if best.path.is_empty():
			best.path = [u.pos] as Array[Vector2]
	return best


func score(u: Unit, s: Vector2, t: Unit, cost: float) -> float:
	var spec := {"might": u.might, "type": u.dmg_type}
	if u.ai == "pencil" and cost >= 3.0:
		spec["dmg_mult"] = 1.2
	var pv := Combat.preview(field, u, s, t, t.pos, spec)
	var sc: float = pv.expected
	if pv.damage >= t.hp:
		sc += 10.0
	var hp_frac := float(t.hp) / t.max_hp
	match u.ai:
		"pencil":
			if pv.type_rel > 0:
				sc += 10.0
			if not pv.cover:
				sc += 5.0
			sc += (1.0 - hp_frac) * 8.0
		"snarer":
			if _in_cover(t):
				sc += 12.0
		"tape":
			if not field.is_slow(t.pos):
				sc += 6.0
			if t.is_large():
				sc += 4.0
		"roomba":
			sc += 2.0
	# Neutral recruits are a secondary target.
	if t.faction == Defs.Faction.NEUTRAL:
		sc -= 3.0
	# Slight preference for not walking further than needed.
	sc -= cost * 0.05
	return sc


## Whether a unit is tucked against half cover (the Snarer wants to pull it out).
func _in_cover(t: Unit) -> bool:
	if t.is_large():
		return false
	for o in field.objects.values():
		if o.cover == Defs.Cover.HALF and Geometry.circle_hits_rect(t.pos, t.radius + 0.4, o.rect):
			return true
	return false


## Bookend Guard holds the central route unless the local defence has collapsed.
static func guard_may_stand(b: Battle, u: Unit, s: Vector2) -> bool:
	var home: Vector2 = u.status.get("home", u.pos)
	u.status["home"] = home
	if defence_collapsed(b):
		return true
	return s.distance_to(home) <= GUARD_LEASH


static func defence_collapsed(b: Battle) -> bool:
	var down := 0
	for e in b.field.units:
		if e.faction == Defs.Faction.ENEMY and e.broken:
			down += 1
	return down >= 3


## No target in reach: walk along the real path toward the closest hostile.
## The Bookend Guard holds its lane instead.
func _advance(u: Unit) -> void:
	if u.ai == "guard" and not defence_collapsed(battle):
		return
	var budget := battle.effective_move(u)
	if budget <= 0.0:
		return
	var goal := _nearest_hostile(u)
	if goal == null:
		return
	# How far each spot is from the goal, walking around furniture.
	var toward := ReachField.compute(field, u, goal.pos, field.size.length() * 2.0, true)
	var r := ReachField.compute(field, u, u.pos, budget)
	var best := u.pos
	var best_d := toward.cost_at(u.pos)
	for s in r.standing_spots(SPOT_SPACING):
		var d := toward.cost_at(s)
		if d < best_d - 0.05:
			best_d = d
			best = s
	if best != u.pos:
		battle.enemy_move(u, r.path_to(best))


func _nearest_hostile(u: Unit) -> Unit:
	var best: Unit = null
	var bd := INF
	for t in field.living_units():
		if not u.is_hostile_to(t):
			continue
		var d := u.gap_to(t)
		if d < bd:
			bd = d
			best = t
	return best


# --- Paper Cutter Captain -----------------------------------------------------

## Alternates: resolve a pending Cutting Line, or act normally and then mark a new one.
func _captain(u: Unit) -> void:
	for tg in battle.telegraphs:
		if tg.owner == u:
			battle.resolve_telegraph(u)
			return
	var plan := best_plan(u)
	if not plan.is_empty():
		battle.enemy_move(u, plan.path)
		if battle.can_target(u, plan.target):
			battle.enemy_attack(u, plan.target)
	else:
		_advance(u)
	if u.broken or u.frozen:
		return
	var lane := best_lane(u)
	if not lane.is_empty():
		battle.add_telegraph(u, lane.a, lane.b, CUTTING_LINE_HALF_WIDTH, CUTTING_LINE_MIGHT)


## The lane from the Captain along `dir`, cut short by full cover.
func lane(u: Unit, dir: Vector2) -> Dictionary:
	var a := u.pos + dir * u.radius
	var b := a
	var step := 0.1
	var travelled := 0.0
	while travelled < CUTTING_LINE_LENGTH:
		var nxt := b + dir * step
		if not field.bounds().has_point(nxt) or not field.has_los(a, nxt):
			break
		b = nxt
		travelled += step
	return {"a": a, "b": b, "dir": dir}


## The lane through the most player-side units; none if it would hit nobody.
## Aims straight at each unit within reach of the blade, and at eight compass points.
func best_lane(u: Unit) -> Dictionary:
	var dirs: Array[Vector2] = []
	for k in 8:
		dirs.append(Vector2.RIGHT.rotated(TAU * k / 8.0))
	for t in field.living_units():
		if t.faction != Defs.Faction.ENEMY and u.gap_to(t) <= CUTTING_LINE_LENGTH:
			dirs.append((t.pos - u.pos).normalized())
	var best := {}
	var best_n := 0
	for d in dirs:
		var l := lane(u, d)
		var n := 0
		for o in battle.units_in_strip(l.a, l.b, CUTTING_LINE_HALF_WIDTH):
			if o.faction != Defs.Faction.ENEMY:
				n += 1
		if n > best_n:
			best_n = n
			best = l
	return best
