// Teacup's bent tea (TeaRibbon) and the puddle her cup pours out when she's Broken.
// The same tea as in her cup, the owner's pick (2026-10-11): her tea brown with the
// tan of its crest ring running down the middle like the light in it; it doesn't
// glow. See-through at its edges and its tail; no fog (the room's fog would tint
// the strip).
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

// 0 ribbon: UV.x runs from the head (0) to the tail (1), UV.y across it
// 1 puddle: a soft round pool on the floor (UV across the quad)
uniform int mode = 0;
// her palette's "brown", "brown_dark" and "tan" (the crest ring)
uniform vec4 tea : source_color = vec4(0.647, 0.322, 0.145, 1.0);
uniform vec4 tea_dark : source_color = vec4(0.443, 0.212, 0.086, 1.0);
uniform vec4 crest : source_color = vec4(0.788, 0.537, 0.349, 1.0);
instance uniform float strength = 1.0;

void fragment() {
	if (mode == 0) {
		float across = abs(UV.y * 2.0 - 1.0);
		float body = 1.0 - smoothstep(0.5, 1.0, across);
		float tail = 1.0 - smoothstep(0.55, 1.0, UV.x);
		// darker at the edges, the crest's tan flowing down the middle
		float shine = pow(1.0 - across, 3.0) * (0.6 + 0.4 * sin(UV.x * 28.0 - TIME * 11.0));
		ALBEDO = mix(mix(tea.rgb, tea_dark.rgb, smoothstep(0.4, 1.0, across)), crest.rgb, shine * 0.7);
		ALPHA = body * tail * strength * COLOR.a;
	} else {
		float d = length(UV - vec2(0.5)) * 2.0;
		float pool = 1.0 - smoothstep(0.75, 1.0, d);
		float sheen = 1.0 - smoothstep(0.0, 0.55, length(UV - vec2(0.38, 0.4)) * 2.0);
		ALBEDO = mix(tea_dark.rgb, crest.rgb, sheen * 0.45);
		ALPHA = pool * 0.85 * strength;
	}
}
