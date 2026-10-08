class_name Sfx
extends Node
## Small pool of AudioStreamPlayers for one-shot sound effects in
## assets/audio/sfx. Missing files are skipped silently.

const DIR := "res://assets/audio/sfx/"
const ART_SOUNDS := {
	"guard_beam": "lamp_flash", "flashbulb": "lamp_flash", "pin": "staple", "staple_burst": "staple",
	"eject": "toaster_pop", "flash_bake": "toaster_heat", "warm_pour": "teacup_pour", "steady_sip": "teacup_pour",
	"suction": "vacuum_suction", "blowback": "vacuum_blow", "lunge": "umbrella_snap", "canopy": "umbrella_snap",
	"cutting_line": "cutter_slice",
}
const ATTACK_SOUNDS := {
	"stapler": "staple", "toaster": "toaster_pop", "umbrella": "umbrella_snap", "rubber": "rubber_snap",
	"tape": "tape_rip", "cutter": "cutter_slice",
}

var _players: Array[AudioStreamPlayer] = []
var _cache := {}
var _next := 0


func _ready() -> void:
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)


func play(sound: String, volume_db := -6.0) -> void:
	if sound == "":
		return
	if not _cache.has(sound):
		var path := DIR + sound + ".wav"
		_cache[sound] = load(path) if ResourceLoader.exists(path) else null
	var stream: AudioStream = _cache[sound]
	if stream == null:
		return
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = stream
	p.volume_db = volume_db
	p.play()


static func attack_sound(u: Unit) -> String:
	return ATTACK_SOUNDS.get(u.sprite, ATTACK_SOUNDS.get(u.id, ""))
