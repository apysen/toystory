class_name EventPlayer
extends Node

## Plays back the events a `Battle` produced (see `Battle.take_events`) as movement,
## animation, effects, sound and log lines. The rules have already resolved by the
## time anything here runs; playback only shows what happened.

## Projectile effect each ranged attacker fires.
const PROJECTILES := {"stapler": "staple_shot", "toaster": "toast", "teacup": "steam_curl"}

@export_group("Collaborators")
@export var board_view: BoardView
@export var camera: BattleCamera
@export var effects: EffectsLayer
@export var audio: BattleAudio
@export var hud: BattleHud
@export var dialogue: DialogueBox

@export_group("Timing")
## Seconds per tile when a unit walks.
@export var step_seconds := 0.11
## Seconds per tile when a unit is pushed or pulled.
@export var shove_seconds := 0.07
@export var lunge_pixels := 10.0
@export var after_strike_seconds := 0.18
@export var area_flash_seconds := 0.3

var _battle: Battle


func setup(b: Battle) -> void:
	_battle = b


func play(events: Array) -> void:
	for e in events:
		await _play_one(e)
		_sync()


func _sync() -> void:
	board_view.sync_units()
	board_view.redraw()
	hud.refresh()


func _play_one(e: Dictionary) -> void:
	match e.type:
		"move", "displace":
			if _battle.phase == Defs.Phase.ENEMY:
				await camera.follow(board_view.unit_center(e.unit, e.unit.pos), Defs.TILE_SIZE)
			var v := board_view.view_of(e.unit)
			var tw := create_tween()
			var dur := step_seconds if e.type == "move" else shove_seconds
			for p in e.path.slice(1):
				tw.tween_property(v, "position", board_view.foot_point(e.unit, p), dur)
			if e.type == "move":
				v.set_moving(true)
				v.apply_facing()
			await tw.finished
			v.set_moving(false)
		"teleport":
			board_view.place(e.unit)
		"strike":
			await _strike(e)
		"damage":
			var v := board_view.view_of(e.unit)
			v.shown_hp = e.hp
			v.queue_redraw()
			# The hurt animation has its own baked flash; tint only units without one.
			if v.has_anim("hurt"):
				if v.sprite.animation != "hurt":
					v.play_once("hurt")
			else:
				var tw := create_tween()
				tw.tween_property(v, "modulate", Color(1, 0.4, 0.4), 0.06)
				tw.tween_property(v, "modulate", Color.WHITE, 0.12)
				await tw.finished
		"heal":
			var v := board_view.view_of(e.unit)
			v.shown_hp = e.hp
			v.queue_redraw()
			audio.play("heal")
			effects.burst("heal_sparkle", v.position + Vector2(0, -56))
			effects.float_text(v.position + Vector2(0, -90), "+%d" % e.amount, Color("80ff90"))
			hud.log_line("%s recovers %d HP." % [e.unit.name, e.amount])
			await get_tree().create_timer(0.25, false).timeout
		"broken":
			hud.log_line("%s is Broken." % e.unit.name)
			audio.play("broken")
			await board_view.view_of(e.unit).play_broken()
		"collision":
			hud.log_line("%s collides!" % e.unit.name)
			audio.play("collision")
		"art":
			hud.log_line("%s uses %s." % [e.unit.name, e.name])
			audio.play(BattleAudio.ART_SOUNDS.get(e.art, ""))
			var cv := board_view.view_of(e.unit)
			cv.play_once("art")
			if e.art == "suction":
				effects.burst("suction_swirl", cv.position + Vector2(cv.unit.facing * 90, -80), cv.unit.facing < 0)
			await hud.toast(e.name)
		"area":
			var col := Color(1, 0.6, 0.2, 0.45)
			if e.kind == "blowback":
				col = Color(0.6, 0.9, 1, 0.4)
			elif e.kind == "cutting_line":
				col = Color(1, 0.15, 0.15, 0.55)
				for t in e.tiles:
					effects.burst("cutting_line", board_view.tile_center(t))
			for t in e.tiles:
				board_view.flash_tiles[t] = col
			board_view.redraw()
			await get_tree().create_timer(area_flash_seconds, false).timeout
			board_view.flash_tiles.clear()
			board_view.redraw()
		"object_hit":
			effects.float_text(board_view.tile_center(e.tile) + Vector2(0, -20), "%d" % e.amount, Color.WHITE)
			if e.destroyed:
				hud.log_line("Cover destroyed.")
				board_view.mark_destroyed(e.tile, e.get("kind", "box"))
			else:
				board_view.sync_props()
		"noise":
			hud.refresh()
		"gaze":
			hud.log_line("Human Gaze! The human looks down.")
			audio.play("gaze", 0.0)
			for fu in e.frozen:
				effects.gaze_poof(board_view.view_of(fu))
			await hud.banner("Human Gaze")
		"gaze_end":
			hud.log_line("The human looks away.")
			audio.play("gaze_end")
			for fu in e.thawed:
				effects.gaze_poof(board_view.view_of(fu))
		"talk":
			await dialogue.play(SliceDialogue.RECRUIT)
			hud.log_line("Umbrella will join next Player Phase.")
		"telegraph":
			hud.log_line("Paper Cutter marks a Cutting Line!")
			audio.play("telegraph")
			board_view.redraw()
			await get_tree().create_timer(0.35, false).timeout
		"telegraph_cancel":
			hud.log_line("Cutting Line cancelled.")
		"tape":
			hud.log_line("%s is taped down." % e.unit.name)
			board_view.redraw()
		"item":
			hud.log_line("%s uses %s." % [e.unit.name, e.item])
		"phase":
			if e.phase == Defs.Phase.PLAYER:
				_sync()
				audio.play("phase")
				await hud.banner("Player Phase  -  Turn %d" % e.turn)


func _strike(e: Dictionary) -> void:
	var tv := board_view.view_of(e.target)
	var av := board_view.view_of(e.attacker)
	audio.play(BattleAudio.attack_sound(e.attacker), -10.0)
	var lunge := (tv.position - av.position).normalized() * lunge_pixels
	if av.has_anim("attack"):
		await av.play_once("attack")
	var tw := create_tween()
	tw.tween_property(av, "position", av.position + lunge, 0.08)
	tw.tween_property(av, "position", av.position, 0.08)
	await tw.finished
	var dist: int = e.attacker.distance_to_unit(e.attacker.pos, e.target, e.target.pos)
	var proj: String = PROJECTILES.get(e.attacker.id, "")
	if dist >= 2 and proj != "":
		await effects.projectile(proj, av.position + Vector2(0, -60), tv.position + Vector2(0, -50))
	audio.play("miss" if not e.hit else ("crit" if e.crit else "hit"))
	if e.hit:
		effects.burst("crit_burst" if e.crit else "hit_spark", tv.position + Vector2(0, -56))
		tv.play_once("hurt")
	var txt := "Miss"
	if e.hit:
		txt = ("CRIT %d" if e.crit else "%d") % e.damage
	if e.get("intercepted", false):
		hud.log_line("Lamp intercepts the hit (Watchful).")
	effects.float_text(tv.position + Vector2(0, -90), txt, Color("ffe070") if e.crit else Color.WHITE)
	hud.log_line("%s %s %s: %s" % [e.attacker.name, "counters" if e.get("counter", false) else "hits", e.target.name, txt])
	await get_tree().create_timer(after_strike_seconds, false).timeout
