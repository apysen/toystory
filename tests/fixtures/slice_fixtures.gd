class_name SliceFixtures
extends RefCounted

## Builds the "Under the Desk" starting board from the same authored mission and
## roster the battle scene uses, so tests and tools never keep a copy of the data.

const MISSION_PATH := "res://data/missions/under_the_desk.tres"
const ROSTER_SCENE_PATH := "res://scenes/units/unit_profiles.tscn"


static func mission() -> MissionDefinition:
	return load(MISSION_PATH)


static func roster() -> Array[Dictionary]:
	var profiles: UnitProfiles = load(ROSTER_SCENE_PATH).instantiate()
	var defs := profiles.definitions()
	profiles.free()
	return defs


static func board() -> Board:
	return MissionSetup.build_board(mission(), roster())


static func battle(seed_value := 1) -> Battle:
	return Battle.new(board(), seed_value)
