class_name SurfaceLibrary
extends RefCounted

## Materials for the diorama, built once from assets/textures/surfaces. Every
## surface is mapped in world space (triplanar), so pieces of any size share a
## consistent texel density without UV unwrapping, and each piece can tint its own
## copy (book cloth, paint).

const DIR := "res://assets/textures/surfaces/"

## name -> [metres per texture repeat, metallic, normal strength]
const SURFACES := {
	"wood": [7.2, 0.0, 0.8],
	"timber": [4.0, 0.0, 0.5],
	"paint": [6.0, 0.0, 0.4],
	"fabric": [1.6, 0.0, 0.8],
	"metal": [4.0, 0.7, 0.4],
	"chrome": [2.0, 1.0, 0.2],
	"card": [1.4, 0.0, 0.7],
	"cloth": [0.8, 0.0, 0.5],
	"pages": [0.35, 0.0, 0.4],
	"spill": [3.0, 0.0, 0.3],
}

static var _cache := {}


## The shared material for a surface, optionally tinted (tinted copies are cached too).
static func get_material(surface: String, tint := Color.WHITE) -> StandardMaterial3D:
	var key := "%s:%s" % [surface, tint.to_html()]
	if _cache.has(key):
		return _cache[key]
	var cfg: Array = SURFACES[surface]
	var m := StandardMaterial3D.new()
	m.albedo_texture = _tex(surface + "_albedo")
	m.albedo_color = tint
	m.normal_enabled = true
	m.normal_texture = _tex(surface + "_normal")
	m.normal_scale = cfg[2]
	m.roughness_texture = _tex(surface + "_rough")
	m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
	m.metallic = cfg[1]
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_triplanar_sharpness = 4.0
	var s := 1.0 / float(cfg[0])
	m.uv1_scale = Vector3(s, s, s)
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	if surface == "spill":
		m.clearcoat_enabled = true
		m.clearcoat = 1.0
		m.clearcoat_roughness = 0.05
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.albedo_color.a = 0.88
	_cache[key] = m
	return m


## An untextured satin colour (painted plastic, tape, rubber).
static func plain(c: Color, roughness := 0.55, metallic := 0.0) -> StandardMaterial3D:
	var key := "plain:%s:%.2f:%.2f" % [c.to_html(), roughness, metallic]
	if _cache.has(key):
		return _cache[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = roughness
	m.metallic = metallic
	_cache[key] = m
	return m


static func _tex(name: String) -> Texture2D:
	var path := DIR + name + ".png"
	return load(path) if ResourceLoader.exists(path) else null
