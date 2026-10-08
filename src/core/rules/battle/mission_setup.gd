class_name MissionSetup
extends RefCounted

## Turns an authored mission and roster into the starting `Board`. Pure: no scene
## access, so tests and tools build the same board the battle scene does.


static func build_board(mission: MissionDefinition, roster: Array[Dictionary]) -> Board:
	var b := Board.new(mission.map_size.x, mission.map_size.y)
	for t in mission.full_cover:
		b.add_object(t, mission.full_cover[t], Defs.Terrain.FULL_COVER)
	for t in mission.half_cover:
		var kind: String = mission.half_cover[t]
		b.add_object(t, kind, Defs.Terrain.HALF_COVER, mission.cover_durability.get(kind, 0))
	for t in mission.spill_tiles:
		b.slow_tiles[t] = "spill"
	for def in roster:
		b.units.append(Unit.from_def(def))
	return b
