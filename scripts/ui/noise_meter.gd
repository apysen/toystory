class_name NoiseMeter
extends Control
## Six-pip shared Noise meter. Turns violet while a Gaze is active.

var value := 0
var gaze := false


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
		var col := Color("3a3a44")
		if on:
			col = Color("f0c040") if i < n - 2 else Color("f07040")
		if gaze:
			col = Color("b090ff") if on else Color("4a3a66")
		draw_rect(r, col)
		draw_rect(r, Color.BLACK, false, 1.0)
