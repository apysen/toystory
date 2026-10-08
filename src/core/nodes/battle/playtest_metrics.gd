class_name PlaytestMetrics
extends Node

## Records the playtest numbers vertical_slice_plan.md section 26 asks for and
## writes one JSON file per battle for later comparison.

## Folder under user:// the per-battle files are written to.
@export var output_folder := "user://playtests"
## A Large unit with this many destinations or fewer counts as path-blocked.
@export var blocked_destination_limit := 3

var threat_inspections := 0
var vacuum_blocked := 0
var _hp_errors: Array[int] = []
var _started_ms := 0


func begin() -> void:
	threat_inspections = 0
	vacuum_blocked = 0
	_hp_errors.clear()
	_started_ms = Time.get_ticks_msec()


func record_selection(u: Unit, destinations: int) -> void:
	if u.is_large() and destinations <= blocked_destination_limit:
		vacuum_blocked += 1


## Compares each player unit's predicted HP from before the Enemy Phase with what it
## actually has afterwards.
func record_predictions(predicted: Dictionary) -> void:
	for u: Unit in predicted:
		_hp_errors.append(absi(int(predicted[u]) - u.hp))


func summary(battle: Battle) -> Dictionary:
	var avg := 0.0
	for e in _hp_errors:
		avg += e
	if not _hp_errors.is_empty():
		avg /= _hp_errors.size()
	var out := battle.stats.duplicate()
	out.merge({
		"turns": battle.turn,
		"duration_s": (Time.get_ticks_msec() - _started_ms) / 1000.0,
		"avg_predicted_hp_error": snappedf(avg, 0.01),
		"threat_inspections": threat_inspections,
		"recruitment_skipped": not battle.recruited,
		"vacuum_path_blocked": vacuum_blocked,
		"victory": battle.phase == Defs.Phase.VICTORY,
	})
	return out


func save(m: Dictionary) -> void:
	DirAccess.make_dir_recursive_absolute(output_folder)
	var stamp := Time.get_datetime_string_from_system().replace(":", "-")
	var f := FileAccess.open("%s/%s.json" % [output_folder, stamp], FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(m, "  "))
