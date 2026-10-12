class_name ReachAreaTexture
extends RefCounted

## Turns a ReachField (or the enemies' danger grid) into the two smooth masks the
## reach-area shader draws from.
##
## `shape` (R: how far inside the area, 0.5 on its edge; G: furniture, units or
## the map's edge next to it) and `glow` (the same inside value blurred wider, for
## the rim's inward fade). Both cover the field plus PAD metres all round, so the
## outline closes before the edge of the map. Built at the field's cell size,
## blurred there and upscaled smoothly, so the edge follows furniture without
## showing the 25 cm sampling grid.

## Metres of floor added round the field on every side.
const PAD := 1.0
## Upscale from the field's cells to the texture.
const UPSCALE := 4

var shape: ImageTexture
var glow: ImageTexture
## Floor point at the textures' (0, 0) corner, and the floor size they cover.
var origin := Vector2.ZERO
var size := Vector2.ZERO


static func build(r: ReachField) -> ReachAreaTexture:
	var n := r.cols * r.rows
	var inside := PackedFloat32Array()
	inside.resize(n)
	var wall := PackedFloat32Array()
	wall.resize(n)
	for i in n:
		if not r.passable(i):
			wall[i] = 1.0
			continue
		var c := r.cost[i]
		if c >= ReachField.INF:
			continue
		# 0.5 exactly where the path cost reaches the budget, so on open floor
		# the edge sits where the rules put it rather than on a cell boundary.
		inside[i] = clampf((r.budget - c) / ReachField.CELL * 0.5 + 0.5, 0.0, 1.0)
	return from_grid(inside, wall, r.cols, r.rows, true)


## The same masks from any grid on the ReachField's cells: `inside` 0..1 (0.5 on
## the edge), `wall` 1 where something solid stops it. The map's edge counts as a
## wall when `edge_is_wall`.
static func from_grid(cells: PackedFloat32Array, walls: PackedFloat32Array, cols: int, rows: int, edge_is_wall: bool) -> ReachAreaTexture:
	var t := ReachAreaTexture.new()
	var pad := int(round(PAD / ReachField.CELL))
	var w := cols + pad * 2
	var h := rows + pad * 2
	var inside := PackedFloat32Array()
	inside.resize(w * h)
	var wall := PackedFloat32Array()
	wall.resize(w * h)
	wall.fill(1.0 if edge_is_wall else 0.0)
	for cy in rows:
		for cx in cols:
			var i := cy * cols + cx
			var k := (cy + pad) * w + cx + pad
			inside[k] = cells[i]
			wall[k] = walls[i]
	inside = _blur(inside, w, h)
	wall = _blur(wall, w, h)
	var wide := _blur(_blur(_blur(inside, w, h), w, h), w, h)
	var img := Image.create(w, h, false, Image.FORMAT_RGB8)
	var gimg := Image.create(w, h, false, Image.FORMAT_L8)
	for y in h:
		for x in w:
			var k := y * w + x
			img.set_pixel(x, y, Color(inside[k], wall[k], 0.0))
			gimg.set_pixel(x, y, Color(wide[k], wide[k], wide[k]))
	img.resize(w * UPSCALE, h * UPSCALE, Image.INTERPOLATE_CUBIC)
	gimg.resize(w * UPSCALE, h * UPSCALE, Image.INTERPOLATE_CUBIC)
	t.shape = ImageTexture.create_from_image(img)
	t.glow = ImageTexture.create_from_image(gimg)
	t.origin = -Vector2.ONE * pad * ReachField.CELL
	t.size = Vector2(w, h) * ReachField.CELL
	return t


## One pass of a 3x3 tent blur (1 2 1), edges clamped.
static func _blur(src: PackedFloat32Array, w: int, h: int) -> PackedFloat32Array:
	var tmp := PackedFloat32Array()
	tmp.resize(w * h)
	for y in h:
		for x in w:
			var l := src[y * w + maxi(x - 1, 0)]
			var rr := src[y * w + mini(x + 1, w - 1)]
			tmp[y * w + x] = (l + src[y * w + x] * 2.0 + rr) * 0.25
	var out := PackedFloat32Array()
	out.resize(w * h)
	for y in h:
		for x in w:
			var u := tmp[maxi(y - 1, 0) * w + x]
			var d := tmp[mini(y + 1, h - 1) * w + x]
			out[y * w + x] = (u + tmp[y * w + x] * 2.0 + d) * 0.25
	return out
