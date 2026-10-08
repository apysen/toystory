class_name EnemyAI
extends RefCounted
## Readable enemy behaviour (vertical_slice_plan.md section 14).

const CUTTING_LINE_LENGTH := 5
const CUTTING_LINE_MIGHT := 7
const GUARD_LEASH := 2

var battle: Battle
var board: Board


func _init(b: Battle) -> void:
	battle = b
	board = b.board


func run_phase() -> void:
	for u in battle.enemy_units():
		if battle.phase != Defs.Phase.ENEMY:
			return
		if u.broken or u.frozen:
			continue
		u.move_path_len = 0
		act(u)
		if battle._check_end():
			return


func act(u: Unit) -> void:
	if u.ai == "captain":
		_captain(u)
		return
	var plan := best_plan(u)
	if plan.is_empty():
		_advance(u)
		return
	battle.enemy_move(u, plan.anchor, plan.path)
	if plan.target != null and battle.can_target(u, plan.target):
		battle.enemy_attack(u, plan.target)


## Best (anchor, target) pair by archetype score, or {} if no target is reachable.
func best_plan(u: Unit) -> Dictionary:
	var m := board.reach_map(u, u.pos, battle.effective_move(u))
	var best := {}
	var best_score := -INF
	for anchor in m:
		if anchor != u.pos and not board.can_stand(u, anchor):
			continue
		if u.ai == "guard" and not _guard_may_use(u, anchor):
			continue
		for t in board.living_units():
			if not battle.can_target(u, t):
				continue
			if not Combat.in_range(u, anchor, t, t.pos, u.min_range, u.attack_range):
				continue
			var saved := u.pos
			u.pos = anchor
			var los := board.has_los(u, anchor, t, t.pos)
			u.pos = saved
			if not los:
				continue
			var s := score(u, anchor, t, m[anchor].cost)
			if s > best_score:
				best_score = s
				best = {"anchor": anchor, "target": t, "path": Board.path_from(m, anchor), "score": s}
	return best


func score(u: Unit, anchor: Vector2i, t: Unit, cost: int) -> float:
	var spec := {"might": u.might, "type": u.dmg_type}
	if u.ai == "pencil" and cost >= 3:
		spec["dmg_mult"] = 1.2
	var pv := Combat.preview(board, u, anchor, t, t.pos, spec)
	var s: float = pv.expected
	if pv.damage >= t.hp:
		s += 10.0
	var hp_frac := float(t.hp) / t.max_hp
	match u.ai:
		"pencil":
			if pv.type_rel > 0:
				s += 10.0
			if not pv.cover:
				s += 5.0
			s += (1.0 - hp_frac) * 8.0
		"snarer":
			if _in_cover(t):
				s += 12.0
		"tape":
			if not board.slow_tiles.has(t.pos):
				s += 6.0
			if t.is_large():
				s += 4.0
		"roomba":
			s += 2.0
		"guard":
			s += 0.0
	# Neutral recruits are a secondary target.
	if t.faction == Defs.Faction.NEUTRAL:
		s -= 3.0
	# Slight preference for not walking further than needed.
	s -= cost * 0.05
	return s


func _in_cover(t: Unit) -> bool:
	if t.is_large():
		return false
	for d in Defs.DIRS:
		if board.terrain_at(t.pos + d) == Defs.Terrain.HALF_COVER:
			return true
	return false


## Bookend Guard holds the central route unless the local defence has collapsed.
func _guard_may_use(u: Unit, anchor: Vector2i) -> bool:
	var home: Vector2i = u.status.get("home", u.pos)
	u.status["home"] = home
	if _defence_collapsed():
		return true
	return Defs.manhattan(anchor, home) <= GUARD_LEASH


func _defence_collapsed() -> bool:
	var down := 0
	for e in board.units:
		if e.faction == Defs.Faction.ENEMY and e.broken:
			down += 1
	return down >= 3


## No target in reach: walk along the real path toward the closest hostile.
## The Bookend Guard holds its lane instead.
func _advance(u: Unit) -> void:
	if u.ai == "guard" and not _defence_collapsed():
		return
	var budget := battle.effective_move(u)
	if budget <= 0:
		return
	var goal := _nearest_hostile(u)
	if goal == null:
		return
	var field := _distance_field(u, goal)
	var m := board.reach_map(u, u.pos, budget)
	var best_anchor := u.pos
	var best_d: int = field.get(u.pos, 1 << 20)
	for a in m:
		if a != u.pos and not board.can_stand(u, a):
			continue
		var d: int = field.get(a, 1 << 20)
		if d < best_d:
			best_d = d
			best_anchor = a
	battle.enemy_move(u, best_anchor, Board.path_from(m, best_anchor))


## Steps from each anchor to any anchor in attack range of `goal`, by terrain only.
func _distance_field(u: Unit, goal: Unit) -> Dictionary:
	var field := {}
	var queue: Array[Vector2i] = []
	for x in range(1, board.width + 1):
		for y in range(1, board.height + 1):
			var a := Vector2i(x, y)
			if _terrain_ok(u, a) and u.distance_to_unit(a, goal, goal.pos) <= u.attack_range \
					and u.distance_to_unit(a, goal, goal.pos) >= 1:
				field[a] = 0
				queue.append(a)
	var i := 0
	while i < queue.size():
		var at := queue[i]
		i += 1
		for d in Defs.DIRS:
			var n: Vector2i = at + d
			if field.has(n) or not _terrain_ok(u, n):
				continue
			field[n] = field[at] + board.step_cost(u, n)
			queue.append(n)
	return field


func _terrain_ok(u: Unit, a: Vector2i) -> bool:
	for t in u.tiles_at(a):
		if not board.in_bounds(t) or board.is_blocking_terrain(t):
			return false
	return true


func _nearest_hostile(u: Unit) -> Unit:
	var best: Unit = null
	var bd := 1 << 30
	for t in board.living_units():
		if not u.is_hostile_to(t) or t.broken:
			continue
		var d := u.distance_to_unit(u.pos, t, t.pos)
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
		battle.enemy_move(u, plan.anchor, plan.path)
		if battle.can_target(u, plan.target):
			battle.enemy_attack(u, plan.target)
	else:
		_advance(u)
	if u.broken or u.frozen:
		return
	var lane := best_lane(u)
	if not lane.is_empty():
		battle.add_telegraph(u, lane.tiles, lane.dir, CUTTING_LINE_MIGHT)


func lane_tiles(u: Unit, dir: Vector2i) -> Array:
	var out: Array = []
	var at := u.pos
	for i in CUTTING_LINE_LENGTH:
		at += dir
		if not board.in_bounds(at) or board.blocks_sight(at):
			break
		out.append(at)
	return out


## Lane with the most player units in it; none if it would hit nobody.
func best_lane(u: Unit) -> Dictionary:
	var best := {}
	var best_n := 0
	for d in Defs.DIRS:
		var tiles := lane_tiles(u, d)
		var n := 0
		for o in battle.units_in_tiles(tiles):
			if o.faction != Defs.Faction.ENEMY:
				n += 1
		if n > best_n:
			best_n = n
			best = {"dir": d, "tiles": tiles}
	return best
