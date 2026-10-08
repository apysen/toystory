class_name Field
extends RefCounted
## The battlefield floor: its bounds, the furniture standing on it, the slow
## patches, and the units. Answers where a body fits, line of sight and cover.
## Pure logic, no nodes. Distances are metres; (0, 0) is the bottom-left corner.

var size: Vector2
## id -> {id, kind, cover: Defs.Cover, rect: Rect2, hp, max_hp, destructible}
var objects := {}
## Slow patches: [{kind: "spill" | "tape", rect: Rect2} or {kind, center, radius}]
var slow_zones: Array = []
var units: Array[Unit] = []


func _init(map_size: Vector2) -> void:
	size = map_size


func bounds() -> Rect2:
	return Rect2(Vector2.ZERO, size)


func add_object(id: String, kind: String, cover: int, rect: Rect2, hp := 0) -> void:
	objects[id] = {"id": id, "kind": kind, "cover": cover, "rect": rect, "hp": hp, "max_hp": hp, "destructible": hp > 0}


func add_slow_rect(kind: String, rect: Rect2) -> void:
	slow_zones.append({"kind": kind, "rect": rect})


func add_slow_circle(kind: String, center: Vector2, radius: float) -> void:
	slow_zones.append({"kind": kind, "center": center, "radius": radius})


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


## The living unit whose body covers `p`, if any.
func unit_at(p: Vector2) -> Unit:
	for u in units:
		if not u.broken and u.pos.distance_to(p) <= u.radius:
			return u
	return null


func is_slow(p: Vector2) -> bool:
	for z in slow_zones:
		if z.has("rect"):
			if z.rect.has_point(p):
				return true
		elif p.distance_to(z.center) <= z.radius:
			return true
	return false


func cost_multiplier(p: Vector2) -> float:
	return Defs.SLOW_COST_MULT if is_slow(p) else 1.0


## Whether a body of `radius` centred on `p` overlaps furniture or leaves the map.
func blocked_by_terrain(p: Vector2, radius: float) -> bool:
	if p.x < radius or p.y < radius or p.x > size.x - radius or p.y > size.y - radius:
		return true
	for o in objects.values():
		if Geometry.circle_hits_rect(p, radius, o.rect):
			return true
	return false


## Whether `unit` could stand with its centre at `p`, ignoring itself.
func can_stand(unit: Unit, p: Vector2) -> bool:
	if blocked_by_terrain(p, unit.radius):
		return false
	for o in units:
		if o != unit and not o.broken and p.distance_to(o.pos) < unit.radius + o.radius - 0.001:
			return false
	return true


## Whether `unit` may pass through `p` on its way somewhere. Allies can be walked
## past; enemies, neutrals and anything frozen by a Gaze cannot.
func can_pass(unit: Unit, p: Vector2) -> bool:
	if blocked_by_terrain(p, unit.radius):
		return false
	for o in units:
		if o == unit or o.broken:
			continue
		if (o.frozen or o.faction != unit.faction) and p.distance_to(o.pos) < unit.radius + o.radius - 0.001:
			return false
	return true


## Line of sight: blocked when the line between two points crosses full cover.
func has_los(a: Vector2, b: Vector2) -> bool:
	for o in objects.values():
		if o.cover == Defs.Cover.FULL and Geometry.segment_hits_rect(a, b, o.rect):
			return false
	return true


## Half cover protects a ranged target when a half-cover object stands close to the
## target, between it and the shot. Large units are too big to hide behind it.
func has_half_cover(defender: Unit, def_pos: Vector2, from: Vector2) -> bool:
	if defender.is_large():
		return false
	var toward := (from - def_pos).normalized()
	var near := def_pos + toward * Defs.COVER_REACH
	for o in objects.values():
		if o.cover != Defs.Cover.HALF:
			continue
		if Geometry.segment_hits_rect(def_pos, near, o.rect) and Geometry.segment_hits_rect(def_pos, from, o.rect):
			return true
	return false


## Deals damage to destructible cover. Returns true when it breaks.
func damage_object(id: String, amount: int) -> bool:
	if not objects.has(id) or not objects[id].destructible:
		return false
	objects[id].hp -= amount
	if objects[id].hp <= 0:
		objects.erase(id)
		return true
	return false


func is_destructible(id: String) -> bool:
	return objects.has(id) and objects[id].destructible
