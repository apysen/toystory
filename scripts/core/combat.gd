class_name Combat
extends RefCounted
## Damage, Hit and Crit (gameplay_design.md sections 8-11). Pure functions.


## spec keys: might, type, accuracy (default BASE_ACCURACY), auto_hit, no_crit,
## dmg_mult (extra multiplier, e.g. Opportunist), power_bonus
static func preview(board: Board, attacker: Unit, att_anchor: Vector2i, defender: Unit, def_anchor: Vector2i, spec: Dictionary) -> Dictionary:
	var dist := attacker.distance_to_unit(att_anchor, defender, def_anchor)
	var ranged := dist >= 2
	var rel := Defs.type_relation(spec.get("type", attacker.dmg_type), defender.dmg_type)

	var power := attacker.power + int(spec.get("power_bonus", 0))
	var defense := defender.defense + (2 if defender.status.has("steady_sip") else 0)
	var base := float(power + int(spec.get("might", attacker.might)) - defense)
	var mult := 1.0 + rel * Defs.TYPE_DMG_BONUS
	mult *= float(spec.get("dmg_mult", 1.0))
	if defender.status.has("guard_beam"):
		mult *= 0.5
	var dmg := int(round(base * mult))
	dmg = maxi(dmg, 1)

	var cover := false
	var evade := 0
	if ranged:
		var att_tile := _nearest_tile(attacker, att_anchor, def_anchor)
		cover = board.has_half_cover(defender, def_anchor, att_tile) or defender.status.has("canopy")
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


static func _nearest_tile(u: Unit, anchor: Vector2i, target: Vector2i) -> Vector2i:
	var best := anchor
	var bd := 1 << 30
	for t in u.tiles_at(anchor):
		var d := Defs.manhattan(t, target)
		if d < bd:
			bd = d
			best = t
	return best


static func in_range(attacker: Unit, att_anchor: Vector2i, defender: Unit, def_anchor: Vector2i, min_r: int, max_r: int) -> bool:
	var d := attacker.distance_to_unit(att_anchor, defender, def_anchor)
	return d >= min_r and d <= max_r


static func collision_damage(u: Unit) -> int:
	return ceili(u.max_hp * Defs.COLLISION_PCT)
