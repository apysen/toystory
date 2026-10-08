class_name SliceBot
extends RefCounted
## Greedy decision-maker used by tools/autoplay.gd and tests/integration/ui_smoke.gd.
## Considers standing spots about half a metre apart across the unit's movement area.

const SPOT_SPACING := 0.5


## {spot, kind: "wait" | "attack" | "talk" | "art", target, art}
static func choose(b: Battle, u: Unit) -> Dictionary:
	var best_score := -INF
	var best := {}
	var umb := b.field.find_unit("umbrella")
	var cutter := b.field.find_unit("cutter")
	var map := Forecast.ThreatMap.new(b, u)
	var saved := u.pos
	for a in b.reach(u).standing_spots(SPOT_SPACING):
		u.pos = a
		var fc := Forecast.for_destination(b, u, a, map)
		var danger: float = fc.expected * (2.0 if fc.risk == "Broken Risk" else 1.0)
		var base := -danger * 0.8
		# Advance toward the Captain.
		base -= u.gap_to(cutter) * 0.6
		var options: Array = [{"kind": "wait", "score": base}]
		for t in b.basic_targets(u):
			var pv := Combat.preview(b.field, u, a, t, t.pos, {"might": u.might, "type": u.dmg_type})
			var sc: float = base + pv.expected * 1.5 + (12.0 if pv.damage >= t.hp else 0.0) + (8.0 if t == cutter else 0.0)
			options.append({"kind": "attack", "target": t, "score": sc})
		if u.id == "lamp" and umb.faction == Defs.Faction.NEUTRAL and not umb.broken:
			if b.talk_targets(u).has(umb):
				options.append({"kind": "talk", "target": umb, "score": base + 30.0})
			else:
				options[0].score -= u.gap_to(umb) * 1.5
		if u.id == "teacup" and not b.gaze_active():
			for o in b.art_targets(u, "warm_pour"):
				if o.hp < o.max_hp * 0.6:
					options.append({"kind": "art", "art": "warm_pour", "target": o, "score": base + 15.0})
		# Damaging Arts: worth it when they beat a Basic Attack by enough to pay the Noise.
		for art_id in u.arts:
			var art := Arts.get_art(art_id)
			if not art.has("might") or not b.art_check(u, art_id).ok:
				continue
			for t in b.art_targets(u, art_id):
				var gain := 0.0
				if t is Vector2:
					for o in b.units_in_cone(u, b.cone_for(u, art_id, t)):
						if b.can_target(u, o):
							gain += Combat.preview(b.field, u, a, o, o.pos, {"might": art.might, "type": art.type}).expected * 1.5
				elif t is Unit:
					gain = Combat.preview(b.field, u, a, t, t.pos, {"might": art.might, "type": art.type}).expected * 1.5
				options.append({"kind": "art", "art": art_id, "target": t, "score": base + gain - art.noise * 2.0})
		for o in options:
			if o.score > best_score:
				best_score = o.score
				best = o.duplicate()
				best["spot"] = a
	u.pos = saved
	return best
