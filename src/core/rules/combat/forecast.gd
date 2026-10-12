class_name Forecast
extends RefCounted
## Dynamic movement forecast (vertical_slice_plan.md section 18): "what happens
## if Enemy Phase began with the battlefield in its current state?"
##
## Free movement asks this every frame, so the slow part (where every enemy could
## stand) is computed once into a ThreatMap when a unit is selected, and each query
## only checks reach and line of sight from those spots.


## Where each enemy could attack from this Enemy Phase, computed with `u` lifted
## off the floor so it doesn't block the paths it is being warned about.
class ThreatMap:
	var battle: Battle
	var unit: Unit
	var version := -1
	## [{enemy, spots: Array[Vector2]}], spots cheapest first
	var entries: Array = []

	func _init(b: Battle, u: Unit) -> void:
		battle = b
		unit = u
		rebuild()

	func is_current() -> bool:
		return version == battle.version

	func rebuild() -> void:
		version = battle.version
		entries.clear()
		var saved := unit.pos
		unit.pos = Vector2(-1000, -1000)
		for e in battle.enemy_units():
			if not Forecast._may_threaten(battle, e):
				continue
			var r := ReachField.compute(battle.field, e, e.pos, battle.effective_move(e))
			var spots: Array[Vector2] = []
			for s in r.standing_spots(0.35):
				if e.ai == "guard" and not EnemyAI.guard_may_stand(battle, e, s):
					continue
				spots.append(s)
			entries.append({"enemy": e, "spots": spots})
		unit.pos = saved


## Threats against `u` if it ended its move at `p`. Pass the unit's ThreatMap
## when asking repeatedly. Returns {threats, telegraph_damage, expected,
## predicted_hp, max_damage, risk}; each threat is {enemy, from, preview,
## displacement: {dir, dist} or {}}.
static func for_destination(battle: Battle, u: Unit, p: Vector2, map: ThreatMap = null) -> Dictionary:
	var field := battle.field
	if map == null or map.unit != u or not map.is_current():
		map = ThreatMap.new(battle, u)
	var threats: Array = []
	var expected := 0.0
	var max_damage := 0
	var watched := battle.gaze_active() and battle.in_gaze_at(u, p)
	if not watched and not u.frozen:
		for entry in map.entries:
			var e: Unit = entry.enemy
			if not e.is_hostile_to(u):
				continue
			var spot := _attack_spot(battle, e, entry.spots, u, p)
			if spot == Vector2.INF:
				continue
			var spec := {"might": e.might, "type": e.dmg_type}
			if e.ai == "pencil" and spot.distance_to(e.pos) >= 3.0:
				spec["dmg_mult"] = 1.2
			var pv := Combat.preview(field, e, spot, u, p, spec)
			var disp := {}
			match e.ai:
				"snarer":
					disp = {"dir": (spot - p).normalized(), "dist": maxf(1.0 - u.forced_move_reduction, 0.0)}
				"roomba":
					disp = {"dir": (p - spot).normalized(), "dist": maxf(1.0 - u.forced_move_reduction, 0.0)}
			threats.append({"enemy": e, "from": spot, "preview": pv, "displacement": disp})
			expected += pv.expected
			max_damage += pv.damage * Defs.CRIT_MULT if pv.crit > 0 else pv.damage
	var tele := 0
	for tg in battle.telegraphs:
		if Geometry.circle_hits_strip(p, u.radius, tg.a, tg.b, tg.half_width):
			var pv := Combat.preview(field, tg.owner, tg.owner.pos, u, p,
				{"might": tg.might, "type": Defs.DmgType.PIERCE, "auto_hit": true, "no_crit": true})
			tele += pv.damage
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


## Every enemy's combined danger zone for the next Enemy Phase, on the ReachField
## grid: a cell is 1 when some enemy that will act could move and then reach a
## Normal unit standing there. Line of sight is ignored (an enemy can usually walk
## round what blocks it), so it can only over-warn. Returns {cols, rows, cells}.
static func danger_grid(battle: Battle) -> Dictionary:
	var cols := int(ceil(battle.field.size.x / ReachField.CELL))
	var rows := int(ceil(battle.field.size.y / ReachField.CELL))
	var cells := PackedFloat32Array()
	cells.resize(cols * rows)
	for e in battle.enemy_units():
		if not _may_threaten(battle, e):
			continue
		var r := ReachField.compute(battle.field, e, e.pos, battle.effective_move(e))
		var reach := (e.radius + e.attack_range + Defs.UNIT_RADIUS) / ReachField.CELL
		var d := _distance_from(r, cols, rows)
		for i in cells.size():
			if d[i] <= reach:
				cells[i] = 1.0
	return {"cols": cols, "rows": rows, "cells": cells}


## Distance in cells from every cell to the nearest one `r` can reach (two-pass
## chamfer, 1 and √2).
static func _distance_from(r: ReachField, cols: int, rows: int) -> PackedFloat32Array:
	var d := PackedFloat32Array()
	d.resize(cols * rows)
	for i in d.size():
		d[i] = 0.0 if r.cost[i] <= r.budget else 1.0e9
	const DIAG := 1.41421356
	for y in rows:
		for x in cols:
			var i := y * cols + x
			var v := d[i]
			if x > 0:
				v = minf(v, d[i - 1] + 1.0)
			if y > 0:
				v = minf(v, d[i - cols] + 1.0)
				if x > 0:
					v = minf(v, d[i - cols - 1] + DIAG)
				if x < cols - 1:
					v = minf(v, d[i - cols + 1] + DIAG)
			d[i] = v
	for y in range(rows - 1, -1, -1):
		for x in range(cols - 1, -1, -1):
			var i := y * cols + x
			var v := d[i]
			if x < cols - 1:
				v = minf(v, d[i + 1] + 1.0)
			if y < rows - 1:
				v = minf(v, d[i + cols] + 1.0)
				if x < cols - 1:
					v = minf(v, d[i + cols + 1] + DIAG)
				if x > 0:
					v = minf(v, d[i + cols - 1] + DIAG)
			d[i] = v
	return d


## Whether `e` takes part in the next Enemy Phase's attacks at all.
static func _may_threaten(battle: Battle, e: Unit) -> bool:
	if e.frozen:
		return false
	if battle.gaze_active() and (e.expected_behavior or battle.in_gaze(e)):
		return false
	if e.ai == "captain":
		for tg in battle.telegraphs:
			if tg.owner == e:
				return false # it spends its turn on the Cutting Line
	return true


## The cheapest spot `e` could reach and attack `target` at `p` from, or INF.
static func _attack_spot(battle: Battle, e: Unit, spots: Array, target: Unit, p: Vector2) -> Vector2:
	var reach := e.attack_range + e.radius + target.radius
	for s: Vector2 in spots:
		var d := s.distance_to(p)
		if d > reach + 0.001 or d - e.radius - target.radius < e.min_range - 0.001:
			continue
		if s.distance_to(p) < e.radius + target.radius - 0.001:
			continue
		if battle.field.has_los(s, p):
			return s
	return Vector2.INF
