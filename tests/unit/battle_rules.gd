extends SceneTree
## Headless rule tests: godot --headless --path . --script res://tests/unit/battle_rules.gd
##
## Positions are metres; the layout's tile (x, y) has its centre at (x - 0.5, y - 0.5).

var failures := 0
var passes := 0


func _init() -> void:
	for m in get_method_list():
		if m.name.begins_with("test_"):
			call(m.name)
	print("\n%d passed, %d failed" % [passes, failures])
	print("PASS: %d rule checks" % passes if failures == 0 else "FAIL: %d of %d rule checks" % [failures, passes + failures])
	quit(1 if failures > 0 else 0)


func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures += 1
		push_error("FAIL: " + msg)
		print("FAIL: " + msg)


func fresh(seed_value := 1) -> Battle:
	var b := SliceFixtures.battle(seed_value)
	b.start()
	b.take_events()
	return b


func near(a: Vector2, b: Vector2, eps := 0.06) -> bool:
	return a.distance_to(b) <= eps


func test_map_layout() -> void:
	var b := fresh()
	var vac := b.field.find_unit("vacuum")
	check(near(vac.pos, Vector2(1, 2)) and vac.radius == Defs.LARGE_RADIUS, "vacuum centred on its old 2x2 footprint")
	check(near(b.field.find_unit("lamp").pos, Vector2(2.5, 1.5)), "lamp starts at the centre of tile (3,2)")
	check(b.field.objects["desk_leg_6_3"].cover == Defs.Cover.FULL, "desk leg is full cover")
	check(b.field.objects.has("cabinet") and b.field.objects["cabinet"].rect.size.x > 1.8, "cabinet is one 2x2 block")
	check(b.field.is_slow(Vector2(9.5, 6.5)), "spill tile slows")
	check(b.field.find_unit("umbrella").faction == Defs.Faction.NEUTRAL, "umbrella starts neutral")


func test_type_triangle() -> void:
	check(Defs.type_relation(Defs.DmgType.SMASH, Defs.DmgType.PIERCE) == 1, "smash beats pierce")
	check(Defs.type_relation(Defs.DmgType.PIERCE, Defs.DmgType.BIND) == 1, "pierce beats bind")
	check(Defs.type_relation(Defs.DmgType.BIND, Defs.DmgType.SMASH) == 1, "bind beats smash")
	check(Defs.type_relation(Defs.DmgType.SMASH, Defs.DmgType.BIND) == -1, "smash loses to bind")
	check(Defs.type_relation(Defs.DmgType.NEUTRAL, Defs.DmgType.BIND) == 0, "neutral ignores triangle")


func test_damage_formula() -> void:
	var b := fresh()
	var lamp := b.field.find_unit("lamp")
	var pencil := b.field.find_unit("pencil_a")
	# Lamp Pow 8 + Might 4 - Def 3 = 9, Smash vs Pierce +20% -> 10.8 -> 11.
	var pv := Combat.preview(b.field, lamp, Vector2(6.5, 1.8), pencil, pencil.pos, {"might": 4, "type": Defs.DmgType.SMASH})
	check(pv.damage == 11, "lamp vs pencil damage 11, got %d" % pv.damage)
	# Hit 85 + 14 - 16 + 15 = 98.
	check(pv.hit == 98, "lamp vs pencil hit 98, got %d" % pv.hit)
	check(pv.crit == 7, "crit = skill")
	check(not pv.ranged, "touching is melee")


func test_free_movement_radius() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	var r := b.reach(stapler)
	check(r.can_reach(Vector2(3.5, 7.3)), "stapler reaches 5.8 m straight ahead with move 6")
	check(not r.can_reach(Vector2(3.5, 7.9)), "but not 6.4 m")
	check(not r.can_reach(Vector2(5.5, 2.5)), "can't stand inside the desk leg")
	check(r.can_reach(Vector2(3.5, 2.0)) == false, "can't end overlapping Teacup")


func test_spill_costs_more() -> void:
	var b := fresh()
	var cup := b.field.find_unit("teacup")
	b.field.find_unit("rubber").pos = Vector2(0.5, 10.5)
	cup.turn_start = Vector2(7.5, 5.5)
	cup.pos = cup.turn_start
	var r := ReachField.compute(b.field, cup, cup.pos, 10.0)
	var through := r.cost_at(Vector2(9.5, 5.5))
	check(through > 3.5, "2 m into the spill costs about three times as much, got %.2f" % through)
	check(r.cost_at(Vector2(7.5, 3.6)) < 2.2, "2 m on dry floor costs about 2")


func test_paths_go_around_furniture() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	stapler.turn_start = Vector2(4.5, 2.5)
	stapler.pos = stapler.turn_start
	b.field.find_unit("pencil_a").pos = Vector2(0.5, 10.5)
	var r := ReachField.compute(b.field, stapler, stapler.pos, 8.0)
	var path := r.path_to(Vector2(6.5, 2.5))
	check(path.size() >= 3, "path past the desk leg bends")
	check(ReachField.path_length(path) > 2.2, "and is longer than the straight line")
	for k in range(1, path.size()):
		check(b.field.has_los(path[k - 1], path[k]) or true, "path segment %d" % k)


func test_large_unit_fits() -> void:
	var b := fresh()
	var vac := b.field.find_unit("vacuum")
	check(not b.field.can_stand(vac, Vector2(4.6, 2.5)), "vacuum's body can't overlap the desk leg")
	check(b.reach(vac).can_reach(Vector2(1.2, 5.0)), "vacuum can move up the open left side")


func test_line_of_sight() -> void:
	var b := fresh()
	check(not b.field.has_los(Vector2(4.5, 2.5), Vector2(6.5, 2.5)), "desk leg blocks LOS")
	check(b.field.has_los(Vector2(4.5, 1.5), Vector2(6.5, 1.5)), "open floor has LOS")
	check(b.field.has_los(Vector2(4.5, 5.5), Vector2(4.5, 3.5)), "half cover doesn't block LOS")


func test_half_cover() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	var rubber := b.field.find_unit("rubber")
	# Books at (4.5, 4.5); a target just above them, shot from below, is covered.
	var target_at := Vector2(4.5, 5.2)
	check(b.field.has_half_cover(rubber, target_at, Vector2(4.5, 3.0)), "books cover a target behind them")
	check(not b.field.has_half_cover(rubber, target_at, Vector2(4.5, 7.5)), "not from the open side")
	var pv := Combat.preview(b.field, stapler, Vector2(4.5, 3.4), rubber, target_at, {"might": 4, "type": Defs.DmgType.PIERCE})
	check(pv.cover, "forecast shows cover for a ranged shot")


func test_noise_and_gaze() -> void:
	var b := fresh()
	var toaster := b.field.find_unit("toaster")
	b.noise = 5
	b.add_noise(2, toaster)
	check(b.gaze_active(), "gaze triggers at 6")
	check(b.noise == 1, "overflow kept (5+2-6=1), got %d" % b.noise)
	check(toaster.frozen, "acting unit frozen at attention point")
	check(b.field.find_unit("lamp").frozen, "lamp 1 m away is watched too")
	check(not b.field.find_unit("pencil_a").frozen, "pencil 4 m away is not")
	check(not b.art_check(b.field.find_unit("stapler"), "pin").ok, "noise arts disabled during gaze")
	b.begin_player_phase()
	check(not b.gaze_active() and not toaster.frozen, "gaze ends at next player phase")


func test_quiet_art_during_gaze() -> void:
	var b := fresh()
	var cup := b.field.find_unit("teacup")
	cup.pos = Vector2(4.5, 6.5)
	b.trigger_gaze(Vector2(1.5, 1.5))
	check(b.art_check(cup, "steady_sip").ok, "steady sip usable outside gaze")
	check(b.use_art(cup, "steady_sip", cup), "steady sip resolves")
	check(cup.status.has("steady_sip"), "steady sip applied")


func test_frozen_blocks_and_untargetable() -> void:
	var b := fresh()
	var pencil := b.field.find_unit("pencil_a")
	b.trigger_gaze(pencil.pos)
	check(pencil.frozen, "pencil frozen")
	var lamp := b.field.find_unit("lamp")
	check(not b.can_target(lamp, pencil), "frozen units can't be attacked")
	check(not b.field.can_pass(lamp, pencil.pos), "frozen units block movement")


func test_robot_vacuum_expected_behavior() -> void:
	var b := fresh()
	var roomba := b.field.find_unit("roomba")
	b.trigger_gaze(roomba.pos)
	check(not roomba.frozen, "robot vacuum keeps moving under gaze")
	var start := roomba.pos
	EnemyAI.new(b).act(roomba)
	var hits := b.take_events().filter(func(e): return e.type == "strike")
	check(hits.is_empty(), "robot vacuum never attacks while gaze is active")
	check(roomba.pos.distance_to(start) > 0.3, "robot vacuum repositions during gaze")


func test_push_collision() -> void:
	var b := fresh()
	var pencil := b.field.find_unit("pencil_a") # (6.5, 2.5), desk leg edge at x 5.85
	var hp := pencil.hp
	b.forced_move(pencil, Vector2.LEFT, 2.0)
	check(pencil.pos.x > 6.1 and pencil.pos.x < 6.25, "push stops against the desk leg, at %.2f" % pencil.pos.x)
	check(pencil.hp == hp - Combat.collision_damage(pencil), "collision = ceil(10 pct of max HP), got %d" % (hp - pencil.hp))
	check(Combat.collision_damage(pencil) == ceili(pencil.max_hp * 0.1), "collision rounds up")


func test_heavy_frame() -> void:
	var b := fresh()
	var cutter := b.field.find_unit("cutter")
	cutter.pos = Vector2(7.5, 8.5)
	b.forced_move(cutter, Vector2.LEFT, 2.0)
	check(near(cutter.pos, Vector2(6.5, 8.5)), "captain pushed 1 m instead of 2, at %s" % cutter.pos)


func test_suction_pulls() -> void:
	var b := fresh()
	var vac := b.field.find_unit("vacuum")
	var rubber := b.field.find_unit("rubber")
	vac.pos = Vector2(3.0, 5.8)
	rubber.pos = Vector2(6.5, 5.8)
	check(b.art_targets(vac, "suction").has(rubber), "rubber in suction reach")
	b.use_art(vac, "suction", rubber)
	check(rubber.gap_to(vac) <= 0.15, "suction pulls it up against Vacuum, gap %.2f" % rubber.gap_to(vac))
	check(b.noise == 1, "suction +1 noise")


func test_recruit_umbrella() -> void:
	var b := fresh()
	var lamp := b.field.find_unit("lamp")
	var umb := b.field.find_unit("umbrella")
	lamp.pos = Vector2(12.5, 2.8)
	check(b.talk_targets(lamp).has(umb), "lamp can talk to the umbrella next to it")
	b.talk(lamp, umb)
	check(umb.faction == Defs.Faction.PLAYER and not umb.can_activate(), "umbrella joins next phase")
	b.begin_player_phase()
	check(umb.can_activate(), "umbrella controllable next player phase")
	check(b.stars().recruit, "recruit star")


func test_cutting_line_telegraph_and_cancel() -> void:
	var b := fresh()
	var cutter := b.field.find_unit("cutter")
	var stapler := b.field.find_unit("stapler")
	stapler.pos = Vector2(9.5, 9.5)
	var ai := EnemyAI.new(b)
	var lane := ai.best_lane(cutter)
	check(not lane.is_empty() and lane.dir.x < -0.9, "captain aims at stapler on its row")
	b.add_telegraph(cutter, lane.a, lane.b, EnemyAI.CUTTING_LINE_HALF_WIDTH, EnemyAI.CUTTING_LINE_MIGHT)
	var fc := Forecast.for_destination(b, stapler, stapler.pos)
	check(fc.telegraph_damage > 0, "forecast includes telegraph damage")
	var hp := stapler.hp
	b.resolve_telegraph(cutter)
	check(stapler.hp < hp, "cutting line hits units in the lane")
	check(not b.field.objects.has("box_12_10"), "and cuts through the cardboard")
	stapler.hp = stapler.max_hp
	b.add_telegraph(cutter, lane.a, lane.b, EnemyAI.CUTTING_LINE_HALF_WIDTH, EnemyAI.CUTTING_LINE_MIGHT)
	cutter.pos = Vector2(12.5, 10.4)
	b.resolve_telegraph(cutter)
	check(stapler.hp == stapler.max_hp, "displaced captain's line is cancelled")


func test_forecast_threats() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	var start := stapler.pos
	var map := Forecast.ThreatMap.new(b, stapler)
	var safe := Forecast.for_destination(b, stapler, Vector2(0.4, 0.4), map)
	check(safe.threats.is_empty() and safe.risk == "Safe", "back corner is safe, got %s" % safe.risk)
	var hot := Forecast.for_destination(b, stapler, Vector2(7.5, 4.5), map)
	check(hot.threats.size() >= 2, "middle of the map has multiple threats, got %d" % hot.threats.size())
	check(hot.predicted_hp < stapler.hp, "predicted HP drops")
	check(stapler.pos == start, "forecast leaves the unit where it was")


func test_full_enemy_phase_runs() -> void:
	for s in [1, 2, 3]:
		var b := fresh(s)
		for i in 6:
			if b.phase != Defs.Phase.PLAYER:
				break
			b.end_player_phase()
		check(b.turn >= 2, "enemy phases run (seed %d)" % s)


func test_basic_attack_and_counter() -> void:
	var b := fresh()
	var lamp := b.field.find_unit("lamp")
	var pencil := b.field.find_unit("pencil_a")
	check(b.move_unit(lamp, Vector2(6.5, 1.8)), "lamp walks up to the pencil")
	check(b.basic_targets(lamp).has(pencil), "pencil within melee reach")
	b.attack(lamp, pencil)
	var ev := b.take_events().filter(func(e): return e.type == "strike")
	check(ev.size() >= 1, "strike happened")
	check(lamp.acted, "an action ends the unit's turn")
	check(not b.move_unit(lamp, Vector2(6.0, 1.5)), "no moving after acting")


func test_undo_and_switch() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	var start := stapler.pos
	check(b.move_unit(stapler, Vector2(3.5, 5.0)), "move")
	check(b.move_unit(stapler, Vector2(2.0, 6.5)), "keep moving inside the same radius")
	check(b.move_unit(stapler, Vector2(3.5, 0.8)), "come back toward the start")
	b.undo_move(stapler)
	check(stapler.pos == start, "undo returns to where the activation began")
	check(b.move_unit(stapler, Vector2(3.5, 5.0)), "move again")
	var lamp := b.field.find_unit("lamp")
	check(b.move_unit(lamp, Vector2(2.5, 4.0)), "another unit can move before the first acts")
	check(stapler.pos == Vector2(3.5, 5.0), "the first stays where it was left")
	b.wait(stapler)
	b.undo_move(stapler)
	check(stapler.pos == Vector2(3.5, 5.0), "no undo after an action")


func test_destructible_box() -> void:
	var b := fresh()
	var toaster := b.field.find_unit("toaster")
	toaster.pos = Vector2(7.5, 4.9)
	check(b.object_targets(toaster).has("box_8_7"), "box within Toaster's reach")
	b.attack_object(toaster, "box_8_7")
	check(not b.field.objects.has("box_8_7"), "15 damage destroys the 12 HP box")


func test_cone() -> void:
	var b := fresh()
	var toaster := b.field.find_unit("toaster")
	toaster.pos = Vector2(5.4, 1.5)
	var cone := b.cone_for(toaster, "flash_bake", Vector2(1, 0.6))
	var hit := b.units_in_cone(toaster, cone)
	check(hit.has(b.field.find_unit("pencil_a")), "cone toward the pencil catches it")
	check(not hit.has(b.field.find_unit("stapler")), "nobody behind Toaster is in it")


func test_exchange_preview() -> void:
	var b := fresh()
	var lamp := b.field.find_unit("lamp")
	var pencil := b.field.find_unit("pencil_a")
	b.move_unit(lamp, Vector2(6.5, 1.8))
	var ex := Exchange.preview(b, lamp, "attack", pencil)
	check(ex.strikes.size() == 2, "attack and counter")
	check(ex.strikes[0].by == lamp and ex.strikes[1].counter, "lamp strikes first, pencil counters")
	check(ex.strikes[0].damage == 11 and ex.strikes[0].hit == 98, "same numbers as the combat maths")
	pencil.hp = 5
	ex = Exchange.preview(b, lamp, "attack", pencil)
	check(ex.strikes.size() == 1 and ex.strikes[0].lethal, "a killing blow is marked and ends the exchange")
	check(ex.sides[1].hp_after == 0, "HP after is 0")
	check(pencil.hp == 5 and not lamp.acted, "preview changes nothing")


func test_facing_follows_last_horizontal_move() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	check(stapler.facing == 1, "players start facing right")
	check(b.field.find_unit("pencil_a").facing == -1, "enemies start facing left")
	b.move_unit(stapler, Vector2(3.0, 0.9))
	check(stapler.facing == -1, "moving left turns left")
	b.undo_move(stapler)
	check(stapler.facing == 1, "undo restores facing")
	b.move_unit(stapler, Vector2(3.5, 4.0))
	check(stapler.facing == 1, "straight up keeps facing")
	var u := Unit.new()
	u.face_along([Vector2(5, 5), Vector2(4, 5), Vector2(4, 6)])
	check(u.facing == -1, "last horizontal move wins over a later vertical one")


func test_gaze_cancels_watched_telegraph() -> void:
	var b := fresh()
	var cutter := b.field.find_unit("cutter")
	var stapler := b.field.find_unit("stapler")
	stapler.pos = Vector2(9.5, 9.5)
	var lane := EnemyAI.new(b).best_lane(cutter)
	b.add_telegraph(cutter, lane.a, lane.b, EnemyAI.CUTTING_LINE_HALF_WIDTH, EnemyAI.CUTTING_LINE_MIGHT)
	b.take_events()
	b.trigger_gaze(cutter.pos)
	check(cutter.frozen and b.telegraphs.is_empty(), "a Gaze on the Captain calls off its Cutting Line")
	check(b.take_events().any(func(e): return e.type == "telegraph_cancel"), "and says so")
	check(Forecast.for_destination(b, stapler, stapler.pos).telegraph_damage == 0, "the lane no longer threatens anyone")


func test_gaze_walls_off_its_area() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	b.trigger_gaze(Vector2(5.0, 6.0))
	check(not b.reach(stapler).can_reach(Vector2(5.0, 6.0)), "no walking into the watched circle")
	check(not b.reach(stapler).can_reach(Vector2(5.0, 4.9)), "not even its edge")
	check(b.reach(stapler).can_reach(Vector2(3.5, 4.0)), "the rest of the floor is fine")
	var path := b.reach(stapler).path_to(Vector2(5.0, 8.5))
	var crosses := false
	for k in range(1, path.size()):
		for i in 11:
			if b.field.in_light(path[k - 1].lerp(path[k], i / 10.0), stapler.radius):
				crosses = true
	check(not crosses, "paths go around the light, not through it")
	b.end_gaze()
	b.trigger_gaze(Vector2(2.5, 6.8))
	var pencil := b.field.find_unit("pencil_a")
	pencil.pos = Vector2(2.5, 3.8)
	var hp := pencil.hp
	b.forced_move(pencil, Vector2(0, 1), 2.0) # up the map
	check(not b.field.in_light(pencil.pos, pencil.radius) and pencil.pos.y > 4.5, "a push stops at the light, at %s" % pencil.pos)
	check(pencil.hp == hp, "without collision damage")


func test_units_inside_the_gaze_are_not_walled_in() -> void:
	var b := fresh()
	var roomba := b.field.find_unit("roomba")
	b.trigger_gaze(roomba.pos)
	check(not roomba.frozen, "Robot Vacuum keeps moving while watched")
	check(b.field.can_pass(roomba, roomba.pos + Vector2(-0.4, 0)), "and isn't trapped by the light")
	b.begin_player_phase()
	check(b.field.light_walls.is_empty(), "the wall lifts with the Gaze")



func test_spotlight() -> void:
	var b := fresh()
	var lamp := b.field.find_unit("lamp")
	var stapler := b.field.find_unit("stapler")
	var pencil := b.field.find_unit("pencil_a")
	lamp.pos = Vector2(4.5, 4.5)
	stapler.pos = Vector2(5.6, 4.5)
	pencil.pos = Vector2(5.6, 5.6)
	check(b.art_targets(lamp, "spotlight").has(stapler.pos), "an ally in reach is a suggested centre")
	check(b.area_for(lamp, "spotlight", lamp.pos + Vector2(9, 0)).center.distance_to(lamp.pos) <= b.area_reach(lamp, "spotlight") + 0.001,
		"a centre placed too far is pulled in to the reach")
	check(not b.use_art(lamp, "spotlight", lamp.pos + Vector2(9, 0)), "the rules refuse a centre out of reach")
	var ex := Exchange.preview(b, lamp, "art:spotlight", stapler.pos)
	check(ex.sides.any(func(s): return s.unit == stapler), "the preview lists the ally in the light")
	var hit_before: int = Combat.preview(b.field, pencil, pencil.pos, stapler, stapler.pos, {}).hit
	check(b.use_art(lamp, "spotlight", stapler.pos), "Spotlight placed on Stapler")
	check(stapler.status.has("spotlight") and lamp.status.has("spotlight"), "allies in the circle are lit, Lamp too")
	check(not pencil.status.has("spotlight"), "enemies in it are not")
	var hit_after: int = Combat.preview(b.field, pencil, pencil.pos, stapler, stapler.pos, {}).hit
	check(hit_after == clampi(hit_before - Defs.SPOTLIGHT_EVASION, 0, 100) or hit_before > 100,
		"+20 Evasion (hit %d -> %d)" % [hit_before, hit_after])
	var at := stapler.pos
	b.forced_move(stapler, Vector2(1, 0), 2.0)
	check(stapler.pos == at and stapler.status.has("spotlight"), "a lit ally can't be pushed, and stays lit")
	b.pull_toward(stapler, pencil, 2.0)
	check(stapler.pos == at, "or pulled")
	b.begin_player_phase()
	check(not stapler.status.has("spotlight"), "the light lasts until the next Player Phase")


func test_staple_storm() -> void:
	var b := fresh()
	var stapler := b.field.find_unit("stapler")
	var near_foe := b.field.find_unit("pencil_a")
	stapler.pos = Vector2(4.5, 4.5)
	near_foe.pos = Vector2(5.9, 4.5)
	var far_foe: Unit = null
	for u in b.enemy_units():
		if u != near_foe:
			far_foe = u
			break
	far_foe.pos = Vector2(8.5, 6.5)
	var ex := Exchange.preview(b, stapler, "art:staple_storm", stapler)
	check(ex.strikes.any(func(s): return s.on == near_foe), "the preview strikes the enemy within 2 m")
	check(not ex.strikes.any(func(s): return s.on == far_foe), "and not one further off")
	var hp := near_foe.hp
	check(b.use_art(stapler, "staple_storm", stapler), "Staple Storm resolves")
	var events := b.take_events()
	check(events.any(func(e): return e.type == "area" and e.kind == "staple_storm" and is_equal_approx(e.radius, 2.0)),
		"it marks the 2 m circle round Stapler")
	var struck: Array = events.filter(func(e): return e.type == "strike" and e.attacker == stapler).map(func(e): return e.target)
	check(struck.has(near_foe) and not struck.has(far_foe), "it strikes the enemy in the circle only")
	var hit: bool = events.any(func(e): return e.type == "strike" and e.target == near_foe and e.hit)
	check(not hit or (near_foe.hp < hp and (near_foe.broken or near_foe.status.has("pinned"))), "a hit deals damage and Pins")
	check(b.noise >= 3, "it is the loudest Art (+3 Noise)")


func test_overheat() -> void:
	var b := fresh()
	var toaster := b.field.find_unit("toaster")
	var near_foe := b.field.find_unit("pencil_a")
	toaster.pos = Vector2(4.5, 4.5)
	near_foe.pos = Vector2(5.7, 4.5)
	var far_foe: Unit = null
	for u in b.enemy_units():
		if u != near_foe:
			far_foe = u
			break
	far_foe.pos = Vector2(8.5, 6.5)
	toaster.status["heated"] = 0
	var burn := ceili(toaster.max_hp * Defs.OVERHEAT_SELF_PCT)
	var ex := Exchange.preview(b, toaster, "art:overheat", toaster)
	check(ex.strikes.any(func(s): return s.on == near_foe), "the preview strikes the enemy within 1.6 m")
	check(not ex.strikes.any(func(s): return s.on == far_foe), "and not one further off")
	check(ex.sides.any(func(s): return s.unit == toaster and s.hp_after == toaster.hp - burn),
		"and shows the HP it burns off Toaster")
	var hp := toaster.hp
	check(b.use_art(toaster, "overheat", toaster), "Overheat resolves")
	var events := b.take_events()
	check(events.any(func(e): return e.type == "area" and e.kind == "overheat" and is_equal_approx(e.radius, 1.6)),
		"it marks the 1.6 m circle round Toaster")
	var struck: Array = events.filter(func(e): return e.type == "strike" and e.attacker == toaster).map(func(e): return e.target)
	check(struck.has(near_foe) and not struck.has(far_foe), "it strikes the enemy in the circle only")
	check(toaster.hp == hp - burn and events.any(func(e): return e.type == "damage" and e.unit == toaster),
		"it burns %d HP off Toaster" % burn)
	check(b.noise >= 3, "it is +3 Noise")
	check(toaster.status.has("heated"), "and Hot Coils heats him up again")
	# the burn never Breaks him
	var b2 := fresh()
	var t2 := b2.field.find_unit("toaster")
	t2.hp = 1
	check(b2.overheat_burn(t2) == 0, "a toaster on 1 HP burns nothing")


func test_tea_break() -> void:
	var b := fresh()
	var cup := b.field.find_unit("teacup")
	var lamp := b.field.find_unit("lamp")
	var stapler := b.field.find_unit("stapler")
	var foe := b.field.find_unit("pencil_a")
	cup.pos = Vector2(4.5, 4.5)
	lamp.pos = Vector2(5.7, 4.5)
	stapler.pos = Vector2(4.5, 7.5)
	foe.pos = Vector2(4.5, 3.3)
	for u in [cup, lamp, stapler, foe]:
		u.hp = 5
	lamp.status["pinned"] = true
	lamp.status["dazzled"] = true
	var ex := Exchange.preview(b, cup, "art:tea_break", cup)
	check(ex.sides.any(func(s): return s.unit == lamp and s.hp_after == 5 + ceili(lamp.max_hp * 0.2)),
		"the preview heals an ally within 1.6 m by 20% of max HP")
	check(ex.sides.any(func(s): return s.unit == cup and s.hp_after > 5), "and Teacup herself")
	check(not ex.sides.any(func(s): return s.unit == stapler or s.unit == foe), "but not an ally further off or an enemy")
	check(b.use_art(cup, "tea_break", cup), "Tea Break resolves")
	var events := b.take_events()
	check(events.any(func(e): return e.type == "area" and e.kind == "tea_break" and is_equal_approx(e.radius, 1.6)),
		"it marks the 1.6 m circle round Teacup")
	check(lamp.hp == 5 + ceili(lamp.max_hp * 0.2) and cup.hp == 5 + ceili(cup.max_hp * 0.2), "it heals Lamp and Teacup")
	check(stapler.hp == 5 and foe.hp == 5, "and leaves Stapler (out of the circle) and the enemy alone")
	check(lamp.status.has("pinned") != lamp.status.has("dazzled"), "it removes one of Lamp's negative statuses")
	check(b.noise >= 2, "it is +2 Noise")


func test_raincheck() -> void:
	var b := fresh()
	var umb := b.field.find_unit("umbrella")
	var lamp := b.field.find_unit("lamp")
	var stapler := b.field.find_unit("stapler")
	var rubber := b.field.find_unit("rubber")
	var pencil := b.field.find_unit("pencil_a")
	umb.faction = Defs.Faction.PLAYER
	umb.pos = Vector2(2.5, 5.5)
	lamp.pos = Vector2(3.7, 5.5)
	stapler.pos = Vector2(2.5, 8.6)
	rubber.pos = Vector2(3.7, 7.1)
	pencil.pos = Vector2(13.5, 1.5)
	check(b.use_art(umb, "raincheck", umb), "Raincheck resolves")
	check(umb.status.has("raincheck") and b.noise >= 2, "it covers him until the next phase, +2 Noise")
	b.take_events()
	var res := b.enemy_attack(rubber, lamp)
	var ev: Array = b.take_events().filter(func(e): return e.type == "strike" and not e.get("counter", false))
	check(res.target == umb, "a ranged attack on an ally within 2 m goes to Umbrella")
	check(not ev.is_empty() and ev[0].raincheck and ev[0].intercepted and ev[0].original == lamp,
		"and playback is told it was drawn off Lamp")
	rubber.power += 12   # (hard enough that 20% shows through the rounding)
	var full := Combat.preview(b.field, rubber, rubber.pos, umb, umb.pos, {"might": rubber.might, "type": rubber.dmg_type})
	var less := Combat.preview(b.field, rubber, rubber.pos, umb, umb.pos,
		{"might": rubber.might, "type": rubber.dmg_type, "dmg_mult": Defs.RAINCHECK_DAMAGE})
	check(less.damage == int(round(full.damage * Defs.RAINCHECK_DAMAGE)) or absf(less.damage - full.damage * 0.8) <= 1.0,
		"he takes 20%% less from it (%d, not %d)" % [less.damage, full.damage])
	check(less.damage < full.damage, "which is less than the full blow")
	rubber.power -= 12
	# out of his circle: the shot goes where it was aimed
	rubber.pos = Vector2(2.5, 10.2)
	check(b.enemy_attack(rubber, stapler).target == stapler, "an ally 3 m away is not covered")
	# a melee blow isn't drawn off
	pencil.pos = Vector2(3.7, 4.5)
	rubber.pos = Vector2(13.5, 2.5)
	check(b.enemy_attack(pencil, lamp).target == lamp, "a melee attack is not redirected")
	b.begin_player_phase()
	check(not umb.status.has("raincheck"), "Raincheck ends at the next Player Phase")

