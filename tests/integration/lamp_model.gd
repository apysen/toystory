extends SceneTree
## Lamp's 3D model in the real battle scene: it replaces the sprite card, its clips
## play and finish, and a Watchful intercept runs out in front of the ally, takes the
## hit without a second flinch, and walks back to Lamp's spot. His Arts play their
## own clips with their light (Flashbulb's hit lands without a Pole Strike swing,
## Guard Beam's beam and bubble, Spotlight's camera push-in and stage light), and
## every light cleans itself up.
## godot --headless --path . --script res://tests/integration/lamp_model.gd

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"

## A Battle Speed of 2x that never touches the player's saved settings.
class DoubleSpeed extends BattleSpeedSettings:
	func speed() -> float:
		return 2.0


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
	var lamp := b.field.find_unit("lamp")
	var card := view.card_of(lamp)
	var model: UnitModel = card.get_node_or_null("Model")
	check(model != null and model.visible, "Lamp shows its 3D model")
	check(not card.get_node("Card").visible, "and its sprite card is hidden")
	for anim in ["idle", "move", "attack", "hurt", "broken", "spotlight", "flashbulb", "guard_beam",
			"intercept_run", "intercept_guard"]:
		check(card.has_anim(anim), "the model has '%s'" % anim)
	for anim in ["art", "ready", "gaze_in", "gaze_out"]:
		check(not card.has_anim(anim), "and no '%s' clip" % anim)
	check(await _finishes(func() -> void: await card.play_once("attack"), 3.0), "attack plays through and finishes")
	check(model.current() == "idle", "and settles back into idle")
	check(await _finishes(func() -> void: await card.play_art("spotlight"), 3.0), "Spotlight plays its own clip")

	# Watchful: an enemy strikes an ally next to Lamp and Lamp takes the hit.
	var ally: Unit = null
	for u in b.player_units():
		if u != lamp:
			ally = u
			break
	var enemy: Unit = b.field.units.filter(func(u: Unit) -> bool: return u.faction == Defs.Faction.ENEMY)[0]
	ally.pos = lamp.pos + Vector2(lamp.radius + ally.radius + 0.1, 0)
	view.card_of(ally).position = BattleSpace.to_world(ally.pos)
	enemy.pos = ally.pos + Vector2(0, ally.radius + enemy.radius + 0.3)
	view.card_of(enemy).position = BattleSpace.to_world(enemy.pos)
	var home := card.position
	var events := [
		{"type": "strike", "attacker": enemy, "target": lamp, "hit": true, "crit": false, "damage": 3,
			"intercepted": true, "original": ally},
		{"type": "damage", "unit": lamp, "hp": lamp.hp - 3},
	]
	check(await _finishes(func() -> void: await view.event_player.play(events), 10.0),
		"a Watchful intercept plays through")
	check(card.position.distance_to(home) < 0.01, "Lamp is back on its own spot")
	check(not card.absorbed_hit, "the guard took the hit without a second flinch")

	# Timing: the strike connects on the model's contact frame, not after the clip.
	check(absf(card.contact_time("attack") - 0.45) < 0.01, "Pole Strike connects 0.45s into the swing")
	var sprite_unit: Unit = null
	for u in b.field.units:
		if not UnitModel.MODELS.has(u.sprite) and not UnitModel.MODELS.has(u.id):
			sprite_unit = u
			break
	check(sprite_unit != null and is_nan(view.card_of(sprite_unit).contact_time("attack")),
		"sprite units keep the old strike timing")

	# Arts: timings from the clips, then each plays through the real event player.
	check(absf(card.art_time("flashbulb", "flash") - 0.45) < 0.01, "Flashbulb pops 0.45s in")
	check(absf(card.art_time("guard_beam", "beam") - 0.367) < 0.01 and absf(card.art_time("guard_beam", "release") - 0.933) < 0.01,
		"Guard Beam's beam runs from 0.37s to 0.93s")
	check(absf(card.art_time("spotlight", "land") - 1.1) < 0.01, "Spotlight's light lands 1.1s in")
	var lights: ArtLights = view.event_player.lights
	check(lights != null, "the event player has the art lights")

	var seen := {}
	var lit := [0]
	var watching := [true]
	var watch_clips := func() -> void:
		while watching[0]:
			seen[model.current()] = true
			lit[0] = maxi(lit[0], lights.live_count())
			await process_frame
	watch_clips.call()

	ally.pos = lamp.pos + Vector2(1.2, 0)
	view.card_of(ally).position = BattleSpace.to_world(ally.pos)
	var beam_events := [{"type": "art", "unit": lamp, "art": "guard_beam", "name": "Guard Beam", "target": ally}]
	check(await _finishes(func() -> void: await view.event_player.play(beam_events), 6.0), "Guard Beam plays through")
	check(seen.has("guard_beam") and lit[0] >= 2, "with its own clip, a beam and a bubble (%d lights)" % lit[0])

	seen.clear()
	enemy.pos = lamp.pos + Vector2(0, lamp.radius + enemy.radius + 0.5)
	view.card_of(enemy).position = BattleSpace.to_world(enemy.pos)
	lamp.acted = false
	check(b.use_art(lamp, "flashbulb", Vector2(0, 1)), "Flashbulb resolves on the enemy in front")
	var flash_events := b.take_events()
	check(flash_events.any(func(e): return e.type == "strike" and e.attacker == lamp), "and strikes it")
	check(await _finishes(func() -> void: await view.event_player.play(flash_events), 8.0), "Flashbulb plays through")
	check(seen.has("flashbulb") and not seen.has("attack"), "its own clip shows the blow, no Pole Strike swing")

	seen.clear()
	lamp.acted = false
	var zoom := view.camera.distance
	check(b.use_art(lamp, "spotlight", ally.pos), "Spotlight resolves on the ally")
	check(await _finishes(func() -> void: await view.event_player.play(b.take_events()), 10.0), "Spotlight plays through")
	check(seen.has("spotlight") and lit[0] >= 4, "with its clip and its stage light (%d lights at once)" % lit[0])
	check(absf(view.camera.distance - zoom) < 0.05, "the camera eases back out after its push-in")
	watching[0] = false
	await create_timer(1.2).timeout
	check(lights.live_count() == 0, "every light has cleaned itself up (%d left)" % lights.live_count())

	# Enemy moves arrive as Arts too (the Captain's Cutting Line) and must play through.
	var cut := [{"type": "art", "unit": enemy, "art": "cutting_line", "name": "Cutting Line", "target": Vector2(1, 0)}]
	check(await _finishes(func() -> void: await view.event_player.play(cut), 5.0), "an enemy's Cutting Line plays through")

	# Battle Speed: playback runs faster, steering stays at real time.
	view.event_player.speed_settings = DoubleSpeed.new()
	var heal := [{"type": "heal", "unit": ally, "hp": ally.hp, "amount": 0}]
	var scale_seen := [0.0]
	var watch := func() -> void:
		await process_frame
		scale_seen[0] = Engine.time_scale
	watch.call()
	check(await _finishes(func() -> void: await view.event_player.play(heal), 5.0), "playback finishes")
	check(is_equal_approx(scale_seen[0], 2.0), "playback runs at the Battle Speed")
	check(is_equal_approx(Engine.time_scale, 1.0), "and the battle is back at real time after")
	print("LAMP MODEL: %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(1 if failures > 0 else 0)
