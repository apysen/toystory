extends SceneTree
## Drives the real battle scene through a whole battle with SliceBot, using the
## same steps a player takes (take control, walk, open the ring, choose, target,
## confirm), to catch playback and interface errors:
## godot --path . --script res://tests/integration/ui_smoke.gd -- [seed]

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"
const Mode := BattleSelection.Mode


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
	while not done[0] and guard < 300:
		guard += 1
		if view.selection.mode != Mode.IDLE:
			await process_frame
			continue
		var acted := false
		for u in b.player_units():
			if not u.can_activate():
				continue
			await _play_unit(view, u)
			acted = true
			break
		if not acted and not done[0]:
			await view.end_turn()
	while not done[0]:
		await process_frame
	print("loop guard=", guard)
	print("SMOKE: %s (turn %d)" % ["PASS" if done[0] else "FAIL", b.turn])
	quit(0 if done[0] else 1)


func _play_unit(view: BattleRoot, u: Unit) -> void:
	var b := view.battle
	var plan := SliceBot.choose(b, u)
	view.control(u)
	# Walk there the way the controller does: small steps inside the area.
	var path := b.reach(u).path_to(plan.get("spot", u.pos))
	for k in range(1, path.size()):
		var from := u.pos
		var steps := maxi(int(ceil(from.distance_to(path[k]) / 0.25)), 1)
		for i in steps:
			var to := from.lerp(path[k], float(i + 1) / steps)
			if b.move_unit(u, to):
				view.card_of(u).position = BattleSpace.to_world(to)
	await process_frame
	view.open_menu()
	match plan.get("kind", "wait"):
		"attack":
			view.choose_action("attack")
			_pick(view, plan.target)
			await view.execute()
		"talk":
			view.choose_action("talk")
			_pick(view, plan.target)
			await view.execute()
		"art":
			view.choose_action("art:" + plan.art)
			if view.selection.mode == Mode.TARGET:
				_pick(view, plan.target)
				await view.execute()
		_:
			await view.choose_action("wait")
	while view.selection.mode == Mode.BUSY:
		await process_frame


func _pick(view: BattleRoot, target: Variant) -> void:
	if target is Vector2:
		view.selection.aim = target
	else:
		view.selection.target_index = maxi(view.selection.targets.find(target), 0)


func _skip_dialogue(view: BattleRoot) -> void:
	# Auto-advance conversation lines while a talk plays.
	var t := Timer.new()
	t.wait_time = 0.05
	t.autostart = true
	t.timeout.connect(func(): if view.dialogue.is_playing(): view.dialogue.advance())
	root.add_child(t)
