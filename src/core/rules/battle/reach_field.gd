class_name ReachField
extends RefCounted
## Where one unit can get to from a starting point with a movement budget.
##
## Dijkstra over a fine sampling grid (CELL metres) with diagonal steps, so the
## area follows furniture and the spill's extra cost while the unit itself moves
## freely between samples. Answers the path cost to any point, a smoothed path
## there, and a spread of standing spots for planners. Pure: reads the Field only.

const CELL := 0.25
const INF := 1.0e20
const _DIAG := 1.41421356

var field: Field
var unit: Unit
var start: Vector2
var budget: float
## Furniture only: units don't block (distance fields toward a target).
var ignore_units := false
var cols: int
var rows: int
var cost: PackedFloat32Array
var prev: PackedInt32Array
var _passable: PackedByteArray


static func compute(f: Field, u: Unit, from: Vector2, move_budget: float, terrain_only := false) -> ReachField:
	var r := ReachField.new()
	r.field = f
	r.unit = u
	r.start = from
	r.budget = move_budget
	r.ignore_units = terrain_only
	r._run()
	return r


func cell_center(i: int) -> Vector2:
	return Vector2((i % cols + 0.5) * CELL, (i / cols + 0.5) * CELL)


func cell_of(p: Vector2) -> int:
	var cx := clampi(int(p.x / CELL), 0, cols - 1)
	var cy := clampi(int(p.y / CELL), 0, rows - 1)
	return cy * cols + cx


func _run() -> void:
	cols = int(ceil(field.size.x / CELL))
	rows = int(ceil(field.size.y / CELL))
	var n := cols * rows
	cost = PackedFloat32Array()
	cost.resize(n)
	cost.fill(INF)
	prev = PackedInt32Array()
	prev.resize(n)
	prev.fill(-1)
	_passable = PackedByteArray()
	_passable.resize(n)
	for i in n:
		_passable[i] = 1 if _can_pass(cell_center(i)) else 0
	var heap := _Heap.new()
	# Seed with the cells around the start, so a unit standing between samples
	# isn't stuck when its own cell centre happens to touch something.
	var sc := cell_of(start)
	for dy in range(-1, 2):
		for dx in range(-1, 2):
			var cx := sc % cols + dx
			var cy := sc / cols + dy
			if cx < 0 or cy < 0 or cx >= cols or cy >= rows:
				continue
			var i := cy * cols + cx
			if _passable[i] == 0 and i != sc:
				continue
			var c := start.distance_to(cell_center(i)) * field.cost_multiplier(cell_center(i))
			if c < cost[i] and _segment_clear(start, cell_center(i)):
				cost[i] = c
				prev[i] = -2 # links straight to the start point
				heap.push(c, i)
	var limit := budget + CELL * 2.0
	while not heap.is_empty():
		var top: Array = heap.pop()
		var c: float = top[0]
		var i: int = top[1]
		# Costs are stored as 32-bit floats; compare with slack or nodes get skipped.
		if c > cost[i] + 0.0001:
			continue
		var cx := i % cols
		var cy := i / cols
		var m_here := field.cost_multiplier(cell_center(i))
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				if dx == 0 and dy == 0:
					continue
				var nx := cx + dx
				var ny := cy + dy
				if nx < 0 or ny < 0 or nx >= cols or ny >= rows:
					continue
				var j := ny * cols + nx
				if _passable[j] == 0:
					continue
				if dx != 0 and dy != 0:
					# No cutting corners past furniture.
					if _passable[cy * cols + nx] == 0 or _passable[ny * cols + cx] == 0:
						continue
				var step := (_DIAG if dx != 0 and dy != 0 else 1.0) * CELL
				var nc := c + step * 0.5 * (m_here + field.cost_multiplier(cell_center(j)))
				if nc < cost[j] - 0.0001 and nc <= limit:
					cost[j] = nc
					prev[j] = i
					heap.push(nc, j)


## Path cost to reach `p` (INF if it can't be reached at all).
func cost_at(p: Vector2) -> float:
	if p.distance_to(start) < 0.01:
		return 0.0
	var best := INF
	var base := cell_of(p - Vector2(CELL, CELL) * 0.5)
	for dy in 2:
		for dx in 2:
			var cx := base % cols + dx
			var cy := base / cols + dy
			if cx >= cols or cy >= rows:
				continue
			var i := cy * cols + cx
			if cost[i] >= INF:
				continue
			var c := cost[i] + cell_center(i).distance_to(p) * field.cost_multiplier(p)
			best = minf(best, c)
	if _segment_clear(start, p):
		best = minf(best, start.distance_to(p) * field.cost_multiplier(p))
	return best


## Whether the unit may end its move with its centre on `p`.
func can_reach(p: Vector2) -> bool:
	if p.distance_to(start) < 0.01:
		return true
	return cost_at(p) <= budget + 0.001 and field.can_stand(unit, p)


## How far toward `target` the unit can get from `from` along a straight line,
## staying inside its area. Used to steer the unit with a stick or keys.
func clamp_step(from: Vector2, target: Vector2) -> Vector2:
	if can_reach(target):
		return target
	var lo := 0.0
	var hi := 1.0
	for _i in 10:
		var mid := (lo + hi) * 0.5
		if can_reach(from.lerp(target, mid)):
			lo = mid
		else:
			hi = mid
	return from.lerp(target, lo)


## A walkable path from the start to `p`, smoothed. Empty if `p` is out of reach.
func path_to(p: Vector2) -> Array[Vector2]:
	var out: Array[Vector2] = []
	if p.distance_to(start) < 0.01:
		out.append(start)
		return out
	if cost_at(p) >= INF:
		return out
	if _segment_clear(start, p) and start.distance_to(p) * field.cost_multiplier(p) <= cost_at(p) + 0.001:
		out.append(start)
		out.append(p)
		return out
	# Walk back from the cheapest cell near p.
	var best_i := -1
	var best_c := INF
	var base := cell_of(p - Vector2(CELL, CELL) * 0.5)
	for dy in 2:
		for dx in 2:
			var cx := base % cols + dx
			var cy := base / cols + dy
			if cx >= cols or cy >= rows:
				continue
			var i := cy * cols + cx
			var c := cost[i] + cell_center(i).distance_to(p)
			if cost[i] < INF and c < best_c:
				best_c = c
				best_i = i
	if best_i < 0:
		return out
	var rev: Array[Vector2] = [p]
	var i := best_i
	var guard := 0
	while i >= 0 and guard < cols * rows:
		rev.append(cell_center(i))
		i = prev[i]
		guard += 1
	rev.append(start)
	rev.reverse()
	return _smooth(rev)


static func path_length(path: Array[Vector2]) -> float:
	var total := 0.0
	for k in range(1, path.size()):
		total += path[k - 1].distance_to(path[k])
	return total


## Standing spots the unit can reach, roughly `spacing` apart, cheapest first.
func standing_spots(spacing := 0.5) -> Array[Vector2]:
	var step := maxi(int(round(spacing / CELL)), 1)
	var found: Array = []
	for cy in range(0, rows, step):
		for cx in range(0, cols, step):
			var i := cy * cols + cx
			if cost[i] <= budget and field.can_stand(unit, cell_center(i)):
				found.append([cost[i], cell_center(i)])
	found.sort_custom(func(a, b): return a[0] < b[0])
	var out: Array[Vector2] = [start]
	for f in found:
		out.append(f[1])
	return out


func _segment_clear(a: Vector2, b: Vector2) -> bool:
	var d := a.distance_to(b)
	var steps := maxi(int(ceil(d / (CELL * 0.4))), 1)
	for k in range(1, steps + 1):
		var p := a.lerp(b, float(k) / steps)
		if not _can_pass(p):
			return false
		if field.is_slow(p) != field.is_slow(a):
			# Keep paths honest about entering or leaving the spill.
			return false
	return true


func _can_pass(p: Vector2) -> bool:
	if ignore_units:
		return not field.blocked_by_terrain(p, unit.radius) and not field.light_blocks(unit, p)
	return field.can_pass(unit, p)


func _smooth(points: Array[Vector2]) -> Array[Vector2]:
	var out: Array[Vector2] = [points[0]]
	var k := 0
	while k < points.size() - 1:
		var far := k + 1
		for j in range(points.size() - 1, k + 1, -1):
			if _segment_clear(points[k], points[j]):
				far = j
				break
		out.append(points[far])
		k = far
	return out


## Minimal binary heap of [priority, value].
class _Heap:
	var _items: Array = []

	func is_empty() -> bool:
		return _items.is_empty()

	func push(p: float, v: int) -> void:
		_items.append([p, v])
		var i := _items.size() - 1
		while i > 0:
			var parent := (i - 1) / 2
			if _items[parent][0] <= _items[i][0]:
				break
			var t: Array = _items[parent]
			_items[parent] = _items[i]
			_items[i] = t
			i = parent

	func pop() -> Array:
		var top: Array = _items[0]
		var last: Array = _items.pop_back()
		if not _items.is_empty():
			_items[0] = last
			var i := 0
			var n := _items.size()
			while true:
				var l := i * 2 + 1
				var r := l + 1
				var m := i
				if l < n and _items[l][0] < _items[m][0]:
					m = l
				if r < n and _items[r][0] < _items[m][0]:
					m = r
				if m == i:
					break
				var t: Array = _items[m]
				_items[m] = _items[i]
				_items[i] = t
				i = m
		return top
