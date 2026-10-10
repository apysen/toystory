class_name EventPlayer
extends Node

## Plays back the events a `Battle` produced (see `Battle.take_events`) in the
## diorama: units walk their paths, attackers lunge, projectiles fly, damage
## numbers float up, cover breaks, the Gaze falls and lifts. During the Enemy
## Phase the camera glides to each enemy as it acts. The rules have already
## resolved by the time anything here runs; playback only shows what happened.
##
## Lamp's Arts are timed to their clips' events: Flashbulb pops on "flash" and its
## hits land then (the clip is the strike, so no Pole Strike swing follows);
## Guard Beam's beam and bubble run from "beam" to "release"; Spotlight, his
## signature, pushes the camera in, rings out on "stamp", shoots a beam into the
## sky on "beam_up" and drops the stage light on its area on "land".
##
## Stapler fires 3D staples straight from his pistols' muzzles: his Staple Shot on
## the attack's contact frame, Pin's heavy staple on its "hit", and Staple Burst's
## four on "shot_1".."shot_4" (right, left, right, left; two to each strike).
## Staple Storm, his signature, pushes the camera in and throws a ring of staples
## out in every direction on each of "volley_1" and "volley_2", with one at each
## enemy it strikes.
##
## Toaster launches 3D toast out of his slots. Every lever slam ("slam") stokes his
## vents; a launched slice is hidden in its slot until the clip brings a fresh one
## up ("reload"), browned. Toast Pop fires the front slice on the attack's "hit";
## Eject fires both at its target on its "hit". Flash Bake grows his palm flames
## from "charge" and blasts a cone of fire from both palms from "fire" to
## "fire_end". Overheat, his signature, pushes the camera in: the vents build to
## white-hot from "slam", fire swirls round him as he lifts off on "rise", and on
## "erupt" pillars of fire burst up round him and a slice blasts sky-high at each
## enemy struck (front and back slots in turn); he lands on "land", smoking.

## Where Lamp's lights come from, in the bone's frame (Y runs down it): the middle
## of the lantern's glass below its hinge, and the bulb inside the shade.
const LANTERN_GLASS := Vector3(0, 0.13, 0)
const SHADE_BULB := Vector3(0, 0.15, 0)

## Units whose model fires 3D staples from its "gun_R" and "gun_L" bones, and where
## the muzzle sits in a gun bone's frame (the front of the jaws, measured off the
## built model).
const STAPLE_SHOOTERS: Array[String] = ["stapler"]
const MUZZLE := Vector3(0, 0.123, 0.075)
## Staples fired toward each strike of a multi-shot Art.
const SHOTS_PER_STRIKE := {"staple_burst": 2, "eject": 2}
## Staples in each of Staple Storm's rings, and how far out they fly before fading.
const STORM_RING := 10
const STORM_REACH := 1.4

## Units whose model launches 3D toast from its "toast_front" / "toast_back" slot
## bones, and the middle of a slice in its bone's frame (Y runs up the slice).
const TOAST_SHOOTERS: Array[String] = ["toaster"]
const SLOT_BONES := {"front": "toast_front", "back": "toast_back"}
const SLICE_MIDDLE := Vector3(0, 0.055, 0)
## Pillars of fire Overheat's eruption throws up round him.
const OVERHEAT_PILLARS := 6

## Projectile effect each ranged attacker fires.
const PROJECTILES := {"stapler": "staple_shot", "toaster": "toast", "teacup": "steam_curl"}

@export_group("Collaborators")
@export var camera: BattleCamera
@export var effects: EffectsLayer
@export var lights: ArtLights
@export var audio: BattleAudio
@export var hud: BattleHud
@export var dialogue: DialogueBox
@export var overlays: GroundOverlays
@export var diorama: Diorama
## Playback runs at its speed; steering a unit never does.
@export var speed_settings: BattleSpeedSettings

@export_group("Timing")
## Metres per second a unit travels during playback: the pace the run clips are
## authored for, so feet match the floor (Battle Speed speeds playback up).
@export var walk_speed := 1.8
## Metres per second a unit slides when pushed or pulled.
@export var shove_speed := 9.0
@export var lunge_metres := 0.25
@export var after_strike_seconds := 0.2

@export_group("Arts")
## How bright the lamp's glow flares when Flashbulb pops (1 = its usual glow).
@export var flash_glow := 7.0
## Signature Arts push the camera in to this share of its zoom.
@export var signature_zoom := 0.6
## Seconds Spotlight's stage light holds after it lands, before it fades.
@export var spotlight_hold_seconds := 0.8
## How bright the Toaster's vents flare when his lever slams down.
@export var vent_flare := 4.0
## How bright they burn at Overheat's eruption (white-hot).
@export var overheat_flare := 9.0
## How much Flash Bake's charge grows his palm flames.
@export var bake_heat := 2.4

var _battle: Battle
var _cards: Dictionary = {}
var _playing := false
## The unit whose Art clip already showed its strike (Flashbulb, Pin, Staple Burst):
## its strikes land without the attack swing until the next Art or the end of playback.
var _strike_in_clip: Unit = null
## That Art, the seconds since its clip started, and the shots still to fire in it
## (staples [{t, gun, heavy}], toast [{t, slot}], in order).
var _clip_art := ""
var _clip_time := 0.0
var _shots: Array = []
## Clip time until which an Art's show is still running after its events (Staple
## Storm's last volley and the camera easing back out); playback waits for it.
var _show_until := 0.0


func setup(b: Battle, cards: Dictionary) -> void:
	_battle = b
	_cards = cards
	if speed_settings != null:
		speed_settings.changed.connect(_apply_speed)


func _exit_tree() -> void:
	Engine.time_scale = 1.0


## Game time runs at the Battle Speed while events play back, and at real time
## otherwise (when the player steers).
func _apply_speed() -> void:
	Engine.time_scale = speed_settings.speed() if _playing and speed_settings != null else 1.0


func _process(delta: float) -> void:
	_clip_time += delta


func card(u: Unit) -> UnitCard:
	return _cards[u.id]


func play(events: Array) -> void:
	_playing = true
	_apply_speed()
	for e in events:
		await _play_one(e)
		_sync()
	if _show_until > _clip_time:
		await _wait(_show_until - _clip_time)
	_show_until = 0.0
	_playing = false
	_strike_in_clip = null
	_shots.clear()
	_apply_speed()
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
			if e.unit == _strike_in_clip:
				# his own Art hurt him (Overheat's burn): its clip shows it, so no flinch
				effects.float_text(c.global_position + Vector3(0, 1.2, 0), "-%d" % e.amount, Color("ff9a50"))
			else:
				c.play_hurt()
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
			_strike_in_clip = null
			if _enemy_turn(e.unit):
				await camera.glide_to(c.global_position)
			_face_art(c, e)
			match e.art:
				"flashbulb":
					hud.toast(e.name)
					await _flashbulb(c)
				"guard_beam":
					hud.toast(e.name)
					await _guard_beam(c, e.target)
				"spotlight":
					hud.toast(e.name)
					await _spotlight(c, e)
				"pin", "staple_burst":
					hud.toast(e.name)
					_staple_art(c, e.art)
				"staple_storm":
					hud.toast(e.name)
					await _staple_storm(c)
				"eject":
					hud.toast(e.name)
					_toast_art(c, e.art)
				"flash_bake":
					hud.toast(e.name)
					await _flash_bake(c, e)
				"overheat":
					hud.toast(e.name)
					await _overheat(c)
				_:
					c.play_art(e.art)
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
	var intercepted: bool = e.get("intercepted", false)
	if intercepted:
		# Watchful: Lamp gets between the ally and the attacker before the blow lands.
		await tc.intercept(card(e.original).global_position, ac.global_position)
	ac.face_along(BattleSpace.to_floor(tc.global_position - ac.global_position))
	var contact := ac.contact_time("attack")
	if e.attacker == _strike_in_clip:
		pass # the Art's own clip already showed the blow
	elif not is_nan(contact):
		audio.play(BattleAudio.attack_sound(e.attacker), -10.0)
		# A model's swing carries its own lunge: the hit lands on its contact frame
		# while the follow-through plays on.
		ac.play_once("attack")
		if e.attacker.id in TOAST_SHOOTERS:
			_toaster_clip(ac, "attack", ["front"])
		await get_tree().create_timer(contact, false).timeout
	else:
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
	if e.attacker.id in STAPLE_SHOOTERS and ac.has_anim("attack"):
		await _fire_staples(ac, _next_shots(e.attacker), tc.global_position + Vector3(0, 0.9 if e.target.is_large() else 0.45, 0), e.hit)
	elif e.attacker.id in TOAST_SHOOTERS and ac.has_anim("attack"):
		await _launch_toast(ac, _next_toast(e.attacker), tc.global_position + Vector3(0, _body_height(e.target), 0), e.hit)
	elif gap > Defs.MELEE_REACH and proj != "" and e.attacker != _strike_in_clip:
		await effects.projectile(proj, ac.global_position + Vector3(0, hand_height, 0), tc.global_position + Vector3(0, 0.45, 0))
	if intercepted:
		tc.take_guarded_hit()
	audio.play("miss" if not e.hit else ("crit" if e.crit else "hit"))
	var hit_at := tc.global_position + Vector3(0, 0.9 if e.target.is_large() else 0.45, 0)
	if e.hit:
		effects.burst("crit_burst" if e.crit else "hit_spark", hit_at)
	var txt := "Miss"
	if e.hit:
		txt = ("CRIT %d" if e.crit else "%d") % e.damage
	if intercepted:
		hud.notify("Lamp intercepts the hit (Watchful).")
	effects.float_text(hit_at + Vector3(0, 0.5, 0), txt, Color("ffe070") if e.crit else (Color.WHITE if e.hit else Color("b8b0c8")))
	await get_tree().create_timer(after_strike_seconds, false).timeout
	if intercepted:
		tc.absorbed_hit = e.hit and tc.has_anim("intercept_guard")
		await tc.stand_down(ac.global_position)


# --- Arts ---------------------------------------------------------------------

## Turns the user toward what its Art is aimed at. Enemy moves played as Arts
## (the Captain's "cutting_line") aren't in Arts.DATA and are left alone.
func _face_art(c: UnitCard, e: Dictionary) -> void:
	if not Arts.DATA.has(e.art):
		return
	var u: Unit = e.unit
	var t: Variant = e.get("target")
	match Arts.get_art(e.art).target:
		"direction":
			if t is Vector2:
				c.face_along(t)
		"area":
			if t is Vector2 and (t as Vector2).distance_to(u.pos) > 0.05:
				c.face_along(t - u.pos)
		"ally", "enemy", "lunge":
			if t is Unit and t != u:
				c.face_along((t as Unit).pos - u.pos)


## Seconds into an Art's clip of one of its events, or `fallback` without one.
func _moment(c: UnitCard, art_id: String, event: String, fallback: float) -> float:
	var t := c.art_time(art_id, event)
	return fallback if is_nan(t) else t


func _wait(seconds: float) -> void:
	if seconds > 0.0:
		await get_tree().create_timer(seconds, false).timeout


func _body_height(u: Unit) -> float:
	return 0.9 if u.is_large() else 0.45


## Pin and Staple Burst: the clip plays and its shots are queued for the strikes that
## follow, each fired on its own frame.
func _staple_art(c: UnitCard, art_id: String) -> void:
	_strike_in_clip = c.unit
	_clip_art = art_id
	_clip_time = 0.0
	_shots.clear()
	c.play_art(art_id)
	if art_id == "pin":
		_shots.append({"t": _moment(c, "pin", "hit", 0.5), "gun": "gun_R", "heavy": true})
	elif art_id == "staple_storm":
		# one staple at each enemy struck: the first two in the first volley, the rest in the second
		var v1 := _moment(c, art_id, "volley_1", 1.0)
		var v2 := _moment(c, art_id, "volley_2", v1 + 0.15)
		for k in 12:
			_shots.append({"t": v1 if k < 2 else v2, "gun": "gun_R" if k % 2 == 0 else "gun_L", "heavy": false})
	else:
		for k in 4:
			_shots.append({"t": _moment(c, art_id, "shot_%d" % (k + 1), 0.25 + 0.15 * k),
				"gun": "gun_R" if k % 2 == 0 else "gun_L", "heavy": false})


## Staple Storm: the camera pushes in, he leaps and spins, and each volley throws a
## ring of staples out all round him (the enemies struck get theirs from the strikes
## that follow); the camera eases back out after the second volley.
func _staple_storm(c: UnitCard) -> void:
	await camera.push_in(c.global_position, signature_zoom)
	_staple_art(c, "staple_storm")
	var v1 := _moment(c, "staple_storm", "volley_1", 1.0)
	var v2 := _moment(c, "staple_storm", "volley_2", v1 + 0.15)
	_storm_ring(c, v1, 0.0)
	_storm_ring(c, v2, PI / STORM_RING)
	_ease_back_after(c, v2 + 0.45)
	_show_until = v2 + 0.9


func _storm_ring(c: UnitCard, at: float, turn: float) -> void:
	await _wait(at - _clip_time)
	var centre := c.global_position + Vector3(0, 0.5, 0)
	for i in STORM_RING:
		var a := turn + TAU * i / STORM_RING
		var d := Vector3(cos(a), -0.08, sin(a)).normalized()
		effects.staple(false, centre + d * 0.25, centre + d * STORM_REACH, false)


func _ease_back_after(c: UnitCard, at: float) -> void:
	await _wait(at - _clip_time)
	camera.ease_back(c.global_position)


## The staples for this strike: the next ones queued by the attacker's Art, or one
## from the right pistol straight away (Staple Shot, a counter).
func _next_shots(attacker: Unit) -> Array:
	if attacker != _strike_in_clip or _shots.is_empty():
		return [{"t": NAN, "gun": "gun_R", "heavy": false}]
	var out: Array = []
	for k in mini(int(SHOTS_PER_STRIKE.get(_clip_art, 1)), _shots.size()):
		out.append(_shots.pop_front())
	return out


## Fires each staple from its pistol's muzzle on its frame and waits for the last
## to land; a pair spreads a little so both read.
func _fire_staples(ac: UnitCard, shots: Array, at: Vector3, hit: bool) -> void:
	for k in shots.size():
		var shot: Dictionary = shots[k]
		if not is_nan(shot.t):
			await _wait(shot.t - _clip_time)
		var from := ac.bone_point(shot.gun, 0.5, MUZZLE)
		var to := at + Vector3(0, 0.06 * (k - (shots.size() - 1) * 0.5), 0)
		if k == shots.size() - 1:
			await effects.staple(shot.heavy, from, to, hit)
		else:
			effects.staple(shot.heavy, from, to, hit)


# --- Toaster -----------------------------------------------------------------

## The toast for this strike: the next slices queued by the attacker's Art (Eject's
## two, Overheat's one each), or the front slice straight away (Toast Pop, a counter).
func _next_toast(attacker: Unit) -> Array:
	if attacker != _strike_in_clip or _shots.is_empty():
		return [{"t": NAN, "slot": "front"}]
	var out: Array = []
	for k in mini(int(SHOTS_PER_STRIKE.get(_clip_art, 1)), _shots.size()):
		out.append(_shots.pop_front())
	return out


## Launches each slice from its slot on its moment (hiding it there until the clip
## reloads it) and waits for the last to land. Overheat's fly sky-high.
func _launch_toast(ac: UnitCard, shots: Array, at: Vector3, hit: bool) -> void:
	var arc := 2.5 if _clip_art == "overheat" and ac.unit == _strike_in_clip else 1.0
	for k in shots.size():
		var shot: Dictionary = shots[k]
		if not is_nan(shot.t):
			await _wait(shot.t - _clip_time)
		var from := ac.bone_point(SLOT_BONES[shot.slot], 0.8, SLICE_MIDDLE)
		ac.set_slice(shot.slot, true)
		var to := at + Vector3(0.05 * (k - (shots.size() - 1) * 0.5), 0, 0)
		if k == shots.size() - 1:
			await effects.toast(from, to, hit, arc)
		else:
			effects.toast(from, to, hit, arc)


## Runs alongside one of the Toaster's toast clips from its start: the lever slam
## stokes the vents until the toast flies (its "hit"), smoke puffs from the slots,
## and the slices in `slots` come back up browned on "reload".
func _toaster_clip(c: UnitCard, clip: String, slots: Array) -> void:
	var slam := c.art_time(clip, "slam")
	var hit := c.art_time(clip, "hit")
	var reload := c.art_time(clip, "reload")
	if is_nan(slam) or is_nan(hit) or is_nan(reload):
		return
	await _wait(slam)
	c.flare_glow(vent_flare, 0.8)
	if c.fire() != null:
		c.fire().vents = 0.8
	await _wait(hit - slam)
	if c.fire() != null:
		c.fire().vents = 0.0
	await _wait(0.15)
	for slot in slots:
		effects.smoke_puff(c.bone_point(SLOT_BONES[slot], 0.8, SLICE_MIDDLE * 2.0), 6, 0.12)
	await _wait(reload - hit - 0.15)
	for slot in slots:
		c.set_slice(slot, false, 1.0)


## Eject: the lever slap, the long heat-up and the fold forward; both slices blast
## out at the target on the clip's "hit" (the strike that follows fires them).
func _toast_art(c: UnitCard, art_id: String) -> void:
	_strike_in_clip = c.unit
	_clip_art = art_id
	_clip_time = 0.0
	_shots.clear()
	c.play_art(art_id)
	var hit := _moment(c, art_id, "hit", 1.0)
	for slot in ["front", "back"]:
		_shots.append({"t": hit, "slot": slot})
	_toaster_clip(c, art_id, ["front", "back"])
	_show_until = _moment(c, art_id, "reload", hit + 1.0) + 0.3


## Flash Bake: he stamps, the palm flames grow as he draws them back, and fire
## blasts from both palms over the cone from "fire" to "fire_end"; its hits land
## while it burns.
func _flash_bake(c: UnitCard, e: Dictionary) -> void:
	_strike_in_clip = c.unit
	_clip_art = "flash_bake"
	_clip_time = 0.0
	c.play_art("flash_bake")
	var stomp := _moment(c, "flash_bake", "stomp", 0.2)
	var charge := _moment(c, "flash_bake", "charge", stomp + 0.3)
	var on := _moment(c, "flash_bake", "fire", charge + 0.8)
	var off := _moment(c, "flash_bake", "fire_end", on + 0.6)
	var aim: Vector2 = e.target if e.target is Vector2 else Vector2.RIGHT
	var reach := float(Arts.get_art("flash_bake").length) + (e.unit as Unit).radius
	await _wait(stomp)
	effects.smoke_puff(c.global_position + Vector3(0, 0.05, 0), 8, 0.22)
	_bake_flames(c, on - stomp, off - stomp)
	await _wait(on - stomp)
	var palms := [func() -> Vector3: return c.bone_point("flame_R", 0.45),
		func() -> Vector3: return c.bone_point("flame_L", 0.45)]
	effects.fire_cone(palms, BattleSpace.dir_to_world(aim), reach, rad_to_deg(Arts.CONE_HALF_ANGLE), off - on)
	_show_until = off + 0.3


## Grows the palm flames until the fire bursts out, and lets them settle after.
func _bake_flames(c: UnitCard, until: float, done: float) -> void:
	var fire := c.fire()
	if fire == null:
		return
	var tw := create_tween()
	tw.tween_property(fire, "heat", bake_heat, until)
	tw.tween_interval(done - until)
	tw.tween_property(fire, "heat", 1.0, 0.4)


## Overheat: the camera pushes in and the clip plays; its toasts are queued for the
## strikes that follow (one at each enemy struck, from the front and back slots in
## turn, sky-high on "erupt") while the show runs alongside.
func _overheat(c: UnitCard) -> void:
	await camera.push_in(c.global_position, signature_zoom)
	_strike_in_clip = c.unit
	_clip_art = "overheat"
	_clip_time = 0.0
	_shots.clear()
	c.play_art("overheat")
	var erupt := _moment(c, "overheat", "erupt", 2.0)
	for k in 12:
		_shots.append({"t": erupt + 0.07 * k, "slot": "front" if k % 2 == 0 else "back"})
	var land := _moment(c, "overheat", "land", erupt + 1.5)
	var reload := _moment(c, "overheat", "reload", land + 0.5)
	_overheat_show(c)
	_ease_back_after(c, land + 0.2)
	_show_until = reload + 0.3


func _overheat_show(c: UnitCard) -> void:
	var fire := c.fire()
	var slam := _moment(c, "overheat", "slam", 0.5)
	var rise := _moment(c, "overheat", "rise", slam + 1.0)
	var erupt := _moment(c, "overheat", "erupt", rise + 0.6)
	var land := _moment(c, "overheat", "land", erupt + 1.5)
	var reload := _moment(c, "overheat", "reload", land + 0.5)
	await _wait(slam - _clip_time)
	c.flare_glow(vent_flare, 0.5)
	c.ramp_glow(1.0, overheat_flare * 0.5, erupt - slam)
	if fire != null:
		create_tween().tween_property(fire, "vents", 1.6, erupt - slam)
	# smoke shudders out of the slots as it builds
	while _clip_time < rise - 0.3:
		for slot in SLOT_BONES:
			effects.smoke_puff(c.bone_point(SLOT_BONES[slot], 0.8, SLICE_MIDDLE * 2.0), 4, 0.12)
		await _wait(0.3)
	await _wait(rise - _clip_time)
	effects.fire_swirl(func() -> Vector3: return c.bone_point("hips", 0.3), 0.35, erupt - rise + 0.2)
	await _wait(erupt - _clip_time)
	c.flare_glow(overheat_flare, 1.0)
	if fire != null:
		fire.vents = 2.0
	for slot in SLOT_BONES:
		c.set_slice(slot, true)
	lights.ground_ring(c.global_position, Color(1.0, 0.5, 0.15))
	var radius := float(Arts.get_art("overheat").radius)
	for i in OVERHEAT_PILLARS:
		var a := TAU * i / OVERHEAT_PILLARS
		effects.fire_pillar(c.global_position + Vector3(cos(a), 0, sin(a)) * radius * 0.75, 1.2, 0.8)
	await _wait(land - _clip_time)
	effects.smoke_puff(c.global_position + Vector3(0, 0.05, 0), 14, 0.3)
	if fire != null:
		var tw := create_tween()
		tw.tween_property(fire, "vents", 0.3, 0.3)
		tw.tween_property(fire, "vents", 0.0, 1.2)
	for slot in SLOT_BONES:
		effects.smoke_puff(c.bone_point(SLOT_BONES[slot], 0.8, SLICE_MIDDLE * 2.0), 6, 0.14)
	await _wait(reload - _clip_time)
	for slot in SLOT_BONES:
		c.set_slice(slot, false, 1.0)


## Flashbulb: the lamp arm throws the head out and it pops; the cone's hits follow.
func _flashbulb(c: UnitCard) -> void:
	_strike_in_clip = c.unit
	c.play_art("flashbulb")
	await _wait(_moment(c, "flashbulb", "flash", 0.3))
	lights.flash(c.bone_point("head", 0.95, SHADE_BULB), c.heading)
	c.flare_glow(flash_glow, 0.5)


## Guard Beam: the staff levels at the ally, a beam runs from the lantern and a
## bubble of light holds round the ally until the staff lowers.
func _guard_beam(c: UnitCard, ally: Unit) -> void:
	var ac := card(ally)
	var h := _body_height(ally)
	c.play_art("guard_beam")
	var on := _moment(c, "guard_beam", "beam", 0.3)
	var off := _moment(c, "guard_beam", "release", on + 0.6)
	await _wait(on)
	var beam := lights.beam(func() -> Vector3: return c.bone_point("lantern", 0.6, LANTERN_GLASS),
		func() -> Vector3: return ac.global_position + Vector3(0, h, 0))
	var bubble := lights.bubble(ac.global_position + Vector3(0, h, 0), ally.radius * lights.bubble_scale)
	await _wait(off - on)
	lights.fade(beam, 0.25)
	lights.fade(bubble, 0.4)


## Spotlight: the camera pushes in, the staff stamps (a ring runs out), the lantern
## shoots a beam into the sky, and the stage light drops onto the area with the
## lamp's own beam on it and a shimmer round each ally it covers; the camera eases
## back out to frame Lamp and the light together.
func _spotlight(c: UnitCard, e: Dictionary) -> void:
	var u: Unit = e.unit
	var area := _battle.area_for(u, e.art, e.target)
	var center := BattleSpace.to_world(area.center)
	await camera.push_in(c.global_position, signature_zoom)
	c.play_art("spotlight")
	var stamp := _moment(c, "spotlight", "stamp", 0.3)
	var up := _moment(c, "spotlight", "beam_up", stamp + 0.4)
	var land := _moment(c, "spotlight", "land", up + 0.3)
	await _wait(stamp)
	lights.ground_ring(c.global_position)
	await _wait(up - stamp)
	var sky := lights.sky_beam(func() -> Vector3: return c.bone_point("lantern", 1.0, LANTERN_GLASS))
	camera.ease_back((c.global_position + center) * 0.5, land - up + 0.2)
	await _wait(land - up)
	lights.fade(sky, 0.3)
	var stage := lights.stage_light(center, area.radius)
	var head_beam := lights.beam(func() -> Vector3: return c.bone_point("head", 0.95, SHADE_BULB), func() -> Vector3: return center)
	for o in _battle.units_in_area(area):
		if o.faction == u.faction and not o.frozen:
			lights.shimmer(card(o).global_position + Vector3(0, _body_height(o), 0), o.radius * lights.bubble_scale)
	await _wait(spotlight_hold_seconds)
	lights.fade(head_beam, 0.3)
	lights.fade(stage, 0.6)
