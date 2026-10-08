extends SceneTree
## Headless rule tests: godot --headless --path . --script res://tests/run_tests.gd

var failures := 0
var passes := 0


func _init() -> void:
	for m in get_method_list():
		if m.name.begins_with("test_"):
			call(m.name)
	print("\n%d passed, %d failed" % [passes, failures])
	quit(1 if failures > 0 else 0)


func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures += 1
		push_error("FAIL: " + msg)
		print("FAIL: " + msg)


func fresh(seed_value := 1) -> Battle:
	var b := Battle.new(UnderTheDesk.build_board(), seed_value)
	b.start()
	b.take_events()
	return b


func test_map_layout() -> void:
	var b := fresh()
	var vac := b.board.find_unit("vacuum")
	check(vac.occupies(Vector2i(2, 3)) and vac.occupies(Vector2i(1, 2)), "vacuum covers (1-2,2-3)")
	check(b.board.terrain_at(Vector2i(6, 3)) == Defs.Terrain.FULL_COVER, "desk leg is full cover")
	check(b.board.terrain_at(Vector2i(10, 7)) == Defs.Terrain.SPILL, "spill tile")
	check(b.board.find_unit("umbrella").faction == Defs.Faction.NEUTRAL, "umbrella starts neutral")


func test_type_triangle() -> void:
	check(Defs.type_relation(Defs.DmgType.SMASH, Defs.DmgType.PIERCE) == 1, "smash beats pierce")
	check(Defs.type_relation(Defs.DmgType.PIERCE, Defs.DmgType.BIND) == 1, "pierce beats bind")
	check(Defs.type_relation(Defs.DmgType.BIND, Defs.DmgType.SMASH) == 1, "bind beats smash")
	check(Defs.type_relation(Defs.DmgType.SMASH, Defs.DmgType.BIND) == -1, "smash loses to bind")
	check(Defs.type_relation(Defs.DmgType.NEUTRAL, Defs.DmgType.BIND) == 0, "neutral ignores triangle")


func test_damage_formula() -> void:
	var b := fresh()
	var lamp := b.board.find_unit("lamp")
	var pencil := b.board.find_unit("pencil_a")
	# Lamp Pow 8 + Might 4 - Def 3 = 9, Smash vs Pierce +20% -> 10.8 -> 11.
	var pv := Combat.preview(b.board, lamp, Vector2i(6, 2), pencil, pencil.pos, {"might": 4, "type": Defs.DmgType.SMASH})
	check(pv.damage == 11, "lamp vs pencil damage 11, got %d" % pv.damage)
	# Hit 85 + 14 - 16 + 15 = 98.
	check(pv.hit == 98, "lamp vs pencil hit 98, got %d" % pv.hit)
	check(pv.crit == 7, "crit = skill")


func test_movement_and_spill() -> void:
	var b := fresh()
	var stapler := b.board.find_unit("stapler")
	var opts := b.move_options(stapler)
	check(opts.has(Vector2i(4, 8)), "stapler reaches (4,8) with move 6")
	check(not opts.has(Vector2i(6, 3)), "can't stand on desk leg")
	# Spill: (9,6) costs 3 to enter.
	var u := b.board.find_unit("teacup")
	u.pos = Vector2i(8, 6)
	b.board.find_unit("rubber").pos = Vector2i(1, 10)
	var m := b.board.reach_map(u, u.pos, 3)
	check(m.has(Vector2i(9, 6)) and m[Vector2i(9, 6)].cost == 3, "spill entry costs 3")


func test_large_unit_pathing() -> void:
	var b := fresh()
	var vac := b.board.find_unit("vacuum")
	var opts := b.move_options(vac)
	for a in opts:
		for t in vac.tiles_at(a):
			check(b.board.terrain_at(t) != Defs.Terrain.FULL_COVER, "vacuum footprint avoids cover at %s" % t)
	check(not opts.has(Vector2i(5, 3)), "vacuum can't overlap desk leg (6,3)")


func test_line_of_sight() -> void:
	var b := fresh()
	# Desk leg at (6,3) blocks (5,3) -> (7,3).
	check(not b.board.has_los_tiles(Vector2i(5, 3), Vector2i(7, 3)), "desk leg blocks LOS")
	check(b.board.has_los_tiles(Vector2i(5, 2), Vector2i(7, 2)), "open row has LOS")


func test_noise_and_gaze() -> void:
	var b := fresh()
	var toaster := b.board.find_unit("toaster")
	b.noise = 5
	b.add_noise(2, toaster)
	check(b.gaze_active(), "gaze triggers at 6")
	check(b.noise == 1, "overflow kept (5+2-6=1), got %d" % b.noise)
	check(toaster.frozen, "acting unit frozen at attention point")
	var lamp := b.board.find_unit("lamp")
	check(lamp.frozen, "lamp at (3,2) inside 3x3 around (3,3)")
	var stapler := b.board.find_unit("stapler")
	check(not b.art_check(stapler, "pin").ok, "noise arts disabled during gaze")
	b.begin_player_phase()
	check(not b.gaze_active() and not toaster.frozen, "gaze ends at next player phase")


func test_quiet_art_during_gaze() -> void:
	var b := fresh()
	var cup := b.board.find_unit("teacup")
	cup.pos = Vector2i(5, 7)
	b.trigger_gaze(Vector2i(2, 2))
	check(b.art_check(cup, "steady_sip").ok, "steady sip usable outside gaze")
	check(b.use_art(cup, "steady_sip", cup), "steady sip resolves")
	check(cup.status.has("steady_sip"), "steady sip applied")


func test_frozen_blocks_and_untargetable() -> void:
	var b := fresh()
	var pencil := b.board.find_unit("pencil_a")
	b.trigger_gaze(pencil.pos)
	check(pencil.frozen, "pencil frozen")
	var lamp := b.board.find_unit("lamp")
	check(not b.can_target(lamp, pencil), "frozen units can't be attacked")
	var vac := b.board.find_unit("vacuum")
	check(not b.board.can_pass(lamp, pencil.pos), "frozen units block movement")


func test_robot_vacuum_expected_behavior() -> void:
	var b := fresh()
	var roomba := b.board.find_unit("roomba")
	b.trigger_gaze(roomba.pos)
	check(not roomba.frozen, "robot vacuum keeps moving under gaze")
	var start := roomba.pos
	EnemyAI.new(b).act(roomba)
	var hits := b.take_events().filter(func(e): return e.type == "strike")
	check(hits.is_empty(), "robot vacuum never attacks while gaze is active")
	check(roomba.pos != start, "robot vacuum repositions during gaze")


func test_push_collision() -> void:
	var b := fresh()
	var pencil := b.board.find_unit("pencil_a") # (7,3), desk leg at (6,3)
	var hp := pencil.hp
	b.forced_move(pencil, Vector2i(-1, 0), 2)
	check(pencil.pos == Vector2i(7, 3), "push into desk leg stops")
	check(pencil.hp == hp - 2, "collision = ceil(10 pct of 18) = 2, got %d" % (hp - pencil.hp))


func test_heavy_frame() -> void:
	var b := fresh()
	var cutter := b.board.find_unit("cutter")
	cutter.pos = Vector2i(8, 9)
	b.forced_move(cutter, Vector2i(-1, 0), 2)
	check(cutter.pos == Vector2i(7, 9), "captain pushed 1 tile instead of 2")


func test_suction_pulls() -> void:
	var b := fresh()
	var vac := b.board.find_unit("vacuum")
	var rubber := b.board.find_unit("rubber")
	vac.pos = Vector2i(3, 6)
	rubber.pos = Vector2i(7, 6)
	b.board.find_unit("lamp").pos = Vector2i(3, 1)
	check(b.art_targets(vac, "suction").has(rubber), "rubber in suction range")
	b.use_art(vac, "suction", rubber)
	check(rubber.pos == Vector2i(5, 6), "suction pulls next to vacuum, got %s" % rubber.pos)
	check(b.noise == 1, "suction +1 noise")


func test_recruit_umbrella() -> void:
	var b := fresh()
	var lamp := b.board.find_unit("lamp")
	var umb := b.board.find_unit("umbrella")
	lamp.pos = Vector2i(13, 3)
	lamp.moved = true
	check(b.talk_targets(lamp).has(umb), "lamp can talk to adjacent umbrella")
	b.talk(lamp, umb)
	check(umb.faction == Defs.Faction.PLAYER and not umb.can_activate(), "umbrella joins next phase")
	b.begin_player_phase()
	check(umb.can_activate(), "umbrella controllable next player phase")
	check(b.stars().recruit, "recruit star")


func test_cutting_line_telegraph_and_cancel() -> void:
	var b := fresh()
	var cutter := b.board.find_unit("cutter")
	var stapler := b.board.find_unit("stapler")
	stapler.pos = Vector2i(10, 10)
	var ai := EnemyAI.new(b)
	var lane := ai.best_lane(cutter)
	check(lane.dir == Vector2i(-1, 0), "captain aims at stapler on its row")
	b.add_telegraph(cutter, lane.tiles, lane.dir, EnemyAI.CUTTING_LINE_MIGHT)
	var fc := Forecast.for_destination(b, stapler, stapler.pos)
	check(fc.telegraph_damage > 0, "forecast includes telegraph damage")
	var hp := stapler.hp
	b.resolve_telegraph(cutter)
	check(stapler.hp < hp, "cutting line hits units in lane")
	# Displacing the captain cancels it.
	stapler.hp = stapler.max_hp
	b.add_telegraph(cutter, lane.tiles, lane.dir, EnemyAI.CUTTING_LINE_MIGHT)
	cutter.pos = Vector2i(13, 11)
	b.resolve_telegraph(cutter)
	check(stapler.hp == stapler.max_hp, "displaced captain's line is cancelled")


func test_forecast_threats() -> void:
	var b := fresh()
	var stapler := b.board.find_unit("stapler")
	var safe := Forecast.for_destination(b, stapler, Vector2i(1, 1))
	check(safe.threats.is_empty() and safe.risk == "Safe", "back corner is safe, got %s" % safe.risk)
	var hot := Forecast.for_destination(b, stapler, Vector2i(8, 5))
	check(hot.threats.size() >= 2, "middle of the map has multiple threats")
	check(hot.predicted_hp < stapler.hp, "predicted HP drops")
	check(stapler.pos == Vector2i(4, 2), "forecast restores position")


func test_full_enemy_phase_runs() -> void:
	for s in [1, 2, 3, 4, 5]:
		var b := fresh(s)
		for i in 10:
			if b.phase != Defs.Phase.PLAYER:
				break
			b.end_player_phase()
		check(b.turn >= 2, "enemy phases run (seed %d)" % s)


func test_basic_attack_and_counter() -> void:
	var b := fresh()
	var lamp := b.board.find_unit("lamp")
	var pencil := b.board.find_unit("pencil_a")
	b.commit_move(lamp, Vector2i(7, 2))
	check(b.basic_targets(lamp).has(pencil), "pencil adjacent")
	b.attack(lamp, pencil)
	var ev := b.take_events().filter(func(e): return e.type == "strike")
	check(ev.size() >= 1, "strike happened")
	check(lamp.acted, "lamp done")


func test_destructible_box() -> void:
	var b := fresh()
	var toaster := b.board.find_unit("toaster")
	toaster.pos = Vector2i(8, 5)
	check(b.object_targets(toaster).has(Vector2i(8, 7)), "box in range 2")
	b.attack_object(toaster, Vector2i(8, 7))
	check(not b.board.objects.has(Vector2i(8, 7)), "15 damage destroys 12 HP box")
