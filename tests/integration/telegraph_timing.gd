extends SceneTree
## The Paper Cutter's Cutting Line must appear on the floor when its turn is shown
## marking it, not as soon as the Enemy Phase starts playing (the rules already
## know the end state by then).
## godot --headless --path . --script res://tests/integration/telegraph_timing.gd

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
	await view.start(7)
	var b := view.battle
	var cutter := b.field.find_unit("cutter")
	# Bring a target within the Captain's lane so it marks one this Enemy Phase.
	var stapler := b.field.find_unit("stapler")
	stapler.pos = Vector2(9.5, 9.5)
	stapler.turn_start = stapler.pos
	view.card_of(stapler).position = BattleSpace.to_world(stapler.pos)
	check(view.overlays.shown_telegraphs.is_empty(), "no lane on the floor before the Enemy Phase")
	view.end_turn()
	await process_frame
	var appeared_far := false
	var appeared := false
	var until := Time.get_ticks_msec() + 40000
	while view.selection.mode == Mode.BUSY and Time.get_ticks_msec() < until:
		if not appeared and not view.overlays.shown_telegraphs.is_empty():
			appeared = true
			var at_cutter := BattleSpace.to_floor(view.camera.focus).distance_to(cutter.pos) < 3.0
			appeared_far = not at_cutter
		await process_frame
	check(not b.telegraphs.is_empty(), "the Captain marked a Cutting Line")
	check(appeared, "the lane appeared during playback")
	check(not appeared_far, "only once the camera had reached the Captain's turn")
	print("TELEGRAPH TIMING: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
