// A droplet of Teacup's tea (TeaFX.drops): a solid bead with a soft rim, facing the
// camera at its particle's size, in the particle's colour (her palette's tea, given
// in sRGB). Particles not yet born come through black, so they're thrown away (no
// tea is black). No fog: the room's fog would show each bead's square.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

void vertex() {
	mat4 face = mat4(normalize(INV_VIEW_MATRIX[0]), normalize(INV_VIEW_MATRIX[1]),
		normalize(INV_VIEW_MATRIX[2]), MODEL_MATRIX[3]);
	float size = length(MODEL_MATRIX[0].xyz);
	MODELVIEW_MATRIX = VIEW_MATRIX * face * mat4(vec4(size, 0, 0, 0), vec4(0, size, 0, 0),
		vec4(0, 0, size, 0), vec4(0, 0, 0, 1));
}

void fragment() {
	if (COLOR.a < 0.01 || dot(COLOR.rgb, vec3(1.0)) < 0.01) {
		discard;
	}
	float d = length(UV - vec2(0.5)) * 2.0;
	ALBEDO = pow(COLOR.rgb, vec3(2.2));
	ALPHA = (1.0 - smoothstep(0.7, 1.0, d)) * COLOR.a;
}
