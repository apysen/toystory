class_name BattleSpace
extends RefCounted

## Maps the rules' floor (metres, x right, y up the map) into the 3D world (x right,
## z toward the camera's home side, y up). The map's bottom-left corner is the
## world origin and "up the map" runs along -z.

## Sprite pixels per metre: a 128px character frame is one metre across.
const PIXELS_PER_METRE := 128.0


static func to_world(p: Vector2, height := 0.0) -> Vector3:
	return Vector3(p.x, height, -p.y)


static func to_floor(w: Vector3) -> Vector2:
	return Vector2(w.x, -w.z)


## A floor direction as a world direction.
static func dir_to_world(d: Vector2) -> Vector3:
	return Vector3(d.x, 0.0, -d.y)


static func rect_center_world(r: Rect2, height := 0.0) -> Vector3:
	return to_world(r.get_center(), height)
