class_name SliceBot
extends RefCounted
## Greedy decision-maker used by tools/autoplay.gd and tests/integration/ui_smoke.gd.


static func choose(b: Battle, u: Unit) -> Dictionary:
	var best_score := -INF
	var best := {}
	var umb := b.board.find_unit("umbrella")
	var cutter := b.board.find_unit("cutter")
	for a in b.move_options(u):
		var saved := u.pos
		u.pos = a
		var fc := Forecast.for_destination(b, u, a)
		var danger: float = fc.expected * (2.0 if fc.risk == "Broken Risk" else 1.0)
		var base := -danger * 0.8
		# Advance toward the Captain.
		base -= u.distance_to_unit(a, cutter, cutter.pos) * 0.6
		var options: Array = [{"kind": "wait", "score": base}]
		for t in b.basic_targets(u, a):
			var pv := Combat.preview(b.board, u, a, t, t.pos, {"might": u.might, "type": u.dmg_type})
			var sc: float = base + pv.expected * 1.5 + (12.0 if pv.damage >= t.hp else 0.0) + (8.0 if t == cutter else 0.0)
			options.append({"kind": "attack", "target": t, "score": sc})
		if u.id == "lamp" and umb.faction == Defs.Faction.NEUTRAL and not umb.broken:
			if u.distance_to_unit(a, umb, umb.pos) == 1:
				options.append({"kind": "talk", "target": umb, "score": base + 30.0})
			else:
				options[0].score -= u.distance_to_unit(a, umb, umb.pos) * 1.5
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
				if t is Vector2i:
					for o in b.units_in_tiles(b.cone_for(u, t)):
						if b.can_target(u, o):
							gain += Combat.preview(b.board, u, a, o, o.pos, {"might": art.might, "type": art.type}).expected * 1.5
				elif t is Unit:
					gain = Combat.preview(b.board, u, a, t, t.pos, {"might": art.might, "type": art.type}).expected * 1.5
				options.append({"kind": "art", "art": art_id, "target": t, "score": base + gain - art.noise * 2.0})
		u.pos = saved
		for o in options:
			if o.score > best_score:
				best_score = o.score
				best = o.duplicate()
				best["anchor"] = a
	return best
