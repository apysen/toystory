class_name BattleAudio
extends Node

## The battle's sound: a small pool of one-shot effect players for
## assets/audio/sfx and the looping battle theme. Missing files are skipped
## silently, so the battle runs before the audio pass is finished.

const ART_SOUNDS := {
	"guard_beam": "lamp_flash", "flashbulb": "lamp_flash", "spotlight": "lamp_flash", "pin": "staple", "staple_burst": "staple",
	"staple_storm": "staple",
	"eject": "toaster_pop", "flash_bake": "toaster_heat", "overheat": "toaster_heat", "warm_pour": "teacup_pour", "steady_sip": "teacup_pour",
	"suction": "vacuum_suction", "blowback": "vacuum_blow", "lunge": "umbrella_snap", "canopy": "umbrella_snap",
	"cutting_line": "cutter_slice",
}
const ATTACK_SOUNDS := {
	"stapler": "staple", "toaster": "toaster_pop", "umbrella": "umbrella_snap", "rubber": "rubber_snap",
	"tape": "tape_rip", "cutter": "cutter_slice",
}

@export_group("Effects")
@export_dir var sfx_folder := "res://assets/audio/sfx"
## Effects that can overlap before the oldest is cut off.
@export_range(1, 32) var voices := 8
@export var default_volume_db := -6.0

@export_group("Music")
## The room's battle theme. Plays on loop for the whole battle.
@export var battle_theme: AudioStream
@export var music_volume_db := -14.0
@export var music_player: AudioStreamPlayer

var _players: Array[AudioStreamPlayer] = []
var _cache := {}
var _next := 0


func _ready() -> void:
	for i in voices:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)


func play(sound: String, volume_db := NAN) -> void:
	if sound == "":
		return
	if not _cache.has(sound):
		var path := "%s/%s.wav" % [sfx_folder, sound]
		_cache[sound] = load(path) if ResourceLoader.exists(path) else null
	var stream: AudioStream = _cache[sound]
	if stream == null:
		return
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = stream
	p.volume_db = default_volume_db if is_nan(volume_db) else volume_db
	p.play()


func start_music() -> void:
	if battle_theme == null or music_player == null:
		return
	if "loop" in battle_theme:
		battle_theme.set("loop", true)
	music_player.stream = battle_theme
	music_player.volume_db = music_volume_db
	music_player.play()


func stop_music(fade_seconds := 0.6) -> void:
	if music_player == null or not music_player.playing:
		return
	var tw := create_tween()
	tw.tween_property(music_player, "volume_db", -60.0, fade_seconds)
	tw.tween_callback(music_player.stop)


static func attack_sound(u: Unit) -> String:
	return ATTACK_SOUNDS.get(u.sprite, ATTACK_SOUNDS.get(u.id, ""))
