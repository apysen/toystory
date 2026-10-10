// Light that Arts throw into the diorama (ArtLights): beams, shells, glare and
// rings, all additive so they brighten whatever is behind them and never cast or
// catch shadows. `strength` fades an instance in and out. No fog: the room's fog
// would tint the whole quad and show its square edges.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

// 0 beam: a cylinder bright down its core, soft at both ends (UV.y along it)
// 1 shell: a bubble, bright at its rim (fresnel), faint across its face
// 2 glare: a camera-facing disc of light, brightest in the middle
// 3 ring: a thin ring on the floor at `ring` (0 centre .. 1 the quad's edge)
// 4 volume: a column of light from above, brighter toward the floor
uniform int mode = 0;
uniform vec4 color : source_color = vec4(1.0, 0.86, 0.55, 1.0);
// Mode 0: how much of each end fades out (0..0.5).
uniform float end_fade = 0.15;
uniform bool billboard = false;
instance uniform float strength = 1.0;
instance uniform float ring = 0.5;

void vertex() {
	if (billboard) {
		MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
			INV_VIEW_MATRIX[0] * length(MODEL_MATRIX[0].xyz),
			INV_VIEW_MATRIX[1] * length(MODEL_MATRIX[1].xyz),
			INV_VIEW_MATRIX[2] * length(MODEL_MATRIX[2].xyz),
			MODEL_MATRIX[3]);
	}
}

void fragment() {
	float facing = abs(dot(normalize(NORMAL), normalize(VIEW)));
	float a = 1.0;
	if (mode == 0) {
		a = smoothstep(0.0, end_fade, UV.y) * smoothstep(1.0, 1.0 - end_fade, UV.y) * pow(facing, 1.5);
	} else if (mode == 1) {
		a = pow(1.0 - facing, 2.5) + 0.06;
	} else if (mode == 2) {
		float d = length(UV - vec2(0.5)) * 2.0;
		a = pow(max(1.0 - d, 0.0), 2.2);
	} else if (mode == 3) {
		float d = length(UV - vec2(0.5)) * 2.0;
		a = exp(-pow((d - ring) / 0.05, 2.0)) * (1.0 - ring * 0.6);
	} else {
		a = mix(0.05, 0.4, UV.y) * pow(facing, 1.2);
	}
	ALBEDO = color.rgb * a * strength;
}
