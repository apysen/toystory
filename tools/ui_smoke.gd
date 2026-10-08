extends SceneTree
## Drives the real battle screen through a whole battle with SliceBot to catch
## playback errors: godot --path . --script res://tools/ui_smoke.gd -- [seed]

func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var seed_value := 3
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		seed_value = int(args[0])
	root.size = Vector2i(1600, 900)
	var view := BattleView.new()
	root.add_child(view)
	var done := [false]
	view.battle_finished.connect(func(r): done[0] = true; print("finished victory=", r.victory, " turns=", r.turns, " metrics=", r.metrics))
	_skip_dialogue(view)
	await view.start(seed_value, SliceDialogue.PRE_BATTLE.slice(0, 1))
	var b := view.battle
	var guard := 0
	while not done[0] and guard < 400:
		guard += 1
		if view.mode == BattleView.Mode.BUSY:
			await process_frame
			continue
		if view._dialogue.visible:
			view._dialogue._advance()
			await process_frame
			continue
		var acted := false
		for u in b.player_units():
			if not u.can_activate():
				continue
			var plan := SliceBot.choose(b, u)
			view.select(u)
			await view._move_to(plan.get("anchor", u.pos))
			match plan.get("kind", "wait"):
				"attack":
					view.on_action("attack")
					await view._execute_target(plan.target)
				"talk":
					view.on_action("talk")
					await view._execute_target(plan.target)
				"art":
					view.on_action("art:" + plan.art)
					await view._execute_target(plan.target)
				_:
					await view.on_action("wait")
			acted = true
			break
		if not acted and not done[0]:
			await view.end_turn()
	print("loop guard=", guard)
	print("smoke done, finished=", done[0], " turn=", b.turn)
	quit()


func _skip_dialogue(view: BattleView) -> void:
	# Auto-advance conversation lines while the talk plays.
	var t := Timer.new()
	t.wait_time = 0.05
	t.autostart = true
	t.timeout.connect(func(): if view._dialogue.visible: view._dialogue._advance())
	root.add_child(t)
