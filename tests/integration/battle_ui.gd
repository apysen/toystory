extends SceneTree
## The battle interface's reading aids and feel, in the real battle scene: the
## movement area's masks, gold rings under what a unit can hit from here, cover
## shields, type matchups, the danger zone, Attack listing only what is in reach,
## hit-stop and the strike close-up, and a signature Art's letterbox.
## godot --headless --path . --script res://tests/integration/battle_ui.gd

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"
const Mode := BattleSelection.Mode

var failures := 0


func _init() -> void:
	_run.call_deferred()


func check(cond: bool, msg: String) -> void:
	if cond:
		print("PASS: " + msg)
	else:
		failures += 1
		push_error("FAIL: " + msg)
		print("FAIL: " + msg)


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(3)
	var b := view.battle
	var stapler := b.field.find_unit("stapler")

	# Movement area: the mask is 0.5 on the budget's edge and inside where it starts.
	var r := b.reach(stapler)
	var tex := ReachAreaTexture.build(r)
	var img := tex.shape.get_image()
	var at := func(p: Vector2) -> float:
		var uv := (p - tex.origin) / tex.size
		return img.get_pixel(int(uv.x * img.get_width()), int(uv.y * img.get_height())).r
	check(at.call(stapler.pos) > 0.9, "the area's mask is full where the unit stands")
	check(at.call(Vector2(-0.5, -0.5)) < 0.1, "and empty off the map")

	# Taking control: matchups, the type triangle and the reach marks.
	view.control(stapler)
	await process_frame
	check(view.plates._matchup == stapler, "the bars show matchups against the controlled unit")
	check(view.hud.type_triangle.visible, "the type triangle shows while a unit is controlled")
	check(view.plates._in_reach == b.basic_targets(stapler), "reticles mark exactly what it can hit from here")

	# Cover: Field.covering agrees with the rule it explains.
	var agree := true
	for e in b.enemy_units():
		var covered := b.field.has_half_cover(stapler, stapler.pos, e.pos)
		if covered != not b.field.covering(stapler, stapler.pos, e.pos).is_empty():
			agree = false
	check(agree, "the covering objects match has_half_cover")

	# Danger zone: every enemy that will act stands inside it.
	var grid := Forecast.danger_grid(b)
	var inside := true
	for e in b.enemy_units():
		if e.frozen:
			continue
		var cx := clampi(int(e.pos.x / ReachField.CELL), 0, grid.cols - 1)
		var cy := clampi(int(e.pos.y / ReachField.CELL), 0, grid.rows - 1)
		if grid.cells[cy * grid.cols + cx] < 0.5:
			inside = false
	check(inside, "every acting enemy stands in the danger zone")
	view.toggle_danger()
	check(view.overlays.is_danger_shown(), "V shows the danger zone")
	view.toggle_danger()
	check(not view.overlays.is_danger_shown(), "and hides it again")

	# Attack lists only what is in reach from here: nothing walks up on its own.
	view.open_menu()
	view.choose_action("attack")
	var only_near := true
	for t in view.selection.targets:
		if t is Unit and not b.basic_targets(stapler).has(t):
			only_near = false
	check(only_near, "Attack offers no enemies out of reach")
	view._back_to_menu()
	view.release()

	# Steer it in range of an enemy, then strike.
	var spot := Vector2.INF
	var keep := stapler.pos
	for s in b.reach(stapler).standing_spots(0.25):
		stapler.pos = s
		if not b.basic_targets(stapler).is_empty():
			spot = s
			break
	stapler.pos = keep
	check(spot != Vector2.INF, "there is a spot in range of an enemy")
	b.move_unit(stapler, spot)
	view.card_of(stapler).position = BattleSpace.to_world(stapler.pos)
	view.control(stapler)
	view.open_menu()
	view.choose_action("attack")
	var target: Unit = view.selection.current_target()
	var hp_before := target.hp
	var own_before := stapler.hp
	var stop_seen := false
	var pushed := false
	view.execute()
	await process_frame
	var until := Time.get_ticks_msec() + 30000
	while view.selection.mode == Mode.BUSY and Time.get_ticks_msec() < until:
		if Engine.time_scale < 0.1:
			stop_seen = true
		if view.camera.is_pushed_in():
			pushed = true
		await process_frame
	check(stapler.acted, "it attacked")
	var landed := target.hp < hp_before or stapler.hp < own_before # its strike or the counter
	check(stop_seen == landed, "a hit freezes the scene for a moment, a miss doesn't")
	check(pushed, "the camera pushed in for the strike")
	check(not view.camera.is_pushed_in(), "and eased back out after it")
	check(Engine.time_scale == 1.0, "time runs normally again")

	# A signature Art plays under the letterbox.
	var lamp := b.field.find_unit("lamp")
	view.control(lamp)
	view.open_menu()
	view.choose_action("art:spotlight")
	var letterboxed := false
	if view.selection.mode == Mode.TARGET:
		view.execute()
		await process_frame
		until = Time.get_ticks_msec() + 30000
		while view.selection.mode == Mode.BUSY and Time.get_ticks_msec() < until:
			if view.hud.letterbox_top.visible and view.hud.signature_name.text == "Spotlight":
				letterboxed = true
			await process_frame
	check(letterboxed, "Spotlight plays under the letterbox with its name card")
	check(not view.hud._signature_on, "the letterbox goes once it is over")
	print("BATTLE UI: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
