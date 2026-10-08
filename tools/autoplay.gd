extends SceneTree
## Greedy bot that plays the slice many times to sanity-check balance:
## godot --headless --path . --script res://tools/autoplay.gd -- [runs]
## It is deliberately simple; real tuning needs human playtests.

func _init() -> void:
	var runs := 30
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		runs = int(args[0])
	var wins := 0
	var turns_total := 0
	var broken_total := 0
	var recruits := 0
	var gazes := 0
	for s in range(1, runs + 1):
		var b := Battle.new(UnderTheDesk.build_board(), s)
		b.start()
		while b.phase == Defs.Phase.PLAYER and b.turn <= 20:
			for u in b.player_units():
				if b.phase != Defs.Phase.PLAYER:
					break
				if u.can_activate():
					_play_unit(b, u)
			if b.phase == Defs.Phase.PLAYER:
				b.end_player_phase()
			b.take_events()
		if b.phase == Defs.Phase.VICTORY:
			wins += 1
			turns_total += b.turn
		for u in b.board.units:
			if u.faction == Defs.Faction.PLAYER and u.broken:
				broken_total += 1
		if b.recruited:
			recruits += 1
		gazes += b.stats.gaze_triggers
	print("runs %d  wins %d  avg win turns %.1f  broken/run %.2f  recruited %d  gazes/run %.2f" % [
		runs, wins, float(turns_total) / maxi(wins, 1), float(broken_total) / runs, recruits, float(gazes) / runs])
	quit()


func _play_unit(b: Battle, u: Unit) -> void:
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
		u.pos = saved
		for o in options:
			if o.score > best_score:
				best_score = o.score
				best = o.duplicate()
				best["anchor"] = a
	if best.is_empty():
		b.wait(u)
		return
	if best.anchor != u.pos:
		b.commit_move(u, best.anchor)
	match best.kind:
		"attack":
			b.attack(u, best.target)
		"talk":
			b.talk(u, best.target)
		"art":
			if not b.use_art(u, best.art, best.target):
				b.wait(u)
		_:
			b.wait(u)
