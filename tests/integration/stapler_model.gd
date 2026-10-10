extends SceneTree
## Stapler's 3D model in the real battle scene: it replaces the sprite card, has
## his clips (and none of Lamp's), the Staple Shot fires on the model's shot frame
## and its staple flies to a distant target, and his Arts play their own clips.
## His staples are 3D models fired from the pistols on the clips' shot frames.
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
	for anim in ["idle", "move", "attack", "pin", "staple_burst", "staple_storm", "hurt", "broken"]:
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
	var effects := view.event_player.effects
	var staples := [0]
	var seen := {}
	var watching := [true]
	var watch := func() -> void:
		while watching[0]:
			seen[model.current()] = true
			staples[0] = maxi(staples[0], effects.find_children("*", "MeshInstance3D", false, false).size())
			await process_frame
	watch.call()
	check(await _finishes(func() -> void: await view.event_player.play(events), 10.0), "a ranged Staple Shot plays through")
	check(staples[0] >= 1, "and fires a 3D staple")

	# Staple Burst: four staples on the clip's shot frames, two to each strike, and no
	# Staple Shot swing after the clip; Pin: one heavy staple on its charged shot.
	var shots := []
	for k in 4:
		shots.append(card.art_time("staple_burst", "shot_%d" % (k + 1)))
	check(shots == [0.25, 0.4, 0.55, 0.7], "Staple Burst's four shots are timed from the clip (%s)" % [shots])
	staples[0] = 0
	seen.clear()
	stapler.acted = false
	var burst := [
		{"type": "art", "unit": stapler, "art": "staple_burst", "name": "Staple Burst", "target": enemy},
		{"type": "strike", "attacker": stapler, "target": enemy, "hit": true, "crit": false, "damage": 2},
		{"type": "strike", "attacker": stapler, "target": enemy, "hit": false, "crit": false, "damage": 0},
	]
	check(await _finishes(func() -> void: await view.event_player.play(burst), 10.0), "Staple Burst plays through")
	check(seen.has("staple_burst") and not seen.has("attack"), "its own clip fires them, no Staple Shot swing")
	check(staples[0] >= 2, "with staples in the air together (%d)" % staples[0])
	staples[0] = 0
	seen.clear()
	var pin := [
		{"type": "art", "unit": stapler, "art": "pin", "name": "Pin", "target": enemy},
		{"type": "strike", "attacker": stapler, "target": enemy, "hit": true, "crit": false, "damage": 5},
	]
	check(await _finishes(func() -> void: await view.event_player.play(pin), 10.0), "Pin plays through")
	check(seen.has("pin") and not seen.has("attack") and staples[0] >= 1, "firing its heavy staple from its own clip")
	# Staple Storm through the rules: the camera pushes in, rings of staples fly out on
	# the volleys, no Staple Shot swing, and the camera comes back out.
	check(absf(card.art_time("staple_storm", "volley_1") - 1.167) < 0.01, "Staple Storm's first volley is 1.17s in")
	staples[0] = 0
	seen.clear()
	stapler.acted = false
	enemy.pos = stapler.pos + Vector2(stapler.radius + enemy.radius + 0.6, 0)
	view.card_of(enemy).position = BattleSpace.to_world(enemy.pos)
	var zoom := view.camera.distance
	check(b.use_art(stapler, "staple_storm", stapler), "Staple Storm resolves")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 12.0), "Staple Storm plays through")
	check(seen.has("staple_storm") and not seen.has("attack"), "with its own clip and no Staple Shot swing")
	check(staples[0] >= 10, "throwing a ring of staples (%d in the air at once)" % staples[0])
	await create_timer(0.6).timeout
	check(absf(view.camera.distance - zoom) < 0.05, "the camera eases back out after its push-in")
	watching[0] = false
	await create_timer(1.5).timeout
	check(effects.find_children("*", "MeshInstance3D", false, false).is_empty(), "every staple has cleaned itself up")
	print("STAPLER MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
