extends SceneTree
## Stapler's 3D model in the real battle scene: it replaces the sprite card, has
## his clips (and none of Lamp's), the Staple Shot fires on the model's shot frame
## and its staple flies to a distant target, and his Arts play their own clips.
## godot --headless --path . --script res://tests/integration/stapler_model.gd

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


## Awaits a coroutine-returning call, giving up after `seconds`.
func _finishes(c: Callable, seconds: float) -> bool:
	var done := [false]
	var run := func() -> void:
		await c.call()
		done[0] = true
	run.call()
	var until := Time.get_ticks_msec() + int(seconds * 1000)
	while not done[0] and Time.get_ticks_msec() < until:
		await process_frame
	return done[0]


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(3)
	var b := view.battle
	var stapler := b.field.find_unit("stapler")
	check(stapler != null, "Stapler is in the battle")
	if stapler == null:
		quit(1)
		return
	var card := view.card_of(stapler)
	var model: UnitModel = card.get_node_or_null("Model")
	check(model != null and model.visible, "Stapler shows his 3D model")
	check(not card.get_node("Card").visible, "and his sprite card is hidden")
	for anim in ["idle", "move", "attack", "pin", "staple_burst", "heavy_duty", "hurt", "broken"]:
		check(card.has_anim(anim), "the model has '%s'" % anim)
	for anim in ["intercept_run", "intercept_guard", "spotlight", "art", "ready", "gaze_in", "gaze_out"]:
		check(not card.has_anim(anim), "and no '%s' clip" % anim)

	check(absf(card.contact_time("attack") - 0.3) < 0.01, "the Staple Shot fires 0.3s into the clip")
	check(await _finishes(func() -> void: await card.play_once("attack"), 3.0), "attack plays through and finishes")
	check(model.current() == "idle", "and settles back into idle")
	check(await _finishes(func() -> void: await card.play_art("pin"), 4.0), "Pin plays its own clip")
	check(await _finishes(func() -> void: await card.play_art("staple_burst"), 4.0), "Staple Burst plays its own clip")

	# A Staple Shot at a target out of reach: the staple flies after the shot frame.
	var enemy: Unit = b.field.units.filter(func(u: Unit) -> bool: return u.faction == Defs.Faction.ENEMY)[0]
	enemy.pos = stapler.pos + Vector2(0, stapler.radius + enemy.radius + 1.2)
	view.card_of(enemy).position = BattleSpace.to_world(enemy.pos)
	var events := [
		{"type": "strike", "attacker": stapler, "target": enemy, "hit": true, "crit": false, "damage": 2},
		{"type": "damage", "unit": enemy, "hp": enemy.hp - 2},
	]
	check(await _finishes(func() -> void: await view.event_player.play(events), 10.0), "a ranged Staple Shot plays through")
	print("STAPLER MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
