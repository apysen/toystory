// Shows a unit through furniture: drawn after everything opaque, it compares its
// anchor depth with the scene's depth and colours only the pixels where something
// stands between the camera and the unit.
shader_type spatial;
render_mode cull_disabled, unshaded, depth_test_disabled, depth_draw_never, skip_vertex_transform;

#include "res://assets/shaders/unit_card.gdshaderinc"

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
instance uniform vec4 silhouette_color : source_color = vec4(0.45, 0.7, 1.0, 0.6);

void vertex() {
	vec3 world = card_world(UV, NODE_POSITION_WORLD, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	v_anchor_depth = card_anchor_depth(NODE_POSITION_WORLD, VIEW_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX);
	UV = sheet_uv(UV, vec2(textureSize(sheet, 0)));
}

void fragment() {
	vec4 c = texture(sheet, UV);
	if (c.a < 0.5) {
		discard;
	}
	float scene = texture(depth_texture, SCREEN_UV).r;
	// Reverse-Z: bigger is nearer. Only where the scene is nearer than the unit.
	if (scene <= v_anchor_depth + 0.00002) {
		discard;
	}
	ALBEDO = silhouette_color.rgb;
	ALPHA = silhouette_color.a * fade;
}
