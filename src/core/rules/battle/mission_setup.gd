class_name MissionSetup
extends RefCounted

## Turns an authored mission and roster into the starting `Field`. The mission is
## laid out on a 1 m grid (tile (1, 1) is the square from (0, 0) to (1, 1)); each
## piece of furniture takes the footprint its kind is given there. Pure: no scene
## access, so tests and tools build the same field the battle scene does.


static func build_field(mission: MissionDefinition, roster: Array[Dictionary]) -> Field:
	var f := Field.new(Vector2(mission.map_size))
	var done := {}
	for t: Vector2i in mission.full_cover:
		var kind: String = mission.full_cover[t]
		if mission.merged_kinds.has(kind):
			if done.has(kind):
				continue
			done[kind] = true
			f.add_object(kind, kind, Defs.Cover.FULL, _merged_rect(mission.full_cover, kind, mission.footprint(kind)))
		else:
			f.add_object("%s_%d_%d" % [kind, t.x, t.y], kind, Defs.Cover.FULL, tile_rect(t, mission.footprint(kind)))
	for t: Vector2i in mission.half_cover:
		var kind: String = mission.half_cover[t]
		f.add_object("%s_%d_%d" % [kind, t.x, t.y], kind, Defs.Cover.HALF, tile_rect(t, mission.footprint(kind)),
			mission.cover_durability.get(kind, 0))
	for t in mission.spill_tiles:
		f.add_slow_rect("spill", tile_rect(t, Vector2.ONE))
	for def in roster:
		f.units.append(Unit.from_def(def, start_position(def)))
	return f


## Centre of a tile on the layout grid.
static func tile_center(t: Vector2i) -> Vector2:
	return Vector2(t.x - 0.5, t.y - 0.5)


## A footprint of `size` metres centred in a tile.
static func tile_rect(t: Vector2i, size: Vector2) -> Rect2:
	return Rect2(tile_center(t) - size * 0.5, size)


## Where a profile starts: the centre of its footprint, whose bottom-left tile is
## its start tile.
static func start_position(def: Dictionary) -> Vector2:
	var tiles: int = def.get("size", 1)
	var bl: Vector2i = def.start_tile
	return Vector2(bl.x - 1, bl.y - 1) + Vector2.ONE * tiles * 0.5


## The block covering every tile of `kind`, shrunk to `footprint` of each tile's margin.
static func _merged_rect(tiles: Dictionary, kind: String, footprint: Vector2) -> Rect2:
	var r := Rect2()
	var first := true
	for t: Vector2i in tiles:
		if tiles[t] != kind:
			continue
		var tr := Rect2(Vector2(t.x - 1, t.y - 1), Vector2.ONE)
		r = tr if first else r.merge(tr)
		first = false
	var margin := (Vector2.ONE - footprint) * 0.5
	return r.grow_individual(-margin.x, -margin.y, -margin.x, -margin.y)
