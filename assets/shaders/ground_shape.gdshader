// Markings painted on the floor: the movement area, range rings, cones, the Gaze
// circle and telegraphed lanes. One shader, one quad per marking; the shape is
// worked out per pixel from floor coordinates (metres, y up the map = world -z).
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, blend_mix;

// 0 disc or ring, 1 cone, 2 strip (lane), 3 cost field (movement area)
uniform int mode = 0;
uniform vec4 fill_color : source_color = vec4(0.3, 0.6, 1.0, 0.25);
uniform vec4 edge_color : source_color = vec4(0.6, 0.85, 1.0, 0.95);
uniform float edge_width = 0.06;
// Pulse speed; 0 holds steady.
uniform float pulse = 0.0;
// Diagonal hatching (telegraphs), stripes per metre; 0 for none.
uniform float hatch = 0.0;

uniform vec2 center;
uniform float radius = 1.0;
uniform float inner_radius = 0.0;

uniform vec2 dir = vec2(1.0, 0.0);
uniform float half_angle = 0.7;
uniform float cone_length = 2.0;

uniform vec2 seg_a;
uniform vec2 seg_b;
uniform float half_width = 0.4;

uniform sampler2D field_tex : filter_linear, repeat_disable;
uniform vec2 field_size = vec2(15.0, 11.0);
uniform float budget = 5.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float seg_dist(vec2 p, vec2 a, vec2 b) {
	vec2 ab = b - a;
	float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-6), 0.0, 1.0);
	return length(p - (a + ab * t));
}

void fragment() {
	vec2 p = vec2(world_pos.x, -world_pos.z);
	float sd = 1.0;
	if (mode == 0) {
		float d = length(p - center);
		sd = d - radius;
		if (inner_radius > 0.0) {
			sd = max(sd, inner_radius - d);
		}
	} else if (mode == 1) {
		vec2 q = p - center;
		float l = length(q);
		float ang = acos(clamp(dot(q / max(l, 1e-4), normalize(dir)), -1.0, 1.0));
		sd = max(l - cone_length, (ang - half_angle) * max(l, 0.3));
	} else if (mode == 2) {
		sd = seg_dist(p, seg_a, seg_b) - half_width;
	} else {
		float c = texture(field_tex, p / field_size).r;
		sd = c - budget;
	}
	float fill = 1.0 - smoothstep(-0.015, 0.015, sd);
	float edge = 1.0 - smoothstep(0.0, edge_width, abs(sd + edge_width * 0.5));
	float wave = pulse > 0.0 ? 0.7 + 0.3 * sin(TIME * pulse) : 1.0;
	float f_alpha = fill_color.a * fill;
	if (hatch > 0.0) {
		float s = fract((p.x + p.y) * hatch);
		f_alpha *= 0.45 + 0.55 * step(0.5, s);
	}
	float alpha = max(f_alpha, edge_color.a * edge) * wave;
	if (alpha < 0.01) {
		discard;
	}
	ALBEDO = mix(fill_color.rgb, edge_color.rgb, clamp(edge * 1.2, 0.0, 1.0));
	ALPHA = alpha;
}
