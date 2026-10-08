class_name Board
extends RefCounted
## Grid, terrain, occupancy, line of sight and pathfinding. Pure logic, no nodes.

var width: int
var height: int
## tile -> {kind, terrain, hp, max_hp, destructible}
var objects := {}
## tile -> true for spill and sticky tape tiles
var slow_tiles := {}
var units: Array[Unit] = []


func _init(w: int, h: int) -> void:
	width = w
	height = h


func in_bounds(t: Vector2i) -> bool:
	return t.x >= 1 and t.y >= 1 and t.x <= width and t.y <= height


func add_object(t: Vector2i, kind: String, terrain: int, hp := 0) -> void:
	objects[t] = {"kind": kind, "terrain": terrain, "hp": hp, "max_hp": hp, "destructible": hp > 0}


func terrain_at(t: Vector2i) -> int:
	if objects.has(t):
		return objects[t].terrain
	if slow_tiles.has(t):
		return Defs.Terrain.SPILL
	return Defs.Terrain.FLOOR


func is_blocking_terrain(t: Vector2i) -> bool:
	var tr := terrain_at(t)
	return tr == Defs.Terrain.FULL_COVER or tr == Defs.Terrain.HALF_COVER


func blocks_sight(t: Vector2i) -> bool:
	return terrain_at(t) == Defs.Terrain.FULL_COVER


func unit_at(t: Vector2i) -> Unit:
	for u in units:
		if not u.broken and u.occupies(t):
			return u
	return null


func living_units() -> Array[Unit]:
	var out: Array[Unit] = []
	for u in units:
		if not u.broken:
			out.append(u)
	return out


func find_unit(id: String) -> Unit:
	for u in units:
		if u.id == id:
			return u
	return null


## Whether `unit` could stand with its anchor at `anchor` (ignoring itself).
func can_stand(unit: Unit, anchor: Vector2i) -> bool:
	for t in unit.tiles_at(anchor):
		if not in_bounds(t) or is_blocking_terrain(t):
			return false
		var o := unit_at(t)
		if o != null and o != unit:
			return false
	return true


## Whether `unit` may pass through the footprint at `anchor` (allies can be passed).
func can_pass(unit: Unit, anchor: Vector2i) -> bool:
	for t in unit.tiles_at(anchor):
		if not in_bounds(t) or is_blocking_terrain(t):
			return false
		var o := unit_at(t)
		if o != null and o != unit:
			if o.frozen or o.faction != unit.faction:
				return false
	return true


func step_cost(unit: Unit, anchor: Vector2i) -> int:
	for t in unit.tiles_at(anchor):
		if slow_tiles.has(t):
			return 1 + Defs.SPILL_EXTRA_COST
	return 1


## Dijkstra over anchors. Returns anchor -> {"cost": int, "prev": Vector2i}.
## Includes pass-through tiles; filter with can_stand for destinations.
func reach_map(unit: Unit, start: Vector2i, budget: int) -> Dictionary:
	var dist := {start: {"cost": 0, "prev": start}}
	var frontier: Array = [[0, start]]
	while not frontier.is_empty():
		var best_i := 0
		for i in frontier.size():
			if frontier[i][0] < frontier[best_i][0]:
				best_i = i
		var cur: Array = frontier.pop_at(best_i)
		var cost: int = cur[0]
		var at: Vector2i = cur[1]
		if cost > dist[at].cost:
			continue
		for d in Defs.DIRS:
			var nxt: Vector2i = at + d
			if not can_pass(unit, nxt):
				continue
			var nc := cost + step_cost(unit, nxt)
			if nc > budget:
				continue
			if not dist.has(nxt) or nc < dist[nxt].cost:
				dist[nxt] = {"cost": nc, "prev": at}
				frontier.append([nc, nxt])
	return dist


## Anchors the unit can end its move on.
func reachable(unit: Unit, start: Vector2i, budget: int) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var m := reach_map(unit, start, budget)
	for a in m:
		if a == start or can_stand(unit, a):
			out.append(a)
	return out


static func path_from(m: Dictionary, goal: Vector2i) -> Array[Vector2i]:
	var path: Array[Vector2i] = []
	if not m.has(goal):
		return path
	var at := goal
	while true:
		path.push_front(at)
		var prev: Vector2i = m[at].prev
		if prev == at:
			break
		at = prev
	return path


## Line of sight between two tiles: blocked if the segment between tile centres
## passes through any full-cover tile other than the endpoints. Grazing a corner
## does not block.
func has_los_tiles(a: Vector2i, b: Vector2i) -> bool:
	if a == b:
		return true
	var fa := Vector2(a) + Vector2(0.5, 0.5)
	var fb := Vector2(b) + Vector2(0.5, 0.5)
	var steps := int(ceil(fa.distance_to(fb) * 8.0))
	for i in range(1, steps):
		var p := fa.lerp(fb, float(i) / steps)
		# Shrink each sample slightly toward the tile interior so corner grazes pass.
		var t := Vector2i(floori(p.x), floori(p.y))
		if t == a or t == b:
			continue
		var local := p - Vector2(t)
		if local.x < 0.02 or local.x > 0.98 or local.y < 0.02 or local.y > 0.98:
			continue
		if blocks_sight(t):
			return false
	return true


## LOS from any tile of `attacker` at `from_anchor` to any tile of `target`.
func has_los(attacker: Unit, from_anchor: Vector2i, target: Unit, target_anchor: Vector2i) -> bool:
	for a in attacker.tiles_at(from_anchor):
		for b in target.tiles_at(target_anchor):
			if has_los_tiles(a, b):
				return true
	return false


func has_los_to_tile(attacker: Unit, from_anchor: Vector2i, t: Vector2i) -> bool:
	for a in attacker.tiles_at(from_anchor):
		if has_los_tiles(a, t):
			return true
	return false


## Half cover applies to a ranged attack when a half-cover object sits on the
## side of the defender facing the attacker. Large units can't use small cover.
func has_half_cover(defender: Unit, def_anchor: Vector2i, attacker_tile: Vector2i) -> bool:
	if defender.is_large():
		return false
	var t := def_anchor
	var to_attacker := attacker_tile - t
	for d in Defs.DIRS:
		var n: Vector2i = t + d
		if terrain_at(n) != Defs.Terrain.HALF_COVER:
			continue
		if d.x * to_attacker.x + d.y * to_attacker.y > 0:
			return true
	return false


func damage_object(t: Vector2i, amount: int) -> bool:
	if not objects.has(t) or not objects[t].destructible:
		return false
	objects[t].hp -= amount
	if objects[t].hp <= 0:
		objects.erase(t)
		return true
	return false


func is_destructible(t: Vector2i) -> bool:
	return objects.has(t) and objects[t].destructible
