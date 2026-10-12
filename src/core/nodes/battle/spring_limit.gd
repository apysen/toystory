class_name SpringLimit
extends SkeletonModifier3D
## Keeps spring-bone cloth from swinging too far off its clip: one SpringLimit runs
## before the SpringBoneSimulator3D and records each cloth bone's animated rotation,
## a second runs after it and turns any bone that swung further than its limit back
## to the limit (Godot's spring bones have no angle limits of their own). The
## sleeves' drapes, sewn along the forearm, swing about 20 degrees at most.
## UnitSprings makes the pair and fills `limits`.

## Bone index -> the most it may swing off its clip, radians.
var limits: Dictionary = {}
## The recorder this clamp reads (null on the recorder itself).
var recorder: SpringLimit
## The widest each bone has swung off its clip after the limit, radians, by bone
## index (for checks and tuning).
var widest: Dictionary = {}

## Bone index -> its animated rotation this frame (the recorder's).
var _animated: Dictionary = {}


func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	if recorder == null:
		for bone in limits:
			_animated[bone] = sk.get_bone_pose_rotation(bone)
		return
	for bone in limits:
		if not recorder._animated.has(bone):
			continue
		var was: Quaternion = recorder._animated[bone]
		var now := sk.get_bone_pose_rotation(bone)
		var off := was.inverse() * now
		if off.w < 0.0:
			off = -off   # the short way round
		var angle := off.get_angle()
		var most: float = limits[bone]
		if angle > most:
			sk.set_bone_pose_rotation(bone, was.slerp(now, most / angle))
		widest[bone] = maxf(widest.get(bone, 0.0), minf(angle, most))
