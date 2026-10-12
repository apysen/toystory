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
##
## Teacup bends tea, drawn as ribbons of her own tea (TeaRibbon) that follow her
## hands or paths between the clip's events. Tea Lash snaps a rope of tea up after
## her left hand on "draw" and punches a dart of it from "bend_L" on "hit". Warm Pour
## and Steady Sip carry the tea across to the ally and heal (or ward) on their
## clips' "hit". Tea Break, her signature, pushes the camera in: a column of tea
## climbs out of her cup, rings her, bursts over the circle on "burst" (an amber ring
## runs out), wraps every ally in it on "hit" under a warm rain (the heals follow),
## and streams home on "return" as the camera eases back out.
##
## Umbrella floats when he travels (UnitModel launches, hovers and lands him). His
## Lunge is three clips split at the game's handoffs: the lead-in ("lunge", ending
## couched), the dash played as the couched run loop ("lunge_run", at the pace it was
## authored for, never the float), and the strike ("lunge_strike", the spike landing
## on its "hit"). Canopy opens over his neighbours on "open" (a shimmer and Half Cover
## over each). Raincheck, his signature, turns him to the nearest enemy that can shoot,
## pushes the camera in, rains over its circle from "open" to "end" and eases back
## on "shield"; a shot it draws off an ally flies to him instead.

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

## Units whose model bends tea (Teacup): Tea Lash's dart leaves her left hand
## ("bend_L"), a little off her palm (BEND_TIP, in the bone's frame).
const TEA_BENDERS: Array[String] = ["teacup"]
const BEND_TIP := Vector3(0, 0.04, 0)
## Metres tea leaving (or coming back into) her cup goes straight up (down) over the
## tea before it bends toward her hands, clear of the rim; and how high Steady Sip's
## thread lobs on its way to the ally (it peaks about 0.6 m over the cup).
const CUP_CLEAR := 0.14
const SIP_RISE := 0.8
## Seconds before Tea Lash's "draw" a stream of tea starts rising out of her cup to
## her hovering hand.
const LASH_GATHER := 0.45
## The amber light Tea Break's burst rings out across the floor, the blue of Steady
## Sip's ward, and where Tea Break's ring of tea orbits her (metres out, and up off
## the floor).
const TEA_AMBER := Color(1.0, 0.7, 0.3)
const WARD_BLUE := Color(0.45, 0.65, 1.0)
const TEA_RING_RADIUS := 0.55
const TEA_RING_HEIGHT := 0.7

## Projectile effect each ranged attacker fires.
## Canopy's shelter and Raincheck's rain, as light.
const CANOPY_TINT := Color(0.55, 0.9, 0.85)
const RAIN_TINT := Color(0.6, 0.8, 1.0)

const PROJECTILES := {"stapler": "staple_shot", "toaster": "toast", "teacup": "tea_lash"}

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

@export_group("Feel")
## Hit-stop: on a hit, the whole scene freezes this long (real seconds), longer on a crit.
@export var hit_stop_seconds := 0.07
@export var crit_hit_stop_seconds := 0.13
## How fast time runs during a hit-stop (a near freeze).
@export var hit_stop_scale := 0.04
## Camera shake on a hit, from a scratch (light) to a heavy blow (a quarter of the
## target's max HP or more), in metres; a crit shakes half again as hard.
@export var shake_light := 0.025
@export var shake_heavy := 0.09
@export var shake_seconds := 0.28
## Strikes push the camera in and down a little for the blow and ease back after
## the exchange. Skipped from this Battle Speed up.
@export var close_ups := true
@export var close_up_zoom := 0.78
@export var close_up_lower_degrees := 9.0
@export var close_up_max_speed := 1.5

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
## The unit whose Lunge has started: its dash runs couched and its strike is the
## Lunge's, not the basic swing.
var _charging: Unit = null
## Whether a strike's close-up has the camera pushed in (eased back when the
## exchange is over).
var _close_up := false


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
		if _close_up and not e.type in ["strike", "damage", "broken"]:
			await _end_close_up()
		await _play_one(e)
		_sync()
	if _close_up:
		await _end_close_up()
	if _show_until > _clip_time:
		await _wait(_show_until - _clip_time)
	_show_until = 0.0
	hud.signature_out()
	_playing = false
	_strike_in_clip = null
	_charging = null
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
			if u == _charging and e.type == "move":
				await _charge(card(u), e.path)
			else:
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
			if Arts.DATA.has(e.art) and Arts.get_art(e.art).get("signature", false):
				hud.signature_in(e.name, e.unit.name)
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
				"warm_pour", "steady_sip":
					hud.toast(e.name)
					await _tea_art(c, e.art, e.target if e.target is Unit else null)
				"tea_break":
					hud.toast(e.name)
					await _tea_break(c, e)
				"lunge" when c.has_anim("lunge_run"):
					hud.toast(e.name)
					await _lunge(c)
				"canopy" when c.has_anim("canopy"):
					hud.toast(e.name)
					await _canopy(c)
				"raincheck":
					hud.toast(e.name)
					await _raincheck(c, e)
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
	await _start_close_up(ac, tc)
	# Lunge's strike is its own clip, landing as the dash arrives
	var swing := "lunge_strike" if e.attacker == _charging and ac.has_anim("lunge_strike") else "attack"
	if e.attacker == _charging:
		_charging = null
	var contact := ac.contact_time(swing)
	if e.attacker == _strike_in_clip:
		pass # the Art's own clip already showed the blow
	elif not is_nan(contact):
		audio.play(BattleAudio.attack_sound(e.attacker), -10.0)
		# A model's swing carries its own lunge: the hit lands on its contact frame
		# while the follow-through plays on.
		ac.play_once(swing)
		if e.attacker.id in TOAST_SHOOTERS:
			_toaster_clip(ac, "attack", ["front"])
		elif e.attacker.id in TEA_BENDERS:
			_tea_lash(ac)
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
	elif e.attacker.id in TEA_BENDERS and ac.has_anim("attack"):
		await effects.tea_dart(_bend(ac, "L").call(), tc.global_position + Vector3(0, _body_height(e.target), 0), e.hit)
	elif gap > Defs.MELEE_REACH and proj != "" and e.attacker != _strike_in_clip:
		await effects.projectile(proj, ac.global_position + Vector3(0, hand_height, 0), tc.global_position + Vector3(0, 0.45, 0))
	if intercepted:
		tc.take_guarded_hit()
	audio.play("miss" if not e.hit else ("crit" if e.crit else "hit"))
	var hit_at := tc.global_position + Vector3(0, 0.9 if e.target.is_large() else 0.45, 0)
	if e.hit:
		effects.burst("crit_burst" if e.crit else "hit_spark", hit_at)
	if intercepted:
		hud.notify("Umbrella draws the shot (Raincheck)." if e.get("raincheck", false) else "Lamp intercepts the hit (Watchful).")
	effects.damage_number(hit_at + Vector3(0, 0.5, 0), e.damage, e.hit, e.crit, e.get("type_rel", 0))
	if e.hit:
		var weight := clampf(float(e.damage) / maxf(e.target.max_hp * 0.25, 1.0), 0.0, 1.0)
		camera.shake(lerpf(shake_light, shake_heavy, weight) * (1.5 if e.crit else 1.0), shake_seconds)
		await _hit_stop(crit_hit_stop_seconds if e.crit else hit_stop_seconds)
	await get_tree().create_timer(after_strike_seconds, false).timeout
	if intercepted:
		tc.absorbed_hit = e.hit and tc.has_anim("intercept_guard")
		await tc.stand_down(ac.global_position)


## Freezes the scene for `seconds` of real time at the moment of a hit.
func _hit_stop(seconds: float) -> void:
	if seconds <= 0.0:
		return
	Engine.time_scale = hit_stop_scale
	await get_tree().create_timer(seconds, true, false, true).timeout
	_apply_speed()


## Pushes the camera in on a strike between `ac` and `tc`, unless an Art already has
## it pushed in or Battle Speed is fast.
func _start_close_up(ac: UnitCard, tc: UnitCard) -> void:
	if _close_up or not close_ups or camera.is_pushed_in():
		return
	if speed_settings != null and speed_settings.speed() > close_up_max_speed:
		return
	_close_up = true
	await camera.push_in((ac.global_position + tc.global_position) * 0.5, close_up_zoom, 0.25, close_up_lower_degrees)


func _end_close_up() -> void:
	_close_up = false
	await camera.ease_back(camera.target_focus, 0.3)


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


# --- Teacup -------------------------------------------------------------------

## A point on one of Teacup's bending bones just off her palm, where her bent tea
## leaves her hand ("R" or "L").
func _bend(c: UnitCard, side: String) -> Callable:
	return func() -> Vector3: return c.bone_point("bend_" + side, 0.5, BEND_TIP)


## Where her tea's surface is (Tea Break's column climbs out of it).
func _cup(c: UnitCard) -> Callable:
	var tea := c.tea()
	return func() -> Vector3: return tea.surface() if tea != null else c.global_position + Vector3(0, 0.8, 0)


## A point travelling along `path` (a Callable taking 0..1) over `seconds`, for a
## ribbon of tea to follow; returns where it is now.
func _moving(path: Callable, seconds: float) -> Callable:
	var t := [0.0]
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void: t[0] = v, 0.0, 1.0, maxf(seconds, 0.01)).set_trans(Tween.TRANS_SINE)
	return func() -> Vector3: return path.call(t[0])


## A fountain of tea from `from` to `to` (Callables: either end may be moving): it
## leaves straight up, `rise` metres before it bends over (so tea out of her cup
## clears the rim instead of cutting through the porcelain), and comes down onto
## `to` from at least `land` metres above it. Its peak is about three quarters of
## the way up to the higher of the two bends.
func _fountain(from: Callable, to: Callable, rise: float, land: float) -> Callable:
	return func(t: float) -> Vector3:
		var a: Vector3 = from.call()
		var b: Vector3 = to.call()
		var up := a + Vector3.UP * rise
		var down := Vector3(b.x, maxf(up.y, b.y + land), b.z)
		var u := 1.0 - t
		return a * u * u * u + up * 3.0 * u * u * t + down * 3.0 * u * t * t + b * t * t * t


## A soft arc of tea from `from` to `to` (Callables: either end may be moving).
func _arc(from: Callable, to: Callable, lift := 0.3) -> Callable:
	return func(t: float) -> Vector3:
		var a: Vector3 = from.call()
		var b: Vector3 = to.call()
		var mid := (a + b) * 0.5 + Vector3.UP * lift
		return a.lerp(mid, t).lerp(mid.lerp(b, t), t)


## A spiral of `loops` turns round the point `center` returns, `radius` out,
## climbing `rise` metres from `height` above it, starting at angle `start`.
func _spiral(center: Callable, radius: float, height: float, rise: float, loops: float, start := 0.0) -> Callable:
	return func(t: float) -> Vector3:
		var a := start + TAU * loops * t
		return (center.call() as Vector3) + Vector3(cos(a) * radius, height + rise * t, sin(a) * radius)


## Runs a ribbon of tea along `path` for `seconds`, then lets it drain away.
func _tea_flow(path: Callable, seconds: float, half_width := 0.02, life := 0.4) -> void:
	var r := effects.tea_ribbon(_moving(path, seconds), half_width, life)
	await _wait(seconds)
	r.stop()


## A thread of tea drawn whole along `path` (a Callable taking 0..1): its head runs
## from start to end over `seconds` with a tail `length` (share of the path) behind
## it, which then drains in after it; smooth at any frame rate.
func _tea_thread(path: Callable, seconds: float, half_width: float, length := 0.6) -> void:
	var span := [0.0, 0.0]
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void:
		span[1] = minf(v, 1.0)
		span[0] = clampf(v - length, 0.0, 1.0), 0.0, 1.0 + length, maxf(seconds, 0.01) * (1.0 + length))
	var thread := effects.tea_strand(func(t: float) -> Vector3: return path.call(lerpf(span[0], span[1], t)),
		half_width, 0.4)
	await tw.finished
	thread.stop()


## Where a unit's chest is in the world.
func _chest(u: Unit) -> Callable:
	return func() -> Vector3: return card(u).global_position + Vector3(0, _body_height(u), 0)


## Tea Lash, alongside the attack clip from its start: just before "draw" the tea
## rises out of her cup and arcs over onto her left hand hovering beside it, and as
## she snaps the hand up it pulls a rope of tea after it that whips round with it
## until the punch ("hit"), when the strike that follows fires the dart.
func _tea_lash(c: UnitCard) -> void:
	var draw := c.art_time("attack", "draw")
	var hit := c.art_time("attack", "hit")
	if is_nan(draw) or is_nan(hit):
		return
	await _wait(maxf(draw - LASH_GATHER, 0.0))
	# a stream of tea rises out of the cup to her hovering hand...
	var arc := _fountain(_cup(c), _bend(c, "L"), CUP_CLEAR, 0.06)
	var grow := [0.0]
	create_tween().tween_method(func(v: float) -> void: grow[0] = v, 0.0, 1.0, LASH_GATHER * 0.5)
	var stream := effects.tea_strand(func(t: float) -> Vector3: return arc.call(t * grow[0]), 0.018, 0.3)
	await _wait(LASH_GATHER)
	# ...and snaps off the surface as she whips the hand up, the rope following it
	stream.stop()
	var rope := effects.tea_ribbon(_bend(c, "L"), 0.022, 0.32)
	await _wait(hit - draw)
	rope.stop()


## Warm Pour and Steady Sip: the clip plays and its heal (or ward) follows on the
## clip's "hit", when the tea reaches the ally; the clip plays out after it.
func _tea_art(c: UnitCard, art_id: String, ally: Unit) -> void:
	_clip_time = 0.0
	c.play_art(art_id)
	var hit := _moment(c, art_id, "hit", 1.0)
	if art_id == "warm_pour":
		_warm_pour_show(c, ally, hit)
	else:
		_steady_sip_show(c, ally, hit)
	await _wait(hit)
	_show_until = _moment(c, art_id, "end", hit + 0.6)


## Warm Pour: on "rise" a ribbon of tea lifts out of the cup, arcs over and loops
## round both hands; on "send" it flows across to the ally in a soft arc and wraps them in a
## rising spiral, and on "end" it fades into light on them.
func _warm_pour_show(c: UnitCard, ally: Unit, hit: float) -> void:
	var rise := _moment(c, "warm_pour", "rise", 1.0)
	var send := _moment(c, "warm_pour", "send", rise + 1.0)
	var end := _moment(c, "warm_pour", "end", hit + 0.6)
	var cup := _cup(c)
	await _wait(rise)
	_tea_flow(_fountain(cup, _bend(c, "L"), CUP_CLEAR, 0.08), 0.45, 0.02, 0.45)
	await _wait(0.4)
	var hands := [effects.tea_ribbon(_bend(c, "L"), 0.02, 0.55), effects.tea_ribbon(_bend(c, "R"), 0.02, 0.55)]
	await _wait(send - _clip_time)
	for h in hands:
		h.stop()
	var left := _bend(c, "L")
	var right := _bend(c, "R")
	var palms := func() -> Vector3: return ((left.call() as Vector3) + (right.call() as Vector3)) * 0.5
	var r := (ally.radius if ally != null else 0.3) * 1.15
	var at := _chest(ally) if ally != null else cup
	var start := func() -> Vector3: return (at.call() as Vector3) + Vector3(r, -0.25, 0)
	var arrive := maxf(hit - send - 0.25, 0.3)
	_tea_flow(_arc(palms, start, 0.35), arrive, 0.024, 0.5)
	await _wait(arrive)
	_tea_flow(_spiral(at, r, -0.25, 0.5, 2.5), end - _clip_time, 0.022, 0.5)
	await _wait(end - _clip_time)
	effects.tea_sparkles((at.call() as Vector3) + Vector3(0, 0.25, 0), r)


## Steady Sip: on "lift" two fingers draw one thin thread up out of the cup; it lobs
## over to the ally in a gentle arc, circles them once at chest height and settles
## into the blue ward on "hit".
func _steady_sip_show(c: UnitCard, ally: Unit, hit: float) -> void:
	var lift := _moment(c, "steady_sip", "lift", 1.0)
	var cup := _cup(c)
	await _wait(lift)
	var r := (ally.radius if ally != null else 0.3) * 1.1
	var at := _chest(ally) if ally != null else cup
	var start := func() -> Vector3: return (at.call() as Vector3) + Vector3(r, 0, 0)
	var across := (hit - lift) * 0.55
	_tea_thread(_fountain(cup, start, SIP_RISE, 0.25), across, 0.009)
	await _wait(across)
	_tea_flow(_spiral(at, r, 0.0, 0.0, 1.0), hit - _clip_time, 0.009, 0.45)
	await _wait(hit - _clip_time)
	if ally != null:
		lights.shimmer(at.call(), ally.radius * lights.bubble_scale, WARD_BLUE)


## Tea Break: the camera pushes in. On "rise" a column of tea climbs out of her cup
## and above her; on "ring" it unwinds into a ring orbiting her as she turns; on
## "burst" the ring bursts out over the circle (an amber ring runs across the floor);
## on "hit" a ribbon peels off round every ally in it under a soft warm rain (the
## heals follow); on "return" the last of it streams back into her cup and the
## camera eases back out.
func _tea_break(c: UnitCard, e: Dictionary) -> void:
	var u: Unit = e.unit
	var area := _battle.around(u, "tea_break")
	var allies := _battle.allies_in(u, area)
	await camera.push_in(c.global_position, signature_zoom)
	_clip_time = 0.0
	c.play_art("tea_break")
	var rise := _moment(c, "tea_break", "rise", 1.2)
	var ring := _moment(c, "tea_break", "ring", rise + 1.0)
	var burst := _moment(c, "tea_break", "burst", ring + 1.2)
	var hit := _moment(c, "tea_break", "hit", burst + 0.2)
	var back := _moment(c, "tea_break", "return", hit + 1.0)
	_tea_break_show(c, allies, area.radius, [rise, ring, burst, hit, back])
	await _wait(hit)
	_ease_back_after(c, back)
	_show_until = back + 0.6


func _tea_break_show(c: UnitCard, allies: Array[Unit], radius: float, moments: Array) -> void:
	var rise: float = moments[0]
	var ring: float = moments[1]
	var burst: float = moments[2]
	var hit: float = moments[3]
	var back: float = moments[4]
	var cup := _cup(c)
	var feet := func() -> Vector3: return c.global_position
	await _wait(rise)
	# the column: three strands twisting up out of the cup
	for k in 3:
		_tea_flow(_spiral(cup, 0.07, 0.0, 0.55, 1.5, TAU * k / 3.0), ring - rise, 0.022, 0.6)
	await _wait(ring - _clip_time)
	# the ring orbiting her as she turns, then bursting out over the circle
	for k in 3:
		_tea_flow(_spiral(feet, TEA_RING_RADIUS, TEA_RING_HEIGHT, 0.0, (burst - ring) * 0.55, TAU * k / 3.0),
			burst - ring, 0.026, 0.55)
	await _wait(burst - _clip_time)
	lights.ground_ring(c.global_position, TEA_AMBER)
	for k in 6:
		var a := TAU * k / 6.0
		var out := func(t: float) -> Vector3:
			var r := lerpf(TEA_RING_RADIUS, radius, t)
			return c.global_position + Vector3(cos(a + t * 0.6) * r, TEA_RING_HEIGHT - 0.3 * t, sin(a + t * 0.6) * r)
		_tea_flow(out, hit - burst + 0.1, 0.024, 0.3)
	await _wait(hit - _clip_time)
	# round every ally in the circle, under a warm rain
	effects.tea_rain(c.global_position, radius, back - hit)
	for o in allies:
		var r := o.radius * 1.15
		_tea_flow(_spiral(_chest(o), r, -0.3, 0.6, 2.0), back - hit - 0.1, 0.02, 0.45)
		_sparkle_after(_chest(o), back - hit - 0.1, r)
	await _wait(back - _clip_time)
	# what's left streams home into her cup
	for k in 3:
		var a := TAU * k / 3.0 + 0.4
		var from := func() -> Vector3: return c.global_position + Vector3(cos(a) * 0.9, 0.35, sin(a) * 0.9)
		_tea_flow(_fountain(from, cup, 0.35, CUP_CLEAR), 0.55, 0.018, 0.4)


func _sparkle_after(at: Callable, seconds: float, radius: float) -> void:
	await _wait(seconds)
	effects.tea_sparkles(at.call(), radius)


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


# --- Umbrella -----------------------------------------------------------------

## Lunge's lead-in: he couches the umbrella and paws the floor; the dash and the
## strike that follow are his (see `_charge`, `_strike`).
func _lunge(c: UnitCard) -> void:
	_charging = c.unit
	await c.play_once("lunge", false)


## Lunge's dash: the couched run loop along the path at the pace it was authored for.
func _charge(c: UnitCard, path: Array) -> void:
	var speed := _moment(c, "lunge_run", "speed", walk_speed)
	c.play("lunge_run")
	for k in range(1, path.size()):
		var a: Vector2 = path[k - 1]
		var b: Vector2 = path[k]
		c.face_along(b - a)
		var tw := create_tween()
		tw.tween_property(c, "position", BattleSpace.to_world(b), maxf(a.distance_to(b) / speed, 0.02))
		await tw.finished


## Canopy: the umbrella springs open over him; on "open" each neighbour it shelters
## shimmers and shows it is in Half Cover.
func _canopy(c: UnitCard) -> void:
	var u := c.unit
	c.play_art("canopy")
	var open := _moment(c, "canopy", "open", 1.2)
	await _wait(open)
	for o in _battle.field.living_units():
		if o.status.has("canopy") and o.faction == u.faction and u.is_adjacent(o):
			var at := card(o).global_position + Vector3(0, _body_height(o), 0)
			lights.shimmer(at, o.radius * lights.bubble_scale, CANOPY_TINT)
			effects.float_text(at + Vector3(0, 0.5, 0), "Half Cover", CANOPY_TINT)
	await _wait(c.clip_length("canopy") - open)


## Raincheck: he turns to the nearest enemy that can shoot, snaps the umbrella open
## (the camera pushed in) and twirls it as rain falls over the circle he covers,
## plants it as a shield on "shield" (the camera easing back out) and closes it with a
## bow on "end".
func _raincheck(c: UnitCard, e: Dictionary) -> void:
	var u: Unit = e.unit
	var shooter := _nearest_shooter(u)
	if shooter != null:
		c.face_along(shooter.pos - u.pos)
	var radius := float(Arts.get_art("raincheck").radius)
	await camera.push_in(c.global_position, signature_zoom)
	c.play_art("raincheck")
	var open := _moment(c, "raincheck", "open", 1.1)
	var shield := _moment(c, "raincheck", "shield", open + 1.6)
	var end := _moment(c, "raincheck", "end", shield + 1.4)
	await _wait(open)
	lights.ground_ring(c.global_position, RAIN_TINT)
	effects.rain(c.global_position, radius, end - open)
	await _wait(shield - open)
	camera.ease_back(c.global_position, 0.5)
	await _wait(c.clip_length("raincheck") - shield)


## The nearest living enemy with a ranged attack, or null.
func _nearest_shooter(u: Unit) -> Unit:
	var best: Unit = null
	for o in _battle.field.living_units():
		if o.faction == Defs.Faction.ENEMY and o.attack_range > Defs.MELEE_REACH 				and (best == null or o.pos.distance_to(u.pos) < best.pos.distance_to(u.pos)):
			best = o
	return best

