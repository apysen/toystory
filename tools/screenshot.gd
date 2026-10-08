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
	await _wait(10)
	_save(out + "/01_start.png")
	var stapler := view.battle.board.find_unit("stapler")
	view.select(stapler)
	view.selection.hover = Vector2i(7, 5)
	view.refresh_hover()
	await _wait(5)
	_save(out + "/02_forecast.png")
	view.camera.set_zoom_level(0.5)
	await _wait(5)
	_save(out + "/03_zoomed_out.png")
	view.camera.set_zoom_level(1.0)
	await view.move_to(Vector2i(7, 5))
	view.on_action("attack")
	view.selection.hover = view.battle.board.find_unit("rubber").pos
	view.refresh_hover()
	await _wait(5)
	_save(out + "/04_combat_forecast.png")
	view.cancel()
	view.cancel()
	view.battle.noise = 5
	var toaster := view.battle.board.find_unit("toaster")
	view.battle.add_noise(2, toaster)
	await view.event_player.play(view.battle.take_events())
	view.camera.move_to(view.board_view.tile_center(Vector2i(4, 3)))
	await _wait(30)
	_save(out + "/05_gaze.png")
	view.open_pause()
	await _wait(5)
	_save(out + "/06_pause.png")
	view.pause_menu.close()
	quit()


func _wait(n: int) -> void:
	for i in n:
		await process_frame


func _save(p: String) -> void:
	var img := root.get_texture().get_image()
	img.save_png(p)
	print("saved ", p)
