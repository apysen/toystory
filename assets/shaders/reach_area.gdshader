// A movement area on the floor (the controlled unit's, or an inspected enemy's):
// a bright rim that fades inward, a nearly clear inside, and a fainter rim where
// furniture, another unit or the map's edge stops it rather than the move budget.
// It takes the room's light, so it dims in the desk's shade like the floor under it.
// The masks come from ReachAreaTexture.
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, specular_disabled;

uniform vec4 rim_color : source_color = vec4(1.0, 0.95, 0.82, 1.0);
uniform vec4 fill_color : source_color = vec4(1.0, 0.95, 0.82, 0.05);
// Peak opacity of the inward glow at the rim (it fades inward over the glow mask).
uniform float glow_alpha = 0.22;
// Rim width in metres; never thinner than rim_min_px on screen.
uniform float rim_width = 0.035;
uniform float rim_min_px = 1.6;
// Opacity of the rim where something other than the budget stops the area.
uniform float blocked_rim = 0.35;
// Share of the colour that glows on its own, so it stays readable in shade.
uniform float emission = 0.45;
// A slow brightening that travels along the rim.
uniform float shimmer = 0.25;
uniform float shimmer_speed = 1.4;

uniform sampler2D shape_tex : filter_linear, repeat_disable;
uniform sampler2D glow_tex : filter_linear, repeat_disable;
uniform vec2 tex_origin;
uniform vec2 tex_size = vec2(17.0, 13.0);

// Grow-in: the area shows within `reveal` metres of `center`, with a bright front.
uniform vec2 center;
uniform float reveal = 1000.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = vec2(world_pos.x, -world_pos.z);
	vec2 uv = (p - tex_origin) / tex_size;
	vec2 s = texture(shape_tex, uv).rg;
	float inside = s.r;
	// Signed distance to the edge, roughly in metres (the mask climbs about two
	// units per metre across the edge), negative inside.
	float sd = (0.5 - inside) * 0.5;
	float aa = max(fwidth(sd), 1e-5);
	float half_w = max(rim_width * 0.5, aa * rim_min_px * 0.5);
	float rim = 1.0 - smoothstep(half_w - aa, half_w + aa, abs(sd + half_w * 0.6));
	float wall = smoothstep(0.08, 0.45, s.g);
	rim *= mix(1.0, blocked_rim, wall);
	float in_mask = smoothstep(aa, -aa, sd);
	// The inward glow: strongest at the rim, gone a few tens of centimetres in.
	float g = texture(glow_tex, uv).r;
	float glow = in_mask * smoothstep(0.95, 0.5, g) * glow_alpha * mix(1.0, blocked_rim, wall);
	float wave = 0.5 + 0.5 * sin(dot(p, vec2(2.1, 1.3)) - TIME * shimmer_speed);
	rim *= 1.0 - shimmer + shimmer * wave;
	// Grow-in from the unit.
	float d = length(p - center);
	float shown = smoothstep(reveal, reveal - 0.5, d);
	float front = (1.0 - smoothstep(0.0, 0.35, abs(d - reveal + 0.2))) * step(reveal, 900.0);
	float a = max(max(rim * rim_color.a, glow), fill_color.a * in_mask) * shown;
	a = max(a, front * in_mask * 0.55);
	if (a < 0.004) {
		discard;
	}
	float to_rim = clamp(rim * 1.4 + front, 0.0, 1.0);
	vec3 col = mix(fill_color.rgb, rim_color.rgb, to_rim);
	ALBEDO = col;
	EMISSION = col * emission;
	ALPHA = a;
}
