extends SceneTree
## Renders battle screens to PNG for review (needs a display, e.g. xvfb-run):
## godot --path . --script res://tools/screenshot.gd -- <out_dir>

func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var out := "user://shots"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	DirAccess.make_dir_recursive_absolute(out)
	root.size = Vector2i(1600, 900)
	var view := BattleView.new()
	root.add_child(view)
	await view.start(7)
	await _wait(10)
	_save(out + "/01_start.png")
	var stapler := view.battle.board.find_unit("stapler")
	view.select(stapler)
	view.hover = Vector2i(7, 5)
	view._on_hover()
	await _wait(5)
	_save(out + "/02_forecast.png")
	view._camera.zoom = Vector2(0.5, 0.5)
	view._pan(Vector2.ZERO)
	await _wait(5)
	_save(out + "/03_zoomed_out.png")
	view._camera.zoom = Vector2(1, 1)
	await view._move_to(Vector2i(7, 5))
	view.on_action("attack")
	view.hover = view.battle.board.find_unit("rubber").pos
	view._on_hover()
	await _wait(5)
	_save(out + "/04_combat_forecast.png")
	quit()


func _wait(n: int) -> void:
	for i in n:
		await process_frame


func _save(p: String) -> void:
	var img := root.get_texture().get_image()
	img.save_png(p)
	print("saved ", p)
