class_name BattleSpeedSettings
extends Node

## How fast battle playback runs: the parts you watch (moves and strikes playing
## out, the Enemy Phase, banners, camera glides) run at this multiple of real time.
## Steering your own unit always runs at the natural pace. Remembered between
## sessions; the pause menu steps through `steps`.

signal changed

const SPEED_KEY := "battle_speed"

## The speeds the pause menu steps through, slowest first.
@export var steps: Array[float] = [1.0, 1.5, 2.0, 3.0]
## Speed on the very first run, before anything is saved.
@export var default_speed := 1.0


func speed() -> float:
	return SettingsStore.read_number(SPEED_KEY, default_speed)


func set_speed(value: float) -> void:
	SettingsStore.write_number(SPEED_KEY, value)
	changed.emit()


## Moves to the next speed in `steps`, wrapping back to the slowest.
func step_up() -> void:
	var current := speed()
	for s in steps:
		if s > current + 0.001:
			set_speed(s)
			return
	set_speed(steps[0])
