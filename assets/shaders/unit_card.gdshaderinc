// Shared pieces of the unit card shaders (adapted from the Kowloon project).
//
// A card is a 1x1 quad placed entirely in the vertex shader: the current frame's
// pixels are laid out around the foot pivot at PIXELS_PER_METRE and turned to
// face whatever is looking at it (the camera, or the sun in the shadow pass).
// Only the yaw turns; cards stay upright, as in HD-2D.
//
// The anchor depth keeps a card from being sliced by furniture: every fragment
// writes the depth of one point (mid-body, nudged toward the viewer), so a
// character is wholly in front of a desk leg or wholly behind it.

uniform sampler2D sheet : source_color, filter_nearest, repeat_disable;
uniform float pixels_per_metre = 128.0;
uniform float anchor_height = 0.4;
uniform float anchor_toward_camera = 0.35;
// How far the card leans back toward the viewer (0 upright, 1 facing it fully),
// so a steep camera still sees the character rather than a sliver.
uniform float lean = 0.0;

instance uniform vec4 region = vec4(0.0, 0.0, 128.0, 128.0); // frame rect in the sheet, pixels
instance uniform vec2 pivot = vec2(64.0, 120.0);              // foot point inside the frame, pixels
instance uniform float flip = 0.0;                            // 1 = mirrored about the pivot
instance uniform vec4 tint : source_color = vec4(1.0);
instance uniform float fade = 1.0;

varying float v_anchor_depth;

// World position of this vertex, turned toward the viewer whose inverse view
// matrix is given.
vec3 card_world(vec2 uv, vec3 node, mat4 inv_view) {
	vec2 px = uv * region.zw;
	float x = (px.x - pivot.x) / pixels_per_metre;
	if (flip > 0.5) {
		x = -x;
	}
	float y = (pivot.y - px.y) / pixels_per_metre;
	vec3 right = inv_view[0].xyz;
	right = normalize(vec3(right.x, 0.0, right.z) + vec3(1e-5, 0.0, 0.0));
	vec3 up = normalize(mix(vec3(0.0, 1.0, 0.0), inv_view[1].xyz, lean));
	return node + right * x + up * y;
}

vec2 sheet_uv(vec2 uv, vec2 sheet_size) {
	vec2 px = uv * region.zw;
	// Half-texel inset stops neighbouring frames bleeding in at the card edge.
	px = clamp(px, vec2(0.5), region.zw - vec2(0.5));
	return (region.xy + px) / sheet_size;
}

float card_anchor_depth(vec3 node, mat4 view, mat4 inv_view, mat4 proj) {
	vec3 back = inv_view[2].xyz;
	vec3 flat_back = normalize(vec3(back.x, 0.0, back.z) + vec3(1e-5, 0.0, 0.0));
	vec3 up = normalize(mix(vec3(0.0, 1.0, 0.0), inv_view[1].xyz, lean));
	vec3 anchor = node + up * anchor_height + flat_back * anchor_toward_camera;
	vec4 clip = proj * view * vec4(anchor, 1.0);
	return clip.z / clip.w;
}

float bayer4(vec2 p) {
	ivec2 i = ivec2(mod(p, 4.0));
	int idx = i.x + i.y * 4;
	int m[16] = int[](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(m[idx]) + 0.5) / 16.0;
}
