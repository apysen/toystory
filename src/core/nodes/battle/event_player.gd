class_name EventPlayer
extends Node

## Plays back the events a `Battle` produced (see `Battle.take_events`) in the
## diorama: units walk their paths, attackers lunge, projectiles fly, damage
## numbers float up, cover breaks, the Gaze falls and lifts. During the Enemy
## Phase the camera glides to each enemy as it acts. The rules have already
## resolved by the time anything here runs; playback only shows what happened.

## Projectile effect each ranged attacker fires.
const PROJECTILES := {"stapler": "staple_shot", "toaster": "toast", "teacup": "steam_curl"}

@export_group("Collaborators")
@export var camera: BattleCamera
@export var effects: EffectsLayer
@export var audio: BattleAudio
@export var hud: BattleHud
@export var dialogue: DialogueBox
@export var overlays: GroundOverlays
@export var diorama: Diorama

@export_group("Timing")
## Metres per second a unit walks during playback.
@export var walk_speed := 4.5
## Metres per second a unit slides when pushed or pulled.
@export var shove_speed := 9.0
@export var lunge_metres := 0.25
@export var after_strike_seconds := 0.2

var _battle: Battle
var _cards: Dictionary = {}


func setup(b: Battle, cards: Dictionary) -> void:
	_battle = b
	_cards = cards


func card(u: Unit) -> UnitCard:
	return _cards[u.id]


func play(events: Array) -> void:
	for e in events:
		await _play_one(e)
		_sync()
	# Whatever playback didn't show explicitly catches up at the end.
	for id in _cards:
		var c: UnitCard = _cards[id]
		c.shown_hp = c.unit.hp
	overlays.shown_telegraphs = _battle.telegraphs.duplicate()
	overlays.sync()


## Refreshes what can be read straight from the rules without getting ahead of
## playback: faction colours, telegraphs, the HUD. HP and the Gaze form follow
## their own events.
func _sync() -> void:
	for id in _cards:
		var c: UnitCard = _cards[id]
		if not c.unit.broken:
			c.refresh()
	overlays.sync()
	hud.refresh()


func _enemy_turn(u: Unit) -> bool:
	return _battle.phase == Defs.Phase.ENEMY and u.faction == Defs.Faction.ENEMY


func _play_one(e: Dictionary) -> void:
	match e.type:
		"move", "displace":
			var u: Unit = e.unit
			if _enemy_turn(u):
				await camera.glide_to(BattleSpace.to_world(e.path[0]))
			await _walk(card(u), e.path, walk_speed if e.type == "move" else shove_speed, e.type == "move")
		"teleport":
			card(e.unit).position = BattleSpace.to_world(e.unit.pos)
		"strike":
			await _strike(e)
		"damage":
			var c := card(e.unit)
			c.shown_hp = e.hp
			if c.has_anim("hurt"):
				c.play_once("hurt")
		"heal":
			var c := card(e.unit)
			c.shown_hp = e.hp
			audio.play("heal")
			effects.burst("heal_sparkle", c.global_position + Vector3(0, 0.45, 0))
			effects.float_text(c.global_position + Vector3(0, 1.0, 0), "+%d" % e.amount, Color("80ff90"))
			await get_tree().create_timer(0.3, false).timeout
		"broken":
			overlays.remove_telegraphs(e.unit)
			hud.notify("%s is Broken." % e.unit.name)
			audio.play("broken")
			await card(e.unit).play_broken()
		"collision":
			hud.notify("%s collides!" % e.unit.name)
			audio.play("collision")
		"art":
			audio.play(BattleAudio.ART_SOUNDS.get(e.art, ""))
			var c := card(e.unit)
			if _enemy_turn(e.unit):
				await camera.glide_to(c.global_position)
			c.play_once("art")
			if e.art == "suction":
				effects.burst("suction_swirl", c.global_position + c.heading * 0.8 + Vector3(0, 0.6, 0))
			await hud.toast(e.name)
		"area":
			overlays.flash_area(e)
			if e.kind == "cutting_line":
				for tg in overlays.shown_telegraphs.duplicate():
					if tg.a == e.a and tg.b == e.b:
						overlays.remove_telegraphs(tg.owner)
				var steps := 6
				for k in steps + 1:
					effects.burst("cutting_line", BattleSpace.to_world((e.a as Vector2).lerp(e.b, float(k) / steps), 0.3))
			await get_tree().create_timer(0.3, false).timeout
		"object_hit":
			var r: Rect2 = e.rect
			effects.float_text(BattleSpace.rect_center_world(r, 0.9), "%d" % e.amount, Color.WHITE)
			diorama.update_cover(e.id, e.destroyed, r, e.kind)
			if e.destroyed:
				hud.notify("Cover destroyed.")
		"noise":
			hud.refresh()
		"gaze":
			hud.notify("Human Gaze! The human looks down.")
			audio.play("gaze", 0.0)
			overlays.gaze_visible = true
			overlays.sync()
			for fu in e.frozen:
				effects.gaze_poof(card(fu), true)
			await hud.banner("Human Gaze")
		"gaze_end":
			hud.notify("The human looks away.")
			audio.play("gaze_end")
			overlays.gaze_visible = false
			overlays.sync()
			for fu in e.thawed:
				effects.gaze_poof(card(fu), false)
		"talk":
			await dialogue.play(SliceDialogue.RECRUIT)
			hud.notify("Umbrella will join next Player Phase.")
		"telegraph":
			await camera.glide_to(card(e.unit).global_position)
			hud.notify("Paper Cutter marks a Cutting Line!")
			audio.play("telegraph")
			overlays.add_telegraph(e.unit, e.a, e.b, e.half_width)
			await get_tree().create_timer(0.45, false).timeout
		"telegraph_cancel":
			overlays.remove_telegraphs(e.unit)
			hud.notify("Cutting Line cancelled.")
		"tape":
			hud.notify("%s is taped down." % e.unit.name)
			diorama.add_tape_patch(e.pos, e.radius)
		"item":
			hud.notify("%s uses %s." % [e.unit.name, e.item])
		"phase":
			if e.phase == Defs.Phase.PLAYER:
				_sync()
				audio.play("phase")
				await hud.banner("Player Phase  -  Turn %d" % e.turn)


func _walk(c: UnitCard, path: Array, speed: float, animate: bool) -> void:
	if path.size() < 2:
		return
	if animate:
		c.set_moving(true)
	for k in range(1, path.size()):
		var a: Vector2 = path[k - 1]
		var b: Vector2 = path[k]
		if animate:
			c.face_along(b - a)
		var tw := create_tween()
		tw.tween_property(c, "position", BattleSpace.to_world(b), maxf(a.distance_to(b) / speed, 0.02))
		await tw.finished
	if animate:
		c.set_moving(false)


func _strike(e: Dictionary) -> void:
	var tc := card(e.target)
	var ac := card(e.attacker)
	if _enemy_turn(e.attacker):
		await camera.glide_to((ac.global_position + tc.global_position) * 0.5)
	ac.face_along(BattleSpace.to_floor(tc.global_position - ac.global_position))
	audio.play(BattleAudio.attack_sound(e.attacker), -10.0)
	if ac.has_anim("attack"):
		await ac.play_once("attack")
	var dir := (tc.global_position - ac.global_position)
	dir.y = 0
	dir = dir.normalized()
	var home := ac.position
	var tw := create_tween()
	tw.tween_property(ac, "position", home + dir * lunge_metres, 0.08)
	tw.tween_property(ac, "position", home, 0.1)
	await tw.finished
	var gap: float = e.attacker.gap_to(e.target)
	var proj: String = PROJECTILES.get(e.attacker.id, "")
	var hand_height := 0.5 if not e.attacker.is_large() else 1.0
	if gap > Defs.MELEE_REACH and proj != "":
		await effects.projectile(proj, ac.global_position + Vector3(0, hand_height, 0), tc.global_position + Vector3(0, 0.45, 0))
	audio.play("miss" if not e.hit else ("crit" if e.crit else "hit"))
	var hit_at := tc.global_position + Vector3(0, 0.9 if e.target.is_large() else 0.45, 0)
	if e.hit:
		effects.burst("crit_burst" if e.crit else "hit_spark", hit_at)
	var txt := "Miss"
	if e.hit:
		txt = ("CRIT %d" if e.crit else "%d") % e.damage
	if e.get("intercepted", false):
		hud.notify("Lamp intercepts the hit (Watchful).")
	effects.float_text(hit_at + Vector3(0, 0.5, 0), txt, Color("ffe070") if e.crit else (Color.WHITE if e.hit else Color("b8b0c8")))
	await get_tree().create_timer(after_strike_seconds, false).timeout
