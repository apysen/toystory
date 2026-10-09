// The edge of a Human Gaze: a curtain of light standing on the watched circle.
// Brightest at the floor, fading as it rises, with slow streaks drifting up so
// it reads as light rather than a solid wall. Nothing outside may cross it.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_add;

uniform vec4 light_color : source_color = vec4(0.82, 0.74, 1.0, 1.0);
uniform float intensity = 0.6;
uniform float streaks = 28.0;
// Height the light fades out by, in metres.
uniform float wall_height = 2.4;

varying float height;

void vertex() {
	height = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y;
}

void fragment() {
	float rise = clamp(height / wall_height, 0.0, 1.0);
	float fade = pow(1.0 - rise, 2.0);
	float s = sin(UV.x * streaks * 6.2831 + sin(UV.x * 7.0 + TIME * 0.7) * 2.0);
	float drift = 0.5 + 0.5 * sin(rise * 9.0 - TIME * 2.2 + UV.x * 40.0);
	float band = clamp(0.55 + 0.25 * s + 0.2 * drift, 0.0, 1.0);
	// A bright seam where the light meets the floor.
	float seam = (1.0 - smoothstep(0.0, 0.06, rise)) * 0.7;
	float pulse = 0.85 + 0.15 * sin(TIME * 2.4);
	ALBEDO = light_color.rgb * (fade * band + seam) * intensity * pulse;
}
