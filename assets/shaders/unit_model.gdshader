// HD-2D unit model: a 3D unit lit like the sprite cards around it, so the two read
// as one cast: room light with a soft wrap, a little self-light under the desk's
// shadow, a rim from behind, and the model's own glow (the lamp's shade, lantern).
shader_type spatial;
render_mode diffuse_lambert_wrap, specular_disabled;

// 16x16 palette of 4x4 swatches, or a detail atlas with the swatches in its corner
// and line art beside them (the Toaster's): faces sample a swatch's middle, so
// every face keeps its exact colour, and the line art is smoothed, not stepped.
uniform sampler2D palette : source_color, filter_linear, repeat_disable;
// Same layout; black except the swatches that glow.
uniform sampler2D glow : source_color, filter_linear, repeat_disable;
uniform float glow_energy = 1.6;
// Matches unit_card.gdshader.
uniform float self_light = 0.28;
uniform float rim_amount = 0.3;
// 1 = solid; below 1 dissolves with the same dither the cards fade with (Broken).
instance uniform float fade = 1.0;
// Multiplies the glow: an Art flares it (Lamp's Flashbulb pops the shade white-hot).
instance uniform float glow_boost = 1.0;
// The Toaster's slices, marked in UV2.y (1 front, 2 back): x and y hide the front
// and back slice (launched, not yet reloaded), z and w brown them (0..1, toasted).
instance uniform vec4 toast_state = vec4(0.0);
// What toasting does to a slice's colours (toast.glb is built in them).
const vec3 TOASTED = vec3(0.8, 0.66, 0.52);

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
	float slice = 1.0 - UV2.y;   // glTF's V is flipped on import: untouched faces read 0
	vec3 c = texture(palette, UV).rgb;
	if (slice > 0.5) {
		bool front = slice < 1.5;
		if ((front ? toast_state.x : toast_state.y) > 0.5) {
			discard;
		}
		c *= mix(vec3(1.0), TOASTED, front ? toast_state.z : toast_state.w);
	}
	ALBEDO = c;
	EMISSION = c * self_light + texture(glow, UV).rgb * glow_energy * glow_boost;
	ROUGHNESS = 1.0;
	RIM = rim_amount;
	RIM_TINT = 0.6;
	BACKLIGHT = vec3(0.35);
}
