extends SceneTree
## Toaster's 3D model in the real battle scene: it replaces the sprite card, has his
## clips (and none of the others'), his palm flames burn and turn into rocket jets on
## the move, Toast Pop launches a 3D slice on the clip's "hit" and brings a fresh one
## up browned, Eject fires both slices from its own clip, Flash Bake blasts its cone
## of fire, and Overheat erupts: a slice at each enemy struck, the burn without a
## flinch, and the camera back out. Everything it spawns cleans itself up.
## godot --headless --path . --script res://tests/integration/toaster_model.gd

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


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var view: BattleRoot = load(BATTLE_SCENE).instantiate()
	root.add_child(view)
	await view.start(3)
	var b := view.battle
	var toaster := b.field.find_unit("toaster")
	check(toaster != null, "Toaster is in the battle")
	if toaster == null:
		quit(1)
		return
	var card := view.card_of(toaster)
	var model: UnitModel = card.get_node_or_null("Model")
	check(model != null and model.visible, "Toaster shows his 3D model")
	check(not card.get_node("Card").visible, "and his sprite card is hidden")
	for anim in ["idle", "move", "attack", "eject", "flash_bake", "overheat", "hurt", "broken"]:
		check(card.has_anim(anim), "the model has '%s'" % anim)
	for anim in ["intercept_run", "spotlight", "pin", "staple_storm", "art", "ready", "gaze_in", "gaze_out"]:
		check(not card.has_anim(anim), "and no '%s' clip" % anim)
	check(absf(card.contact_time("attack") - 2.267) < 0.01, "Toast Pop's slice leaves 2.27s into the clip")
	check(absf(card.art_time("eject", "hit") - 2.833) < 0.01, "Eject's slices blast out 2.83s in")
	check(absf(card.art_time("overheat", "erupt") - 2.5) < 0.01, "Overheat erupts 2.5s in")

	# his palm flames burn, and on the move they shoot back as rocket jets
	var fire := card.fire()
	check(fire != null, "his model keeps fire burning on its bones")
	await create_timer(0.2).timeout
	var palms := fire.find_children("*", "CPUParticles3D", false, false)
	check(palms.size() >= 2 and (palms[0] as CPUParticles3D).emitting, "a flame burns in each palm")
	check((palms[0] as CPUParticles3D).direction.y > 0.9, "burning upright while he stands")
	card.set_moving(true)
	await create_timer(0.3).timeout
	check((palms[0] as CPUParticles3D).direction.y < 0.6, "and shooting back as a rocket jet on the move")
	card.set_moving(false)

	var enemies: Array = b.field.units.filter(func(u: Unit) -> bool: return u.faction == Defs.Faction.ENEMY and not u.broken)
	var enemy: Unit = enemies[0]
	var effects := view.event_player.effects
	var seen := {}
	var toasts := [0]
	var flames := [0]
	var front_gone := [false]
	var watching := [true]
	var watch := func() -> void:
		while watching[0]:
			seen[model.current()] = true
			toasts[0] = maxi(toasts[0], effects.find_children("*", "MeshInstance3D", false, false).size())
			flames[0] = maxi(flames[0], effects.find_children("*", "CPUParticles3D", false, false).size())
			front_gone[0] = front_gone[0] or (model.slice_hidden("front") and not model.slice_hidden("back"))
			await process_frame
	watch.call()

	# Toast Pop at a target out of reach: the front slice flies after the clip's
	# "hit", is gone from its slot, and a fresh one comes back up browned.
	_place(view, enemy, toaster.pos + Vector2(0, toaster.radius + enemy.radius + 1.4))
	var pop := [
		{"type": "strike", "attacker": toaster, "target": enemy, "hit": true, "crit": false, "damage": 3},
		{"type": "damage", "unit": enemy, "hp": enemy.hp - 3},
	]
	check(await _finishes(func() -> void: await view.event_player.play(pop), 10.0), "a Toast Pop plays through")
	check(toasts[0] >= 1, "and launches a 3D slice of toast")
	check(front_gone[0], "the launched front slice is gone from its slot (the back one stays)")
	await create_timer(1.0).timeout
	check(not model.slice_hidden("front") and model.slice_brown("front") > 0.99, "a fresh front slice comes back up browned")

	# Eject through the rules: both slices at the target from its own clip, no Toast Pop.
	toasts[0] = 0
	seen.clear()
	_place(view, enemy, toaster.pos + Vector2(toaster.radius + enemy.radius + 0.8, 0))
	check(b.use_art(toaster, "eject", enemy), "Eject resolves")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 15.0), "Eject plays through")
	check(seen.has("eject") and not seen.has("attack"), "with its own clip and no Toast Pop swing")
	check(toasts[0] >= 2, "blasting both slices together (%d in the air)" % toasts[0])
	check(model.slice_brown("back") > 0.99 and not model.slice_hidden("back"), "and both come back up browned")

	# Flash Bake through the rules: the palm flames grow and a cone of fire blasts out.
	flames[0] = 0
	seen.clear()
	toaster.acted = false
	var heat := [1.0]
	var watch_heat := func() -> void:
		while watching[0]:
			heat[0] = maxf(heat[0], fire.heat)
			await process_frame
	watch_heat.call()
	check(b.use_art(toaster, "flash_bake", (enemy.pos - toaster.pos).normalized()), "Flash Bake resolves")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 15.0), "Flash Bake plays through")
	check(seen.has("flash_bake") and not seen.has("attack"), "with its own clip")
	check(heat[0] > 1.5, "his palm flames grow as he charges (heat %.2f)" % heat[0])
	check(flames[0] >= 2, "and fire blasts out of both palms (%d emitters)" % flames[0])

	# Overheat through the rules with three enemies round him: a slice at each one
	# struck, sky-high, the burn shown without a flinch, the camera back out after.
	toasts[0] = 0
	flames[0] = 0
	seen.clear()
	toaster.acted = false
	var around: Array = enemies.slice(0, 3)
	for k in around.size():
		var a := TAU * k / around.size()
		_place(view, around[k], toaster.pos + Vector2(cos(a), sin(a)) * 1.2)
	var zoom := view.camera.distance
	var hp := toaster.hp
	check(b.use_art(toaster, "overheat", toaster), "Overheat resolves")
	var events := b.take_events()
	var struck := events.filter(func(e): return e.type == "strike" and e.attacker == toaster).size()
	check(struck >= 2, "it strikes the enemies round him (%d)" % struck)
	check(toaster.hp < hp, "and burns some of Toaster's own HP")
	check(await _finishes(func() -> void: await view.event_player.play(events), 20.0), "Overheat plays through")
	check(seen.has("overheat") and not seen.has("attack") and not seen.has("hurt"),
		"with its own clip, no Toast Pop swing and no flinch at the burn")
	check(toasts[0] >= mini(struck, 2), "launching a slice at each enemy struck (%d in the air)" % toasts[0])
	check(flames[0] >= 3, "with fire swirling and pillars erupting (%d emitters)" % flames[0])
	await create_timer(0.6).timeout
	check(absf(view.camera.distance - zoom) < 0.05, "the camera eases back out after its push-in")
	check(not model.slice_hidden("front") and not model.slice_hidden("back"), "and fresh slices are back in the slots")
	watching[0] = false
	await create_timer(2.0).timeout
	check(effects.find_children("*", "MeshInstance3D", false, false).is_empty(), "every slice of toast has cleaned itself up")
	check(effects.find_children("*", "CPUParticles3D", false, false).is_empty(), "and all the fire and smoke too")
	print("TOASTER MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
