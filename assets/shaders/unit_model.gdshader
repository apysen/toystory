// HD-2D unit model: a 3D unit lit like the sprite cards around it, so the two read
// as one cast: room light with a soft wrap, a little self-light under the desk's
// shadow, a rim from behind, and the model's own glow (the lamp's shade, lantern).
shader_type spatial;
render_mode diffuse_lambert_wrap, specular_disabled;

// 16x16 palette of 4x4 swatches: sampled nearest so every face keeps its exact colour.
uniform sampler2D palette : source_color, filter_nearest, repeat_disable;
// Same layout; black except the swatches that glow.
uniform sampler2D glow : source_color, filter_nearest, repeat_disable;
uniform float glow_energy = 1.6;
// Matches unit_card.gdshader.
uniform float self_light = 0.28;
uniform float rim_amount = 0.3;
// 1 = solid; below 1 dissolves with the same dither the cards fade with (Broken).
instance uniform float fade = 1.0;

float bayer4(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	int i = q.x + q.y * 4;
	const float m[16] = float[](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[i] + 0.5) / 16.0;
}

void fragment() {
	if (fade < 0.999 && bayer4(FRAGCOORD.xy) > fade) {
		discard;
	}
	vec3 c = texture(palette, UV).rgb;
	ALBEDO = c;
	EMISSION = c * self_light + texture(glow, UV).rgb * glow_energy;
	ROUGHNESS = 1.0;
	RIM = rim_amount;
	RIM_TINT = 0.6;
	BACKLIGHT = vec3(0.35);
}
