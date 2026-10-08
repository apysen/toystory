extends SceneTree
## Drives the real battle scene through a whole battle with SliceBot to catch
## playback errors: godot --path . --script res://tests/integration/ui_smoke.gd -- [seed]

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var seed_value := 3
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		seed_value = int(args[0])
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	var done := [false]
	view.battle_finished.connect(func(r): done[0] = true; print("finished victory=", r.victory, " turns=", r.turns, " metrics=", r.metrics))
	_skip_dialogue(view)
	await view.start(seed_value, SliceDialogue.PRE_BATTLE.slice(0, 1))
	var b := view.battle
	var guard := 0
	while not done[0] and guard < 400:
		guard += 1
		if view.selection.mode == BattleSelection.Mode.BUSY or view.selection.mode == BattleSelection.Mode.DONE:
			await process_frame
			continue
		var acted := false
		for u in b.player_units():
			if not u.can_activate():
				continue
			var plan := SliceBot.choose(b, u)
			view.select(u)
			await view.move_to(plan.get("anchor", u.pos))
			match plan.get("kind", "wait"):
				"attack":
					view.on_action("attack")
					await view.execute_target(plan.target)
				"talk":
					view.on_action("talk")
					await view.execute_target(plan.target)
				"art":
					view.on_action("art:" + plan.art)
					await view.execute_target(plan.target)
				_:
					await view.on_action("wait")
			acted = true
			break
		if not acted and not done[0]:
			await view.end_turn()
	while not done[0]:
		await process_frame
	print("loop guard=", guard)
	print("SMOKE: %s (turn %d)" % ["PASS" if done[0] else "FAIL", b.turn])
	quit(0 if done[0] else 1)


func _skip_dialogue(view: BattleRoot) -> void:
	# Auto-advance conversation lines while a talk plays.
	var t := Timer.new()
	t.wait_time = 0.05
	t.autostart = true
	t.timeout.connect(func(): if view.dialogue.is_playing(): view.dialogue.advance())
	root.add_child(t)
