// HD-2D unit card: pixel art lit by the room, sorted as one object.
shader_type spatial;
render_mode cull_disabled, diffuse_lambert_wrap, specular_disabled, skip_vertex_transform;

#include "res://assets/shaders/unit_card.gdshaderinc"

// A little self-light keeps faces readable under the desk's shadow.
uniform float self_light = 0.28;
// Soft rim from behind, so figures separate from the floorboards.
uniform float rim_amount = 0.3;

void vertex() {
	vec3 world = card_world(UV, NODE_POSITION_WORLD, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	// The card always faces the viewer: light it as if it did.
	NORMAL = vec3(0.0, 0.0, 1.0);
	v_anchor_depth = card_anchor_depth(NODE_POSITION_WORLD, VIEW_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX);
	UV = sheet_uv(UV, vec2(textureSize(sheet, 0)));
}

void fragment() {
	vec4 c = texture(sheet, UV);
	if (c.a < 0.5 || (fade < 0.999 && bayer4(FRAGCOORD.xy) > fade)) {
		discard;
	}
	ALBEDO = c.rgb * tint.rgb;
	EMISSION = c.rgb * tint.rgb * self_light;
	ROUGHNESS = 1.0;
	RIM = rim_amount;
	RIM_TINT = 0.6;
	BACKLIGHT = vec3(0.35);
	DEPTH = v_anchor_depth;
}
