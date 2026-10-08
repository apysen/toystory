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
		var b := SliceFixtures.battle(s)
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
	var best := SliceBot.choose(b, u)
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
