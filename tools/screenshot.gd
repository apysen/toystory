extends SceneTree
## Renders battle screens to PNG for review (needs a display):
## godot --path . --script res://tools/screenshot.gd -- <out_dir>

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var out := "user://shots"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	DirAccess.make_dir_recursive_absolute(out)
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(7)
	await _wait(20)
	_save(out + "/01_start.png")
	var b := view.battle
	var stapler := b.field.find_unit("stapler")
	view.control(stapler)
	await _wait(10)
	# Walk the stapler to the nearest spot with an enemy in reach.
	var goal := stapler.pos
	var saved := stapler.pos
	for spot in b.reach(stapler).standing_spots(0.4):
		stapler.pos = spot
		if not b.basic_targets(stapler).is_empty():
			goal = spot
			break
	stapler.pos = saved
	var path := b.reach(stapler).path_to(goal)
	for k in range(1, path.size()):
		var from := stapler.pos
		var steps := int(ceil(from.distance_to(path[k]) / 0.08))
		for i in steps:
			var to := from.lerp(path[k], float(i + 1) / steps)
			if b.move_unit(stapler, to):
				view.card_of(stapler).position = BattleSpace.to_world(to)
				view.card_of(stapler).face_along(path[k] - from)
			await process_frame
	await _wait(25)
	_save(out + "/02_control.png")
	view.open_menu()
	await _wait(15)
	_save(out + "/03_ring.png")
	view.ring.turn(1)
	await _wait(15)
	_save(out + "/04_ring_turned.png")
	view.ring.turn(-1)
	await _wait(10)
	view.ring.choose()
	await _wait(20)
	_save(out + "/05_preview.png")
	view.camera.yaw += 1.4
	await _wait(25)
	_save(out + "/06_orbit.png")
	view._back_to_menu()
	view._close_menu()
	view.release()
	b.noise = 5
	var toaster := b.field.find_unit("toaster")
	b.add_noise(2, toaster)
	await view.event_player.play(b.take_events())
	view.camera.look_at_point(BattleSpace.to_world(Vector2(3, 3)), true)
	await _wait(30)
	_save(out + "/07_gaze.png")
	view.camera.distance = 22.0
	view.camera.pitch = deg_to_rad(68)
	view.camera.look_at_point(BattleSpace.to_world(Vector2(7.5, 5.5)), true)
	await _wait(30)
	_save(out + "/08_overview.png")
	view.camera.yaw = PI
	view.camera.pitch = deg_to_rad(30)
	view.camera.distance = view.camera.max_distance
	await _wait(30)
	_save(out + "/10_zoomed_out_from_wall.png")
	view.camera.yaw = PI * 0.5
	await _wait(30)
	_save(out + "/11_zoomed_out_side.png")
	view.open_pause()
	await _wait(5)
	_save(out + "/09_pause.png")
	view.pause_menu.close()
	quit()


## Waits `n` frames, and at least n/60 seconds so tweens finish even when frames run fast.
func _wait(n: int) -> void:
	var until := Time.get_ticks_msec() + n * 1000 / 60
	for i in n:
		await process_frame
	while Time.get_ticks_msec() < until:
		await process_frame


func _save(p: String) -> void:
	var img := root.get_texture().get_image()
	img.save_png(p)
	print("saved ", p)
