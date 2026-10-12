class_name UnitSprings
extends Node
## A model's cloth moving with physics in the game: Godot spring bones
## (SpringBoneSimulator3D) on its cloth chains, so sleeves, cords, tassels, skirts,
## cape and mantle swing as the unit travels, turns and moves, lag behind and settle
## back onto the clip's pose. Physics is the game's alone (decided 2026-10-11): the
## clips keep their gravity hang (`settle()` in the Blender scripts) as the pose the
## springs move from, and the game tweens units and strips root motion, so only
## springs at runtime react to travel and turns.
##
## Built from `<model>_springs.json` beside the model (written by its Blender export,
## in Godot's frame): every chain's bones, their heads and tails, and the collider
## capsules round the body. Each chain collides with every capsule; where it already
## rests inside one (a cape hanging close against the body's rough envelope), it gets
## a slimmer copy that reaches just short of it, so it is never shoved out but still
## can't swing into the body. SpringLimit keeps each bone within its kind of cloth's
## swing of the clip. UnitModel adds one to a model
## that has the file: the Teacup's 20 chains (written by her animate script), and
## Lamp's cape, tabard and lantern, Stapler's cloak and scarf, Toaster's cape and
## Umbrella's cape, tabard and the gold drops round his hat's brim ("drop")
## (toy3d.export_springs).

## How each kind of cloth moves, by the start of its chain's name: stiffness (how
## hard it springs back to the clip), drag (how quickly it calms), gravity (extra sag
## while it swings), the most each link may swing off the clip in degrees (a chain's
## links add up: the sleeve's two-link drape swings 20 degrees at most), and the
## radius of its joints against the colliders (metres).
@export var cloth := {
	"sleeve": {"stiffness": 3.0, "drag": 0.6, "gravity": 0.2, "limit": 10.0, "radius": 0.015},
	"cord": {"stiffness": 1.5, "drag": 0.5, "gravity": 0.4, "limit": 25.0, "radius": 0.006},
	"tassel": {"stiffness": 1.5, "drag": 0.5, "gravity": 0.4, "limit": 30.0, "radius": 0.01},
	"skirt": {"stiffness": 4.0, "drag": 0.6, "gravity": 0.0, "limit": 10.0, "radius": 0.02},
	"cape": {"stiffness": 3.0, "drag": 0.6, "gravity": 0.0, "limit": 15.0, "radius": 0.02},
	"mantle": {"stiffness": 5.0, "drag": 0.6, "gravity": 0.0, "limit": 8.0, "radius": 0.015},
	"cloak": {"stiffness": 3.0, "drag": 0.6, "gravity": 0.0, "limit": 15.0, "radius": 0.02},
	"scarf": {"stiffness": 2.0, "drag": 0.5, "gravity": 0.0, "limit": 20.0, "radius": 0.02},
	"tabard": {"stiffness": 4.0, "drag": 0.6, "gravity": 0.0, "limit": 12.0, "radius": 0.02},
	"lantern": {"stiffness": 1.0, "drag": 0.35, "gravity": 1.0, "limit": 20.0, "radius": 0.03},
	"drop": {"stiffness": 1.5, "drag": 0.45, "gravity": 0.6, "limit": 30.0, "radius": 0.01},
}
## Metres a chain's joints are kept clear of a capsule at rest.
@export var rest_clearance := 0.004
## A capsule slimmed below this share of its radius to fit a chain is left out for it
## (the chain rests deep inside it, as a cord knotted into the tabard).
@export var least_slim := 0.4

var simulator: SpringBoneSimulator3D
var _skeleton: Skeleton3D
var _limiter: SpringLimit
## Bone index -> its chain's name.
var _chain_of: Dictionary = {}


## The springs file beside a model, or {} when it has none.
static func read(model_path: String) -> Dictionary:
	var path := model_path.get_basename() + "_springs.json"
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func _init(skeleton: Skeleton3D, data: Dictionary) -> void:
	name = "Springs"
	_skeleton = skeleton
	_build(data)


func _build(data: Dictionary) -> void:
	var recorder := SpringLimit.new()
	recorder.name = "SpringRecord"
	_skeleton.add_child(recorder)
	simulator = SpringBoneSimulator3D.new()
	simulator.name = "SpringBones"
	_skeleton.add_child(simulator)
	var limiter := SpringLimit.new()
	limiter.name = "SpringLimit"
	limiter.recorder = recorder
	_skeleton.add_child(limiter)

	var capsules: Array = data.get("capsules", [])
	## capsule name and radius (mm) -> its collider, so chains share them
	var made := {}

	var bones: Dictionary = data.get("bones", {})
	var chains: Dictionary = data.get("springs", {})
	var names := chains.keys()
	names.sort()
	simulator.setting_count = names.size()
	for i in names.size():
		var chain: Array = chains[names[i]]
		var kind := _kind(names[i])
		var last: Dictionary = bones[chain[chain.size() - 1]]
		simulator.set_root_bone_name(i, chain[0])
		simulator.set_end_bone_name(i, chain[chain.size() - 1])
		simulator.set_extend_end_bone(i, true)
		simulator.set_end_bone_direction(i, SkeletonModifier3D.BONE_DIRECTION_PLUS_Y)
		simulator.set_end_bone_length(i, _vec(last.tail).distance_to(_vec(last.head)))
		simulator.set_stiffness(i, float(kind.stiffness))
		simulator.set_drag(i, float(kind.drag))
		simulator.set_gravity(i, float(kind.gravity))
		simulator.set_radius(i, float(kind.radius))
		# the joints at rest: each bone's head and the last one's tail
		var joints: Array[Vector3] = []
		for bone in chain:
			joints.append(_vec(bones[bone].head))
		joints.append(_vec(last.tail))
		var hits: Array[SpringBoneCollisionCapsule3D] = []
		for c in capsules:
			var near := INF
			for p in joints:
				near = minf(near, _to_segment(p, _vec(c.head), _vec(c.tail)))
			var r := minf(float(c.radius), near - float(kind.radius) - rest_clearance)
			if r < float(c.radius) * least_slim:
				continue
			var key := "%s@%d" % [c.name, roundi(r * 1000.0)]
			if not made.has(key):
				made[key] = _capsule(c, r)
			if made[key] != null:
				hits.append(made[key])
		simulator.set_enable_all_child_collisions(i, false)
		simulator.set_collision_count(i, hits.size())
		for k in hits.size():
			simulator.set_collision_path(i, k, simulator.get_path_to(hits[k]))
		for bone in chain:
			var b := _skeleton.find_bone(bone)
			if b >= 0:
				recorder.limits[b] = deg_to_rad(float(kind.limit))
				_chain_of[b] = names[i]
	limiter.limits = recorder.limits
	_limiter = limiter


## The widest each chain's links have swung off the clip so far, in degrees
## ({chain: degrees}), and starts counting afresh.
func take_widest() -> Dictionary:
	var out := {}
	for bone in _limiter.widest:
		var chain: String = _chain_of.get(bone, "")
		out[chain] = maxf(out.get(chain, 0.0), rad_to_deg(_limiter.widest[bone]))
	_limiter.widest.clear()
	return out


## How a chain moves (by the start of its name), or the stiffest kind if unknown.
func _kind(chain: String) -> Dictionary:
	for prefix in cloth:
		if chain.begins_with(prefix):
			return cloth[prefix]
	return cloth["mantle"]


## A collider round the body: a capsule from head to tail on its bone, `radius` thick.
func _capsule(c: Dictionary, radius: float) -> SpringBoneCollisionCapsule3D:
	var bone := _skeleton.find_bone(c.bone)
	if bone < 0:
		return null
	var a := _vec(c.head)
	var b := _vec(c.tail)
	var up := (b - a).normalized()
	var side := up.cross(Vector3.FORWARD if absf(up.dot(Vector3.FORWARD)) < 0.9 else Vector3.RIGHT).normalized()
	var at := Transform3D(Basis(side, up, side.cross(up)), (a + b) * 0.5)
	var local := _skeleton.get_bone_global_rest(bone).affine_inverse() * at
	var col := SpringBoneCollisionCapsule3D.new()
	col.name = "Collide_%s_%d" % [c.name, roundi(radius * 1000.0)]
	col.bone_name = c.bone
	col.radius = radius
	col.mid_height = a.distance_to(b)
	col.position_offset = local.origin
	col.rotation_offset = local.basis.get_rotation_quaternion()
	simulator.add_child(col)
	return col


static func _vec(v: Array) -> Vector3:
	return Vector3(float(v[0]), float(v[1]), float(v[2]))


static func _to_segment(p: Vector3, a: Vector3, b: Vector3) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 1e-8), 0.0, 1.0)
	return p.distance_to(a + ab * t)
