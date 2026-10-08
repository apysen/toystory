class_name Combat
extends RefCounted
## Damage, Hit and Crit (gameplay_design.md sections 8-11). Pure functions.


## spec keys: might, type, accuracy (default BASE_ACCURACY), auto_hit, no_crit,
## dmg_mult (extra multiplier, e.g. Opportunist), power_bonus, crit_bonus
static func preview(field: Field, attacker: Unit, att_pos: Vector2, defender: Unit, def_pos: Vector2, spec: Dictionary) -> Dictionary:
	var gap := Geometry.gap(att_pos, attacker.radius, def_pos, defender.radius)
	var ranged := gap > Defs.MELEE_REACH
	var rel := Defs.type_relation(spec.get("type", attacker.dmg_type), defender.dmg_type)

	var power := attacker.power + int(spec.get("power_bonus", 0))
	var defense := defender.defense + (2 if defender.status.has("steady_sip") else 0)
	var base := float(power + int(spec.get("might", attacker.might)) - defense)
	var mult := 1.0 + rel * Defs.TYPE_DMG_BONUS
	mult *= float(spec.get("dmg_mult", 1.0))
	if defender.status.has("guard_beam"):
		mult *= 0.5
	var dmg := maxi(int(round(base * mult)), 1)

	var cover := false
	var evade := 0
	if ranged:
		cover = field.has_half_cover(defender, def_pos, att_pos) or defender.status.has("canopy")
		if cover:
			evade += Defs.HALF_COVER_EVASION
		elif defender.id == "umbrella":
			evade += Defs.WEATHERPROOF_EVASION # Weatherproof
	var hit := int(spec.get("accuracy", Defs.BASE_ACCURACY)) + attacker.skill * 2 - defender.speed * 2
	hit += rel * Defs.TYPE_HIT_BONUS - evade
	if attacker.status.has("dazzled"):
		hit -= 20
	hit = clampi(hit, 0, 100)
	var crit := 0 if spec.get("no_crit", false) else clampi(attacker.skill + int(spec.get("crit_bonus", 0)), 0, 100)
	if spec.get("auto_hit", false):
		hit = 100
	var expected := hit / 100.0 * (dmg * (1.0 - crit / 100.0) + dmg * Defs.CRIT_MULT * crit / 100.0)
	return {
		"damage": dmg, "hit": hit, "crit": crit, "type_rel": rel, "cover": cover,
		"ranged": ranged, "expected": expected,
	}


## Whether `defender` is within the edge-to-edge reach [min_r, max_r] of `attacker`.
static func in_range(attacker: Unit, att_pos: Vector2, defender: Unit, def_pos: Vector2, min_r: float, max_r: float) -> bool:
	var g := Geometry.gap(att_pos, attacker.radius, def_pos, defender.radius)
	return g >= min_r - 0.001 and g <= max_r + 0.001


static func collision_damage(u: Unit) -> int:
	return ceili(u.max_hp * Defs.COLLISION_PCT)
