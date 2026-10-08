class_name NoiseMeter
extends Control

## Shared Noise meter: one pip per point up to the Gaze threshold. Turns violet
## while a Gaze is active.

@export var off_color := Color("3a3a44")
@export var on_color := Color("f0c040")
## The last two pips before the threshold.
@export var warning_color := Color("f07040")
@export var gaze_on_color := Color("b090ff")
@export var gaze_off_color := Color("4a3a66")

var value := 0
var gaze := false


func show_noise(noise: int, gaze_active: bool) -> void:
	value = noise
	gaze = gaze_active
	queue_redraw()


func _draw() -> void:
	var n := Defs.NOISE_THRESHOLD
	var w := size.x / n
	for i in n:
		var r := Rect2(i * w + 2, 4, w - 4, size.y - 8)
		var on := i < value
		var icon := SpriteLib.load_ui("noise_pip_gaze" if gaze and on else ("noise_pip_on" if on else "noise_pip_off"))
		if icon != null:
			var side := minf(r.size.x, r.size.y)
			var ir := Rect2(r.get_center() - Vector2(side, side) / 2, Vector2(side, side))
			draw_texture_rect(icon, ir, false)
			continue
		var col := off_color
		if on:
			col = on_color if i < n - 2 else warning_color
		if gaze:
			col = gaze_on_color if on else gaze_off_color
		draw_rect(r, col)
		draw_rect(r, Color.BLACK, false, 1.0)
