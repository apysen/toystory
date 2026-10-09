extends SceneTree
## Lamp's 3D model in the real battle scene: it replaces the sprite card, its clips
## play and finish, and a Watchful intercept runs out in front of the ally, takes the
## hit without a second flinch, and walks back to Lamp's spot.
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
	for anim in ["idle", "move", "attack", "hurt", "broken", "spotlight", "intercept_run", "intercept_guard"]:
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
