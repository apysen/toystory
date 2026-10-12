extends SceneTree
## Teacup's 3D model in the real battle scene: it replaces the sprite card, has her
## clips (and none of the others'), her cloth swings on spring bones as she runs and
## settles back, steam curls off her cup, her tea sloshes about and
## spills a little as she runs, Tea Lash snaps a rope of
## bent tea up after her hand and punches a dart of it from her palm on the clip's
## "hit", a hit holds her tea a third lower until her next attack refills it, Warm
## Pour carries a ribbon of tea to the ally and heals when it arrives (the clip's
## "hit"), and Tea Break, her signature, rings her with tea and heals every ally round
## her on its "hit", the camera pushed in and back out after. Everything it spawns
## cleans itself up.
## godot --headless --path . --script res://tests/integration/teacup_model.gd

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


func _ribbons(effects: Node) -> Array[Node]:
	return effects.find_children("*", "TeaRibbon", false, false)


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(3)
	var b := view.battle
	var cup := b.field.find_unit("teacup")
	check(cup != null, "Teacup is in the battle")
	if cup == null:
		quit(1)
		return
	var card := view.card_of(cup)
	var model: UnitModel = card.get_node_or_null("Model")
	check(model != null and model.visible, "Teacup shows her 3D model")
	check(not card.get_node("Card").visible, "and her sprite card is hidden")
	for anim in ["idle", "move", "attack", "warm_pour", "steady_sip", "tea_break", "hurt", "broken"]:
		check(card.has_anim(anim), "the model has '%s'" % anim)
	for anim in ["intercept_run", "spotlight", "overheat", "eject", "art", "ready", "gaze_in", "gaze_out"]:
		check(not card.has_anim(anim), "and no '%s' clip" % anim)
	check(cup.arts.has("tea_break"), "Tea Break is one of her Arts")
	check(absf(card.contact_time("attack") - 2.367) < 0.01, "Tea Lash's dart leaves 2.37s into the clip")
	check(absf(card.art_time("warm_pour", "hit") - 2.9) < 0.01, "Warm Pour's tea reaches the ally 2.9s in")
	check(absf(card.art_time("steady_sip", "hit") - 2.0) < 0.01, "Steady Sip's ward settles 2s in")
	check(absf(card.art_time("tea_break", "hit") - 3.8) < 0.01, "Tea Break heals 3.8s in")
	check(model.bone_position("bend_L") != Vector3.INF and model.bone_position("book") != Vector3.INF,
		"her bending and book bones came through")

	# her cloth is on spring bones: it swings as she runs and settles back after
	var springs := model.springs()
	check(springs != null and springs.simulator.setting_count >= 20, "her cloth hangs on spring bones (%d chains)" %
		(springs.simulator.setting_count if springs != null else 0))
	for other in ["lamp", "stapler", "toaster"]:
		var om: UnitModel = view.card_of(b.field.find_unit(other)).get_node_or_null("Model")
		check(om != null and om.springs() != null, "%s's cloth swings on spring bones too" % other)
	if springs != null:
		await create_timer(1.0).timeout
		springs.take_widest()
		card.face_along(Vector2(0, 1))
		card.set_moving(true)
		var run := card.create_tween()
		run.tween_property(card, "position", card.position + Vector3(0, 0, 1.8), 1.0)
		await run.finished
		card.set_moving(false)
		var swung: Dictionary = springs.take_widest()
		check(swung.get("cape", 0.0) > 5.0 and swung.get("skirt_FL", 0.0) > 3.0 and swung.get("tassel_0", 0.0) > 5.0,
			"running, her cape, skirts and tassels swing (cape %.0f, skirt %.0f, tassel %.0f degrees)" %
			[swung.get("cape", 0.0), swung.get("skirt_FL", 0.0), swung.get("tassel_0", 0.0)])
		check(swung.get("sleeve_R", 99.0) <= 10.01, "the sleeve drapes within their limit (%.1f degrees a link)" % swung.get("sleeve_R", 0.0))
		await create_timer(2.5).timeout
		springs.take_widest()
		await create_timer(0.5).timeout
		var still: Dictionary = springs.take_widest()
		var most := 0.0
		for chain in still:
			most = maxf(most, still[chain])
		check(most < 4.0, "standing, it settles back onto her clip (%.1f degrees at most)" % most)
		_place(view, cup, cup.pos)
		card.tea().refill()   # (the run spilt some)
		await create_timer(0.8).timeout

	# steam curls off her cup
	var tea := card.tea()
	check(tea != null, "her model keeps the tea in her cup")
	await create_timer(0.3).timeout
	var steam := tea.find_children("*", "CPUParticles3D", false, false)
	check(not steam.is_empty() and (steam[0] as CPUParticles3D).emitting, "steam curls off it")
	check((steam[0] as Node3D).global_position.distance_to(tea.surface()) < 0.1, "right over the tea")

	var effects := view.event_player.effects
	var seen := {}
	var ribbons := [0]
	var clip_t := [0.0]
	var watching := [true]
	var watch := func() -> void:
		while watching[0]:
			seen[model.current()] = true
			clip_t[0] += view.get_process_delta_time()
			ribbons[0] = maxi(ribbons[0], _ribbons(effects).size())
			await process_frame
	watch.call()

	# a hit: the flinch slops tea over the rim and holds it a third lower
	card.play_hurt()
	await create_timer(0.8).timeout
	check(absf(tea.held - 1.0 / 3.0) < 0.01, "a hit holds her tea a third of the way down")
	check(tea.lowered() > 0.004, "and the tea sits lower in her cup (%.1f mm)" % (tea.lowered() * 1000.0))

	# Tea Lash at a target out of reach: a rope of tea after her hand, then the dart
	# from her palm after the clip's "hit"; her next attack refills the cup.
	var enemies: Array = b.field.units.filter(func(u: Unit) -> bool: return u.faction == Defs.Faction.ENEMY and not u.broken)
	var enemy: Unit = enemies[0]
	_place(view, enemy, cup.pos + Vector2(0, cup.radius + enemy.radius + 1.4))
	var lash := [
		{"type": "strike", "attacker": cup, "target": enemy, "hit": true, "crit": false, "damage": 2},
		{"type": "damage", "unit": enemy, "hp": enemy.hp - 2},
	]
	var dart_from := [Vector3.INF]
	var hand := [Vector3.INF]
	var watch_dart := func() -> void:
		var before := 0
		while watching[0] and dart_from[0] == Vector3.INF:
			var now := _ribbons(effects)
			if model.current() == "attack" and now.size() > before and before > 0:
				dart_from[0] = (now[now.size() - 1] as TeaRibbon).head.call()
				hand[0] = model.bone_position("bend_L")
			before = now.size()
			await process_frame
	watch_dart.call()
	check(await _finishes(func() -> void: await view.event_player.play(lash), 10.0), "a Tea Lash plays through")
	check(seen.has("attack"), "with her attack clip")
	check(ribbons[0] >= 2, "a rope of tea and a dart of it fly (%d ribbons at once)" % ribbons[0])
	check(dart_from[0] != Vector3.INF and dart_from[0].distance_to(hand[0]) < 0.15,
		"the dart leaves from her bending hand (%.2f m off it)" % dart_from[0].distance_to(hand[0]))
	await create_timer(1.6).timeout
	check(tea.held < 0.01 and tea.lowered() < 0.001, "and her cup is full again as the clip refills it")

	# running: the tea sloshes about in the cup and spills a little over the rim
	card.set_moving(true)
	var tip := [0.0]
	var spills := [0]
	var t_end := Time.get_ticks_msec() + 1500
	while Time.get_ticks_msec() < t_end:
		tip[0] = maxf(tip[0], tea.tipped())
		spills[0] = maxi(spills[0], tea.find_children("*", "CPUParticles3D", false, false).size() - 1)
		await process_frame
	card.set_moving(false)
	check(tip[0] > deg_to_rad(2.0), "running, her tea tips about in the cup (%.1f degrees)" % rad_to_deg(tip[0]))
	check(spills[0] >= 1, "and spills a little over the rim")
	check(tea.held > 0.1 and tea.held <= 1.0 / 3.0 + 0.001, "running low, at most a third down (%.2f)" % tea.held)
	tea.refill()
	await create_timer(0.8).timeout

	# Warm Pour through the rules: the tea flows to the ally; they heal when it arrives.
	var lamp := b.field.find_unit("lamp")
	_place(view, lamp, cup.pos + Vector2(cup.radius + lamp.radius + 0.8, 0))
	lamp.hp = 10
	view.card_of(lamp).shown_hp = 10
	cup.acted = false
	seen.clear()
	ribbons[0] = 0
	check(b.use_art(cup, "warm_pour", lamp), "Warm Pour resolves")
	var healed_at := [-1.0]
	var watch_heal := func() -> void:
		while watching[0] and healed_at[0] < 0.0:
			if view.card_of(lamp).shown_hp > 10:
				healed_at[0] = clip_t[0]
			await process_frame
	clip_t[0] = 0.0
	watch_heal.call()
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 15.0), "Warm Pour plays through")
	check(seen.has("warm_pour") and not seen.has("attack"), "with its own clip")
	check(ribbons[0] >= 2, "ribbons of tea flow round her hands and across (%d at once)" % ribbons[0])
	check(healed_at[0] >= 2.8, "Lamp's HP rises when the tea reaches him (%.2fs in)" % healed_at[0])

	# Tea Break through the rules: Lamp and Teacup heal, Stapler further off doesn't;
	# the camera pushes in and eases back out after.
	var stapler := b.field.find_unit("stapler")
	_place(view, lamp, cup.pos + Vector2(cup.radius + lamp.radius + 0.3, 0))
	_place(view, stapler, cup.pos + Vector2(0, -3.0))
	for u in [cup, lamp, stapler]:
		u.hp = 8
		view.card_of(u).shown_hp = 8
	cup.acted = false
	b.noise = 0
	seen.clear()
	ribbons[0] = 0
	var zoom := view.camera.distance
	var closest := [zoom]
	var watch_zoom := func() -> void:
		while watching[0]:
			closest[0] = minf(closest[0], view.camera.distance)
			await process_frame
	watch_zoom.call()
	check(b.use_art(cup, "tea_break", cup), "Tea Break resolves")
	healed_at[0] = -1.0
	clip_t[0] = 0.0
	watch_heal.call()
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 20.0), "Tea Break plays through")
	check(seen.has("tea_break") and not seen.has("attack"), "with its own clip")
	check(ribbons[0] >= 6, "its tea rings her and bursts out (%d ribbons at once)" % ribbons[0])
	check(view.card_of(lamp).shown_hp > 8 and card.shown_hp > 8, "Lamp and Teacup heal")
	check(view.card_of(stapler).shown_hp == 8, "Stapler out of the circle doesn't")
	check(healed_at[0] >= 3.7, "the heals land on the clip's hit (%.2fs after the camera push-in)" % healed_at[0])
	check(closest[0] < zoom - 0.1, "the camera pushes in for the signature")
	await create_timer(0.6).timeout
	check(absf(view.camera.distance - zoom) < 0.05, "and eases back out after")
	watching[0] = false
	await create_timer(2.0).timeout
	check(_ribbons(effects).is_empty(), "every ribbon of tea has drained away")
	check(effects.find_children("*", "CPUParticles3D", false, false).is_empty(), "and every splash and sparkle")
	check(effects.find_children("*", "AnimatedSprite3D", false, false).is_empty(), "and every other effect")

	# Broken: the steam stops and the tea pours out into a puddle
	card.play_broken()
	await create_timer(2.0).timeout
	check(not (steam[0] as CPUParticles3D).emitting, "a Broken Teacup's tea goes cold")
	check(tea.find_child("Puddle", false, false) != null, "and pours out into a puddle")
	print("TEACUP MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
