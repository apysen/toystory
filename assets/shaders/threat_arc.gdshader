// A pulsing arc from an enemy to the unit it could hit (Fortune's Weave style).
// UV.x runs from the enemy (0) to the target (1); UV.y across the ribbon. Bright
// pulses travel toward the target; `strength` (the hit chance) sets how bright.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, depth_test_disabled, shadows_disabled, blend_mix;

uniform float pulse_speed = 1.4;
uniform float pulse_count = 2.0;

void fragment() {
	float strength = COLOR.a;
	float across = 1.0 - abs(UV.y * 2.0 - 1.0);
	// The line is only a few pixels wide: keep it solid, with a soft edge.
	float core = smoothstep(0.0, 0.35, across);
	float band = fract(UV.x * pulse_count - TIME * pulse_speed);
	float glow = 0.35 + 0.65 * smoothstep(0.75, 1.0, band);
	// Fade in from the enemy and keep the head bright.
	float ends = smoothstep(0.0, 0.08, UV.x);
	ALBEDO = mix(COLOR.rgb, vec3(1.0), glow * 0.35);
	ALPHA = clamp(core * ends * (0.5 + 0.5 * strength) * (0.7 + 0.3 * glow), 0.0, 1.0);
}
