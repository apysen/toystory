extends SceneTree
## Triggers a Human Gaze through the real battle flow, catching the acting unit and
## the Paper Cutter, and checks the battle carries on: no softlock in playback, the
## Captain's Cutting Line is called off, and the Enemy Phase still runs.
## godot --headless --path . --script res://tests/integration/gaze_flow.gd

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


func _wait_while_busy(view: BattleRoot, seconds: float) -> bool:
	var until := Time.get_ticks_msec() + int(seconds * 1000)
	while view.selection.mode == Mode.BUSY and Time.get_ticks_msec() < until:
		await process_frame
	return view.selection.mode != Mode.BUSY


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(7)
	var b := view.battle
	var toaster := b.field.find_unit("toaster")
	var cutter := b.field.find_unit("cutter")
	toaster.pos = Vector2(11.2, 9.5)
	toaster.turn_start = toaster.pos
	view.card_of(toaster).position = BattleSpace.to_world(toaster.pos)
	EnemyAI.new(b).act(cutter)
	b.take_events()
	check(b.telegraphs.size() == 1, "the Captain has marked a Cutting Line")
	b.noise = 5
	view.control(toaster)
	view.open_menu()
	view.choose_action("art:flash_bake")
	view.selection.aim = (cutter.pos - toaster.pos).normalized()
	view.execute()
	check(await _wait_while_busy(view, 15.0), "playback finishes after a Gaze catches units mid-attack")
	check(view.selection.mode == Mode.IDLE, "and hands control back")
	check(b.gaze_active() and cutter.frozen, "the Captain is watched")
	check(b.telegraphs.is_empty(), "its Cutting Line is called off")
	check(view.card_of(toaster).shows_frozen, "Toaster shows its object form")
	view.end_turn()
	await process_frame
	check(await _wait_while_busy(view, 30.0), "the Enemy Phase plays through")
	check(b.turn == 2 and not b.gaze_active(), "the Gaze lifts on the next Player Phase")
	check(not view.card_of(toaster).shows_frozen, "Toaster is itself again")
	print("GAZE FLOW: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
