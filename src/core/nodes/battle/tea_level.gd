class_name TeaLevel
extends SkeletonModifier3D
## Runs after Teacup's clips on her "tea" bone:
## - holds the tea down after she's been hit (or has spilt some running): at least
##   `drop` metres under where it was built along the cup's axis, so a clip that
##   lowers it further (spending the tea in an Art) still shows that;
## - tips the surface about in the cup as it sloshes (`tilt`, radians about the cup's
##   X and Z), never further than the room left under the rim allows, after the tilt
##   the clip already gave it and the waves the shader heaves it in (`wave`).
## UnitTea sets `drop`, `tilt` and `wave`. (Godot hands the skin the modified pose but
## restores the animated one afterwards, so scripts reading the bone see the clip's;
## `lowered` and `tipped` say what was last done to it.)

## Metres from the built tea level up to the highest its edge may reach under the
## rim (TEA_DROP - TEA_FREEBOARD in the build), and the tea's radius (TEA_R).
const FREE := 0.009
const RADIUS := 0.126

var drop := 0.0
var tilt := Vector2.ZERO
## Metres the shader's waves lift the edge right now.
var wave := 0.0
## Metres the tea was last lowered below where its clip put it.
var lowered := 0.0
## Radians it was last tipped by on top of its clip.
var tipped := 0.0

var _bone := -1
var _rest := Transform3D.IDENTITY


## Starts holding `bone` on `skeleton` (the modifier must be the skeleton's child).
func setup(skeleton: Skeleton3D, bone: String) -> void:
	_bone = skeleton.find_bone(bone)
	if _bone >= 0:
		_rest = skeleton.get_bone_rest(_bone)


func _process_modification_with_delta(_delta: float) -> void:
	lowered = 0.0
	tipped = 0.0
	var sk := get_skeleton()
	if sk == null or _bone < 0:
		return
	# the tea's offset in the cup's frame, whose Y is the cup's axis
	var pos := sk.get_bone_pose_position(_bone)
	var down := (pos - _rest.origin).y
	if drop > 0.0 and down > -drop:
		lowered = drop + down
		pos.y -= lowered
		sk.set_bone_pose_position(_bone, pos)
	var angle := tilt.length()
	if angle < 1e-4:
		return
	var rot := sk.get_bone_pose_rotation(_bone)
	var has := (_rest.basis.get_rotation_quaternion().inverse() * rot).get_angle()
	var room := FREE + maxf(-(pos - _rest.origin).y, 0.0) - wave
	var most := asin(clampf(room / RADIUS, 0.0, 1.0)) - has
	tipped = clampf(angle, 0.0, maxf(most, 0.0))
	if tipped > 0.0:
		var axis := Vector3(tilt.x, 0.0, tilt.y).normalized()
		sk.set_bone_pose_rotation(_bone, Quaternion(axis, tipped) * rot)
