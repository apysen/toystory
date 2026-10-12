class_name Arts
extends RefCounted
## Art and item definitions for the slice squad (character_abilities_stats.md).
## Signature Arts are paralogue unlocks ("signature": true); Lamp's Spotlight,
## Stapler's Staple Storm, Toaster's Overheat and Teacup's Tea Break are in the
## slice so they can be played and tested.
##
## Reach is the edge-to-edge gap in metres between the user and the target
## ("min" and "max"). The interface draws it as a ring around the user.
##
## target kinds:
##   "enemy"     pick a hostile unit (or destructible cover for attacks) within reach
##   "ally"      pick a friendly unit within reach ("self": true allows the user)
##   "self"      no pick; with a "radius" it covers the circle round the user, shown
##               before it is confirmed (enemies in it with "might", allies without)
##   "direction" aim a cone in any direction ("length" past the user's edge)
##   "area"      place a circle ("radius") whose centre is within "max" of the user's edge
##   "lunge"     pick a hostile unit along a clear straight dash of up to "dash" metres

## Cone half-angle shared by Flashbulb, Flash Bake and Blowback.
const CONE_HALF_ANGLE := deg_to_rad(40.0)

const DATA := {
	"guard_beam": {"name": "Guard Beam", "noise": 1, "target": "ally", "min": 0.0, "max": 2.6, "self": false,
		"desc": "Next hit on the ally before your next phase deals 50% less damage and can't displace them."},
	"spotlight": {"name": "Spotlight", "noise": 2, "target": "area", "min": 0.0, "max": 2.6, "radius": 1.6, "signature": true,
		"desc": "Allies in the light gain +20 Evasion and can't be moved by force until your next phase."},
	"flashbulb": {"name": "Flashbulb", "noise": 1, "target": "direction", "length": 1.8, "might": 2, "type": Defs.DmgType.SMASH,
		"desc": "Short cone. Light Smash damage and Dazzle (-20 Hit on next attack)."},
	"staple_storm": {"name": "Staple Storm", "noise": 3, "target": "self", "radius": 2.0, "might": 4,
		"type": Defs.DmgType.PIERCE, "signature": true,
		"desc": "Leap, spin and fire all round: Pierce damage to every enemy within 2 m, and Pins each one hit."},
	"pin": {"name": "Pin", "noise": 1, "target": "enemy", "min": 0.0, "max": 1.6, "might": 4, "type": Defs.DmgType.PIERCE,
		"desc": "Pierce attack. On hit, the target can't move next Enemy Phase."},
	"staple_burst": {"name": "Staple Burst", "noise": 2, "target": "enemy", "min": 0.0, "max": 1.6, "might": 2, "type": Defs.DmgType.PIERCE,
		"desc": "Two reduced-Might attacks. The second picks another target if the first falls."},
	"eject": {"name": "Eject", "noise": 1, "target": "enemy", "min": 0.0, "max": 1.6, "might": 5, "type": Defs.DmgType.SMASH,
		"desc": "Smash attack. On hit, push the target 2 m."},
	"flash_bake": {"name": "Flash Bake", "noise": 2, "target": "direction", "length": 1.8, "might": 6, "type": Defs.DmgType.SMASH,
		"desc": "Short cone. High Smash damage to everything in it."},
	"overheat": {"name": "Overheat", "noise": 3, "target": "self", "radius": 1.6, "might": 7, "type": Defs.DmgType.SMASH,
		"signature": true,
		"desc": "Erupt: very high Smash damage to every enemy within 1.6 m. Burns off 20% of Toaster's max HP."},
	"warm_pour": {"name": "Warm Pour", "noise": 1, "target": "ally", "min": 0.0, "max": 2.6, "self": true,
		"desc": "Restore 30% of the ally's max HP."},
	"steady_sip": {"name": "Steady Sip", "noise": 0, "target": "ally", "min": 0.0, "max": 1.6, "self": true,
		"desc": "Remove one negative status and grant +2 Defense until your next phase."},
	"tea_break": {"name": "Tea Break", "noise": 2, "target": "self", "radius": 1.6, "signature": true,
		"desc": "Every ally within 1.6 m (Teacup too) restores 20% of max HP and loses one negative status."},
	"suction": {"name": "Suction", "noise": 1, "target": "enemy", "min": 0.9, "max": 3.6,
		"desc": "Pull a normal-sized enemy up to 3 m toward Vacuum. Always succeeds."},
	"blowback": {"name": "Blowback", "noise": 1, "target": "direction", "length": 1.8,
		"desc": "Cone. Push everything in it 2 m. Always succeeds."},
	"lunge": {"name": "Lunge", "noise": 1, "target": "lunge", "dash": 3.0, "might": 6, "type": Defs.DmgType.PIERCE,
		"desc": "Dash up to 3 m in a straight line and attack."},
	"canopy": {"name": "Canopy", "noise": 0, "target": "self",
		"desc": "Allies right next to Umbrella count as in Half Cover against ranged attacks until your next phase."},
}

const ITEMS := {
	"repair_tape": {"name": "Repair Tape", "heal_pct": 0.4, "desc": "Restore 40% of max HP. Uses the Action."},
}


static func get_art(id: String) -> Dictionary:
	return DATA[id]


static func noise_of(id: String) -> int:
	return DATA[id].noise
