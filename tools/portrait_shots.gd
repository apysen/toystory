extends SceneTree
## Renders the menus and one dialogue line per speaker to PNG:
## godot --path . --script res://tools/portrait_shots.gd -- <out_dir>

const APP_SCENE := "res://scenes/app/app.tscn"
const BATTLE_SCENE := "res://scenes/battle/battle.tscn"


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	var out := OS.get_cmdline_user_args()[0] if OS.get_cmdline_user_args().size() > 0 else "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	root.size = Vector2i(1600, 900)
	var app: AppRoot = load(APP_SCENE).instantiate()
	root.add_child(app)
	await _wait(3)
	_save(out + "/mission_select.png")
	app.show_team_preview()
	await _wait(5)
	_save(out + "/team_preview.png")
	app.queue_free()
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(7)
	var i := 0
	for sp in ["Lamp", "Vacuum", "Paper Cutter Captain", "Umbrella", "Pencil Lancer", "Robot Vacuum"]:
		view.dialogue.play([{"speaker": sp, "text": "Portrait check for %s." % sp}])
		await _wait(5)
		_save(out + "/dialogue_%d.png" % i)
		view.dialogue.advance()
		i += 1
	quit()


func _wait(frames: int) -> void:
	for _i in frames:
		await process_frame


func _save(path: String) -> void:
	root.get_texture().get_image().save_png(path)
	print("saved ", path)
