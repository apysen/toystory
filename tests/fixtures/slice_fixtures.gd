class_name SliceFixtures
extends RefCounted

## Builds the "Under the Desk" starting field from the same authored mission and
## roster the battle scene uses, so tests and tools never keep a copy of the data.

const MISSION_PATH := "res://data/missions/under_the_desk.tres"
const ROSTER_SCENE_PATH := "res://scenes/units/unit_profiles.tscn"


static func mission() -> MissionDefinition:
	return load(MISSION_PATH)


## The roster as the real slice has it: dev switches (a neutral put straight into the
## squad for testing, `UnitProfile.dev_in_squad`) are left off.
static func roster() -> Array[Dictionary]:
	var profiles: UnitProfiles = load(ROSTER_SCENE_PATH).instantiate()
	for p in profiles.get_children():
		if p is UnitProfile:
			(p as UnitProfile).dev_in_squad = false
	var defs := profiles.definitions()
	profiles.free()
	return defs


static func field() -> Field:
	return MissionSetup.build_field(mission(), roster())


static func battle(seed_value := 1) -> Battle:
	return Battle.new(field(), seed_value)
