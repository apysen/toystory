class_name UnitProfiles
extends Node

## The authored mission roster: one `UnitProfile` child per combatant, player,
## neutral and enemy alike.
##
## It is a container, not a system. The battle root reads the definitions once when
## a battle starts and nothing here runs per frame. The roster lives in its own scene
## so tuning the squad and the opposition is one file to open. Add a combatant by
## adding a child here.


## Every profile's definition, in child order.
func definitions() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for child in get_children():
		var profile := child as UnitProfile
		if profile != null:
			out.append(profile.to_def())
	return out


## Definitions of one faction only (the team preview shows the player squad).
func definitions_of(faction: Defs.Faction) -> Array[Dictionary]:
	return definitions().filter(func(d: Dictionary) -> bool: return d.faction == faction)
