class_name UnitFire
extends Node3D
## The fire a model keeps burning on its own bones (the Toaster's): a flame in each
## open palm ("flame_R", "flame_L") and, when he runs hot, fire licking out of his
## vents ("vent_R", "vent_L"). UnitModel adds one to a model that has flame bones.
##
## The palm flames burn upright from the palms. In the travel clip ("move") his
## arms are swept back and the flames turn into rocket jets: long, fast fire shot
## straight back along his hands. Arts raise `heat` (bigger, wilder flames: Flash
## Bake's charge) and `vents` (Overheat's build-up; Hot Coils' Heated), and a
## Broken toaster goes cold (`go_out`). Presentation only.

const FLAME_BONES: Array[String] = ["flame_R", "flame_L"]
const HAND_BONES: Array[String] = ["hand_R", "hand_L"]
const VENT_BONES: Array[String] = ["vent_R", "vent_L"]

## Size of a palm flame's blobs and how many burn at once (at heat 1).
@export var palm_size := 0.075
@export var palm_amount := 10
## Rocket jets: blob size, how fast the fire shoots back (m/s) and how long it lives.
@export var jet_size := 0.08
@export var jet_speed := 3.2
@export var jet_lifetime := 0.22
## Vent fire at full `vents`.
@export var vent_size := 0.07
@export var vent_amount := 10

## Flame size and fury (1 = his idle flames).
var heat := 1.0
## Fire out of the vents an Art stokes: 0 none, 1 burning, 2 white-hot.
var vents := 0.0
## Hot Coils' Heated: the vents smoulder (at least half `vents`) until it is used.
var hot := false

var _model: UnitModel
var _palms: Array[CPUParticles3D] = []
var _vents: Array[CPUParticles3D] = []
var _out := false


func _init(model: UnitModel) -> void:
	_model = model
	name = "Fire"


func _ready() -> void:
	for b in FLAME_BONES:
		var p := FireFX.flame(palm_amount, palm_size)
		add_child(p)
		_palms.append(p)
	for b in VENT_BONES:
		var v := FireFX.flame(vent_amount, vent_size, 0.35)
		v.emitting = false
		add_child(v)
		_vents.append(v)


## Puts the fire out (Broken): the flames die and stay out.
func go_out() -> void:
	_out = true
	for p in _palms + _vents:
		p.emitting = false


func _process(_delta: float) -> void:
	if _out or not _model.is_visible_in_tree():
		for p in _palms + _vents:
			p.emitting = false
		return
	var jets := _model.current() == "move"
	for i in _palms.size():
		var p := _palms[i]
		var at := _model.bone_position(FLAME_BONES[i])
		if at == Vector3.INF:
			p.emitting = false
			continue
		p.emitting = true
		if jets:
			# the fire shoots out behind him along the hand (its bone runs wrist to fingers)
			var hand := _model.bone_position(HAND_BONES[i])
			var along := (_model.bone_position(HAND_BONES[i], Vector3(0, 1, 0)) - hand).normalized()
			p.global_position = hand + along * 0.05
			p.direction = along
			p.spread = 7.0
			p.gravity = Vector3.ZERO
			p.initial_velocity_min = jet_speed * 0.8
			p.initial_velocity_max = jet_speed
			_set_lifetime(p, jet_lifetime)
			(p.mesh as QuadMesh).size = Vector2.ONE * jet_size
		else:
			p.global_position = at
			p.direction = Vector3.UP
			p.spread = 12.0 + 10.0 * (heat - 1.0)
			p.gravity = Vector3(0, 1.4 * heat, 0)
			p.initial_velocity_min = 0.15 * heat
			p.initial_velocity_max = 0.35 * heat
			_set_lifetime(p, 0.45)
			(p.mesh as QuadMesh).size = Vector2.ONE * palm_size * heat
	var burn := maxf(vents, 0.5 if hot else 0.0)
	for i in _vents.size():
		var v := _vents[i]
		var at := _model.bone_position(VENT_BONES[i])
		v.emitting = burn > 0.05 and at != Vector3.INF
		if v.emitting:
			v.global_position = at
			(v.mesh as QuadMesh).size = Vector2.ONE * vent_size * clampf(burn, 0.4, 2.0)
			v.initial_velocity_max = 0.3 + 0.3 * burn


## Lifetime only when it changes: setting it restarts the emitter's cycle.
func _set_lifetime(p: CPUParticles3D, seconds: float) -> void:
	if not is_equal_approx(p.lifetime, seconds):
		p.lifetime = seconds
