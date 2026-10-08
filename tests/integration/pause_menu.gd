extends SceneTree
## Opens the pause menu in the real battle scene and checks that it pauses the
## battle, that the volume slider drives the bus and is saved, and that Resume and
## Return to Missions work: godot --headless --path . --script res://tests/integration/pause_menu.gd

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"

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
	# Keep the player's own saved volume: put it back when done.
	var saved := SettingsStore.read_volume(AudioSettings.VOLUME_KEY, -1.0)
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	var abandoned := [false]
	view.battle_abandoned.connect(func(): abandoned[0] = true)
	await view.start(5)
	var menu := view.pause_menu

	var esc := InputEventAction.new()
	esc.action = "cancel"
	esc.pressed = true
	root.push_input(esc)
	await process_frame
	check(menu.is_open() and paused, "Esc with nothing selected opens the menu and pauses")

	menu.volume_slider.value = 50
	var bus := AudioServer.get_bus_index(view.audio_settings.bus_name)
	check(is_equal_approx(AudioServer.get_bus_volume_db(bus), linear_to_db(0.5 * view.audio_settings.max_linear_volume)), "slider sets the bus volume")
	check(menu.volume_value.text == "50%", "slider shows its percentage")
	check(is_equal_approx(SettingsStore.read_volume(AudioSettings.VOLUME_KEY, -1.0), 0.5), "volume is saved")
	menu.volume_slider.value = 0
	check(AudioServer.is_bus_mute(bus), "zero volume mutes the bus")

	var saved_fullscreen := SettingsStore.read_flag(DisplaySettings.FULLSCREEN_KEY, false)
	menu.fullscreen_button.pressed.emit()
	check(SettingsStore.read_flag(DisplaySettings.FULLSCREEN_KEY, false) != saved_fullscreen, "Fullscreen button saves the choice")
	SettingsStore.write_flag(DisplaySettings.FULLSCREEN_KEY, saved_fullscreen)

	menu.resume_button.pressed.emit()
	await process_frame
	check(not menu.is_open() and not paused, "Resume closes the menu and unpauses")

	var start_button := InputEventAction.new()
	start_button.action = "pause"
	start_button.pressed = true
	root.push_input(start_button)
	await process_frame
	check(menu.is_open() and paused, "the controller's Start button opens the menu")
	menu.main_menu_button.pressed.emit()
	await process_frame
	check(abandoned[0] and not paused, "Return to Missions leaves the battle unpaused")

	if saved >= 0.0:
		SettingsStore.write_volume(AudioSettings.VOLUME_KEY, saved)
	else:
		var config := ConfigFile.new()
		if config.load(SettingsStore.PATH) == OK:
			config.erase_section_key(SettingsStore.AUDIO_SECTION, AudioSettings.VOLUME_KEY)
			config.save(SettingsStore.PATH)
	print("PAUSE MENU: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
