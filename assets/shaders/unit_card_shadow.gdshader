// Shadow caster for a unit card: drawn only into shadow maps. In the shadow pass
// the "viewer" is the light, so the card turns to face the sun by itself and the
// shadow stays a full silhouette at every camera angle.
shader_type spatial;
render_mode cull_disabled, unshaded, skip_vertex_transform;

#include "res://assets/shaders/unit_card.gdshaderinc"

void vertex() {
	vec3 world = card_world(UV, NODE_POSITION_WORLD, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	UV = sheet_uv(UV, vec2(textureSize(sheet, 0)));
}

void fragment() {
	vec4 c = texture(sheet, UV);
	if (c.a < 0.5 || (fade < 0.999 && bayer4(FRAGCOORD.xy) > fade)) {
		discard;
	}
	ALBEDO = vec3(0.0);
}
