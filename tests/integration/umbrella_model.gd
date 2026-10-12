extends SceneTree
## Umbrella's 3D model in the real battle scene: it replaces the sprite card and has
## his clips (and none of the others'). Moving launches him into his float (dust kicks
## up), stopping leaves him hovering, and he lands by himself after 3 s still, or at
## once when his action ring opens. Lunge plays its lead-in, dashes with the couched
## run (never the float) and strikes with its own clip; Canopy opens over his
## neighbours; Raincheck, his signature, rains over its circle with the camera pushed
## in, and a shot it draws off an ally flies to him. Everything it spawns cleans up.
## godot --headless --path . --script res://tests/integration/umbrella_model.gd

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


func _place(view: BattleRoot, u: Unit, at: Vector2) -> void:
	u.pos = at
	view.card_of(u).position = BattleSpace.to_world(at)


## Waits until `model` is playing `anim`, for at most `seconds`.
func _reaches(model: UnitModel, anim: String, seconds: float) -> bool:
	var until := Time.get_ticks_msec() + int(seconds * 1000)
	while model.current() != anim and Time.get_ticks_msec() < until:
		await process_frame
	return model.current() == anim


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(3)
	var b := view.battle
	var umb := b.field.find_unit("umbrella")
	check(umb != null and umb.faction == Defs.Faction.PLAYER, "Umbrella starts in the squad (the dev switch)")
	if umb == null:
		quit(1)
		return
	var crowded := b.field.living_units().filter(func(o: Unit) -> bool:
		return o != umb and o.pos.distance_to(umb.pos) < o.radius + umb.radius)
	check(crowded.is_empty(), "he starts clear of every other unit")
	check(not b.reach(umb).standing_spots(0.5).is_empty(), "and can move from where he starts")
	var card := view.card_of(umb)
	var model: UnitModel = card.get_node_or_null("Model")
	check(model != null and model.visible, "Umbrella shows his 3D model")
	check(not card.get_node("Card").visible, "and his sprite card is hidden")
	for anim in ["idle", "move_start", "move", "hover", "move_end", "attack", "lunge", "lunge_run", "lunge_strike",
			"canopy", "raincheck", "hurt", "broken"]:
		check(card.has_anim(anim), "the model has '%s'" % anim)
	for anim in ["intercept_run", "spotlight", "tea_break", "art", "ready", "gaze_in", "gaze_out"]:
		check(not card.has_anim(anim), "and no '%s' clip" % anim)
	check(umb.arts.has("raincheck"), "Raincheck is one of his Arts")
	check(absf(card.contact_time("attack") - 2.2) < 0.01, "Tip Thrust lands 2.2s into its clip")
	check(absf(card.contact_time("lunge_strike") - 0.2) < 0.01, "Lunge's spike lands 0.2s into its strike")
	check(absf(card.art_time("canopy", "open") - 1.2) < 0.01, "Canopy stands open 1.2s in")
	check(absf(card.art_time("raincheck", "open") - 1.1) < 0.01 and absf(card.art_time("raincheck", "end") - 4.167) < 0.01,
		"Raincheck opens 1.1s in and closes 4.17s in")
	check(absf(card.art_time("lunge_run", "speed") - 2.6 * UnitModel.SCALE.umbrella) < 0.01,
		"the charge runs at the 2.6 m/s it was authored for, at his shown size")
	# shown about as tall as the rest of the squad (his hat's cross over the floor)
	var tops := {}
	for id in ["lamp", "stapler", "toaster", "teacup", "umbrella"]:
		var m: UnitModel = view.card_of(b.field.find_unit(id)).get_node_or_null("Model")
		var top := -INF
		for mi: MeshInstance3D in m.find_children("*", "MeshInstance3D", true, false):
			var box := mi.global_transform * mi.get_aabb()
			top = maxf(top, box.end.y - m.global_position.y)
		tops[id] = top
	var others: float = (tops.lamp + tops.stapler + tops.toaster + tops.teacup) / 4.0
	check(absf(tops.umbrella - others) < 0.05, "he stands about as tall as the others (%.2f m, they average %.2f)" %
		[tops.umbrella, others])
	var springs := model.springs()
	check(springs != null and springs.simulator.setting_count >= 10, "his cape, tabard and hat drops hang on spring bones")
	await create_timer(0.5).timeout

	var effects := view.event_player.effects
	var seen := {}
	var watching := [true]
	var watch := func() -> void:
		while watching[0]:
			seen[model.current()] = true
			await process_frame
	watch.call()

	# travel: a launch into the float, hovering when he stops, landing after 3 s still
	_place(view, umb, Vector2(2.5, 5.5))
	card.face_along(Vector2(0, 1))
	card.set_moving(true)
	check(model.current() == "move_start" and model.is_aloft(), "moving launches him (move_start)")
	var dust := [false]
	var watch_dust := func() -> void:
		var until := Time.get_ticks_msec() + 800
		while Time.get_ticks_msec() < until:
			if not effects.find_children("*", "AnimatedSprite3D", false, false).is_empty():
				dust[0] = true
			await process_frame
	watch_dust.call()
	check(await _reaches(model, "move", 1.5), "and he floats on (move)")
	check(dust[0], "dust kicks up as he springs off the floor")
	var lifted := model.bone_position("hips").y - card.global_position.y
	check(lifted > 0.5, "he hangs off the floor (hips %.2f m up)" % lifted)
	var run := card.create_tween()
	run.tween_property(card, "position", card.position + Vector3(0, 0, 1.0), 0.6)
	await run.finished
	card.set_moving(false)
	check(await _reaches(model, "hover", 0.5), "stopping leaves him hovering")
	await create_timer(1.5).timeout
	check(model.current() == "hover" and model.is_aloft(), "still aloft 1.5s later")
	card.set_moving(true)
	check(await _reaches(model, "move", 0.5) and not seen.has("move_end"), "moving again floats on without landing")
	card.set_moving(false)
	check(await _reaches(model, "move_end", model.land_after + 0.8), "after %.0fs still he lands (move_end)" % model.land_after)
	check(await _reaches(model, "idle", 1.5) and not model.is_aloft(), "and stands at idle, umbrella shouldered")
	_place(view, umb, umb.pos)

	# the action ring lands him at once
	umb.acted = false
	view.control(umb)
	card.set_moving(true)
	await _reaches(model, "move", 1.5)
	card.set_moving(false)
	await _reaches(model, "hover", 0.5)
	view.open_menu()
	check(model.current() == "move_end", "opening his action ring lands him straight away")
	check(await _reaches(model, "idle", 1.5), "before he picks what to do")
	view.release()

	# Lunge through the rules: lead-in, couched dash (no float), its own strike
	var foe := b.field.find_unit("pencil_a")
	_place(view, umb, Vector2(2.5, 5.5))
	_place(view, foe, Vector2(2.5, 8.0))
	umb.acted = false
	b.noise = 0
	seen.clear()
	var start := card.position
	check(b.use_art(umb, "lunge", foe), "Lunge resolves")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 15.0), "Lunge plays through")
	check(seen.has("lunge") and seen.has("lunge_run") and seen.has("lunge_strike"), "lead-in, couched charge and strike")
	check(not seen.has("move_start") and not seen.has("attack"), "never the float or the basic swing")
	check(card.position.distance_to(start) > 1.0, "he dashed up to his target (%.2f m)" % card.position.distance_to(start))
	await _reaches(model, "idle", 2.0)

	# Canopy: his neighbour shimmers into Half Cover on "open"
	var lamp := b.field.find_unit("lamp")
	_place(view, lamp, umb.pos + Vector2(umb.radius + lamp.radius + 0.02, 0))
	umb.acted = false
	seen.clear()
	check(b.use_art(umb, "canopy", umb) and lamp.status.has("canopy"), "Canopy covers Lamp beside him")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 10.0), "Canopy plays through")
	check(seen.has("canopy") and not seen.has("attack"), "with its own clip")

	# Raincheck: rain falls over his circle, the camera pushes in and back out
	umb.acted = false
	b.noise = 0
	seen.clear()
	var zoom := view.camera.distance
	var closest := [zoom]
	var rain := [0]
	var watch_rain := func() -> void:
		while watching[0]:
			closest[0] = minf(closest[0], view.camera.distance)
			rain[0] = maxi(rain[0], effects.find_children("*", "CPUParticles3D", false, false).size())
			await process_frame
	watch_rain.call()
	check(b.use_art(umb, "raincheck", umb), "Raincheck resolves")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 15.0), "Raincheck plays through")
	check(seen.has("raincheck"), "with its own clip")
	check(rain[0] >= 1, "rain falls over his circle")
	check(closest[0] < zoom - 0.1, "the camera pushes in for the signature")
	await create_timer(0.6).timeout
	check(absf(view.camera.distance - zoom) < 0.05, "and eases back out after")

	# a shot at Lamp beside him goes to Umbrella instead
	var rubber := b.field.find_unit("rubber")
	_place(view, rubber, lamp.pos + Vector2(0, 1.6))
	var res := b.enemy_attack(rubber, lamp)
	check(res.target == umb, "a ranged shot at Lamp is drawn to Umbrella")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 10.0), "and plays through")
	watching[0] = false
	await create_timer(2.5).timeout
	check(effects.find_children("*", "CPUParticles3D", false, false).is_empty(), "the rain has stopped and cleared")
	check(effects.find_children("*", "AnimatedSprite3D", false, false).is_empty(), "and every splash and puff")
	print("UMBRELLA MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
