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
// Teacup's tea, marked 3 in UV2.y with its radius in UV2.x (0 middle .. 1 edge): one
// plain tea brown, heaving in waves that run out from the middle as it sloshes
// (`tea_slosh`, 0 calm .. 1 sloshing hard: she's running, hit or bending it). The
// game tips the whole surface about in the cup as well (TeaLevel).
instance uniform float tea_slosh = 0.0;
// Cloth on spring bones (UnitSprings) also ripples a little in a breeze: each vertex
// by its cloth sway weight in UV2.x (0 pinned .. 1 at the hem). 0 off, 1 on.
instance uniform float cloth_ripple = 0.0;
const float RIPPLE = 0.0035;
uniform vec3 tea_surface : source_color = vec3(0.443, 0.212, 0.086);
// Metres the waves heave at the edge at full slosh (UnitTea.WAVE keeps the tilt
// inside the rim with this much to spare).
const float TEA_WAVE = 0.002;

float bayer4(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	int i = q.x + q.y * 4;
	const float m[16] = float[](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[i] + 0.5) / 16.0;
}

void vertex() {
	float tag = 1.0 - UV2.y;
	if (tag > 2.5) {
		// waves running out from the middle while it sloshes
		VERTEX.y += tea_slosh * TEA_WAVE * UV2.x * sin(UV2.x * 11.0 - TIME * 9.0);
	} else if (tag < 0.5 && cloth_ripple > 0.0) {
		// a slow ripple running down the cloth, strongest at the hem
		float w = UV2.x * cloth_ripple * RIPPLE;
		VERTEX.x += w * sin(TIME * 1.7 + VERTEX.y * 11.0 + VERTEX.z * 5.0);
		VERTEX.z += w * cos(TIME * 1.3 + VERTEX.y * 9.0 + VERTEX.x * 5.0);
	}
}

void fragment() {
	if (fade < 0.999 && bayer4(FRAGCOORD.xy) > fade) {
		discard;
	}
	float slice = 1.0 - UV2.y;   // glTF's V is flipped on import: untouched faces read 0
	vec3 c = texture(palette, UV).rgb;
	if (slice > 2.5) {
		c = tea_surface;
	} else if (slice > 0.5) {
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
