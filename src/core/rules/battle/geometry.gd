class_name Geometry
extends RefCounted

## Ground-plane geometry for the battle rules. Positions are metres on the floor,
## x to the right and y "up the map" (away from the player's side). Pure functions.


## Whether segment a-b crosses the rectangle (touching an edge counts).
static func segment_hits_rect(a: Vector2, b: Vector2, r: Rect2) -> bool:
	if r.has_point(a) or r.has_point(b):
		return true
	var c := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]
	for i in 4:
		if Geometry2D.segment_intersects_segment(a, b, c[i], c[(i + 1) % 4]) != null:
			return true
	return false


## Distance from point p to segment a-b.
static func point_segment_distance(p: Vector2, a: Vector2, b: Vector2) -> float:
	return p.distance_to(Geometry2D.get_closest_point_to_segment(p, a, b))


## Whether a circle overlaps a rectangle.
static func circle_hits_rect(c: Vector2, radius: float, r: Rect2) -> bool:
	var nearest := Vector2(clampf(c.x, r.position.x, r.end.x), clampf(c.y, r.position.y, r.end.y))
	return c.distance_squared_to(nearest) < radius * radius


## Whether a circle overlaps a strip: the segment a-b widened to `half_width` each side.
static func circle_hits_strip(c: Vector2, radius: float, a: Vector2, b: Vector2, half_width: float) -> bool:
	return point_segment_distance(c, a, b) <= half_width + radius


## Whether a circle touches a cone (apex, unit direction, length, half angle in radians).
static func circle_in_cone(c: Vector2, radius: float, apex: Vector2, dir: Vector2, length: float, half_angle: float) -> bool:
	var to := c - apex
	var d := to.length()
	if d <= radius:
		return true
	if d - radius > length:
		return false
	var slack := asin(clampf(radius / d, 0.0, 1.0))
	return absf(dir.angle_to(to)) <= half_angle + slack


## Edge-to-edge distance between two circles (negative when they overlap).
static func gap(a: Vector2, ra: float, b: Vector2, rb: float) -> float:
	return a.distance_to(b) - ra - rb


## The four corners of a cone's outline for drawing: apex plus an arc of points.
static func cone_outline(apex: Vector2, dir: Vector2, length: float, half_angle: float, steps := 12) -> PackedVector2Array:
	var out := PackedVector2Array([apex])
	for i in steps + 1:
		var a := -half_angle + 2.0 * half_angle * i / steps
		out.append(apex + dir.rotated(a) * length)
	return out
