class_name Diorama
extends Node3D

## The study floor under the desk, built as a lit 3D diorama from the mission and
## the live Field: floorboards, the skirting and wall, the desk and its legs, the
## office chair, the filing cabinet, book stacks, cardboard boxes, the spilled
## juice and the clutter around the edges. Gameplay furniture is placed exactly on
## the rectangles the rules use, so what blocks a unit is what you see.
##
## Built at runtime from data rather than baked, so a change to the mission moves
## the furniture with it. Destructible cover is rebuilt as it takes damage.

@export_group("Room")
## How far the floor runs past the map on every side, in metres.
@export var floor_margin := 22.0
## Distance from the top edge of the map to the wall.
@export var wall_gap := 2.4
@export var wall_height := 16.0
@export var wall_color := Color("b9c7cf")
@export var rug_color := Color("8e3b36")
@export var rug_rect := Rect2(9.2, -3.5, 13.0, 8.5)
## Painter's tape around the battlefield.
@export var tape_color := Color("4f8fd0")

@export_group("Desk")
@export var desk_height := 6.6
## Desk top extent on the floor, in map metres (it runs off the left of the map).
@export var desk_rect := Rect2(-4.2, 1.6, 10.6, 6.8)
@export var chair_seat_height := 4.4

@export_group("Cover Colours")
@export var book_colors: PackedColorArray = PackedColorArray([
	Color("b8433a"), Color("2f5d8c"), Color("d9a23b"), Color("3f7d4f"), Color("6b4f8f"), Color("e7e0cf"), Color("1f2a3a")])
@export var cabinet_color := Color("8fa391")

var _scenery: Node3D
var _cover: Node3D
var _cover_nodes := {} # object id -> Node3D
var _field: Field
var _rng := RandomNumberGenerator.new()


func setup(field: Field, mission: MissionDefinition) -> void:
	_field = field
	_rng.seed = 7
	for c in get_children():
		c.queue_free()
	_scenery = _node("Scenery", self)
	_cover = _node("Cover", self)
	_build_room(Vector2(mission.map_size))
	_build_desk(field)
	for o in field.objects.values():
		_build_cover(o)
	_build_spill(field)
	_build_clutter(Vector2(mission.map_size))


## Destructible cover took damage: show it dented, or flattened when destroyed.
func update_cover(id: String, destroyed: bool, rect: Rect2, kind: String) -> void:
	if _cover_nodes.has(id):
		_cover_nodes[id].queue_free()
		_cover_nodes.erase(id)
	if destroyed:
		_build_crushed_box(rect, kind)
	elif _field.objects.has(id):
		_build_cover(_field.objects[id])


## Tape Lash left a sticky patch.
func add_tape_patch(center: Vector2, radius: float) -> void:
	var m := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = radius
	cyl.bottom_radius = radius
	cyl.height = 0.01
	cyl.radial_segments = 20
	m.mesh = cyl
	m.material_override = SurfaceLibrary.plain(Color(0.92, 0.84, 0.55, 1.0), 0.25)
	m.position = BattleSpace.to_world(center, 0.012)
	m.rotation.y = _rng.randf() * TAU
	_scenery.add_child(m)


# --- Room ----------------------------------------------------------------------

func _build_room(map: Vector2) -> void:
	var size := map + Vector2.ONE * floor_margin * 2.0
	_box(_scenery, Vector3(size.x, 0.2, size.y), BattleSpace.to_world(map * 0.5, -0.1), SurfaceLibrary.get_material("wood"))
	# The wall beyond the top of the map, with its skirting board and a socket.
	var wall_z := -(map.y + wall_gap)
	_box(_scenery, Vector3(size.x, wall_height, 0.4), Vector3(map.x * 0.5, wall_height * 0.5, wall_z - 0.2),
		SurfaceLibrary.get_material("paint", wall_color))
	_box(_scenery, Vector3(size.x, 1.1, 0.25), Vector3(map.x * 0.5, 0.55, wall_z + 0.12), SurfaceLibrary.get_material("paint"))
	_box(_scenery, Vector3(size.x, 0.12, 0.32), Vector3(map.x * 0.5, 1.1, wall_z + 0.1), SurfaceLibrary.get_material("paint"))
	var socket := _box(_scenery, Vector3(1.1, 1.1, 0.12), Vector3(11.5, 2.4, wall_z + 0.06), SurfaceLibrary.plain(Color("f4f1ea"), 0.35))
	for dx in [-0.22, 0.22]:
		_box(socket, Vector3(0.08, 0.26, 0.04), Vector3(dx, 0.08, 0.07), SurfaceLibrary.plain(Color("2a2a2a"), 0.6))
	# A cable from the socket runs off along the skirting.
	_cylinder(_scenery, 0.07, 9.0, Vector3(16.0, 0.08, wall_z + 0.5), SurfaceLibrary.plain(Color("e9e6df"), 0.5), Vector3(0, 0, PI * 0.5))
	# Rug, with a darker border band.
	var rug_center := Vector3(rug_rect.get_center().x, 0.015, -rug_rect.get_center().y)
	_box(_scenery, Vector3(rug_rect.size.x, 0.03, rug_rect.size.y), rug_center, SurfaceLibrary.get_material("fabric", rug_color))
	_box(_scenery, Vector3(rug_rect.size.x - 0.8, 0.032, rug_rect.size.y - 0.8), rug_center + Vector3(0, 0.002, 0),
		SurfaceLibrary.get_material("fabric", rug_color.lightened(0.18)))
	_box(_scenery, Vector3(rug_rect.size.x - 1.4, 0.034, rug_rect.size.y - 1.4), rug_center + Vector3(0, 0.003, 0),
		SurfaceLibrary.get_material("fabric", rug_color))
	# Painter's tape marks out the battlefield.
	var tape := SurfaceLibrary.plain(tape_color, 0.7)
	var w := 0.14
	_box(_scenery, Vector3(map.x + w * 2, 0.012, w), BattleSpace.to_world(Vector2(map.x * 0.5, -w * 0.5), 0.04), tape)
	_box(_scenery, Vector3(map.x + w * 2, 0.012, w), BattleSpace.to_world(Vector2(map.x * 0.5, map.y + w * 0.5), 0.04), tape)
	_box(_scenery, Vector3(w, 0.012, map.y), BattleSpace.to_world(Vector2(-w * 0.5, map.y * 0.5), 0.04), tape)
	_box(_scenery, Vector3(w, 0.012, map.y), BattleSpace.to_world(Vector2(map.x + w * 0.5, map.y * 0.5), 0.04), tape)


func _build_desk(field: Field) -> void:
	var top_center := BattleSpace.to_world(desk_rect.get_center(), desk_height)
	# The underside faces down only, so a camera above sees straight through it
	# while its shadow still falls across the floor.
	var under := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = desk_rect.size
	plane.flip_faces = true
	under.mesh = plane
	under.material_override = SurfaceLibrary.get_material("timber")
	under.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED
	under.position = top_center
	_scenery.add_child(under)
	# Legs off the left edge of the map (the two on the map are gameplay cover).
	for p in [Vector2(desk_rect.position.x + 0.6, 2.5), Vector2(desk_rect.position.x + 0.6, 7.5)]:
		_desk_leg(p)


func _desk_leg(p: Vector2) -> void:
	var leg := _box(_scenery, Vector3(0.62, desk_height, 0.62), BattleSpace.to_world(p, desk_height * 0.5), SurfaceLibrary.get_material("timber"))
	_box(leg, Vector3(0.72, 0.12, 0.72), Vector3(0, -desk_height * 0.5 + 0.06, 0), SurfaceLibrary.plain(Color("3a2a20"), 0.6))


# --- Cover ---------------------------------------------------------------------

func _build_cover(o: Dictionary) -> void:
	var root := _node(o.id, _cover)
	var r: Rect2 = o.rect
	match o.kind:
		"desk_leg":
			root.position = BattleSpace.rect_center_world(r)
			_box(root, Vector3(r.size.x - 0.08, desk_height, r.size.y - 0.08), Vector3(0, desk_height * 0.5, 0), SurfaceLibrary.get_material("timber"))
			_box(root, Vector3(r.size.x, 0.12, r.size.y), Vector3(0, 0.06, 0), SurfaceLibrary.plain(Color("3a2a20"), 0.6))
		"chair_leg":
			_build_chair(root, r)
		"cabinet":
			_build_cabinet(root, r)
		"books":
			_build_books(root, r)
		"box", "small_box":
			_build_box(root, r, o)
	_cover_nodes[o.id] = root


func _build_chair(root: Node3D, r: Rect2) -> void:
	root.position = BattleSpace.rect_center_world(r)
	var chrome := SurfaceLibrary.get_material("chrome")
	_cylinder(root, 0.2, chair_seat_height - 0.3, Vector3(0, (chair_seat_height - 0.3) * 0.5 + 0.25, 0), chrome)
	_cylinder(root, 0.3, 0.3, Vector3(0, 0.2, 0), SurfaceLibrary.plain(Color("1d1d20"), 0.4))
	# Five-star base, kept low and short so it stays inside the cover footprint's reach.
	for k in 5:
		var a := TAU * k / 5.0 + 0.3
		var arm := _box(root, Vector3(0.95, 0.13, 0.16), Vector3(cos(a) * 0.48, 0.12, sin(a) * 0.48), SurfaceLibrary.plain(Color("1d1d20"), 0.35))
		arm.rotation.y = -a
		var caster := _cylinder(root, 0.11, 0.12, Vector3(cos(a) * 0.92, 0.07, sin(a) * 0.92), SurfaceLibrary.plain(Color("2a2a2e"), 0.5), Vector3(PI * 0.5, 0, 0))
		caster.rotation.y = -a
	var seat := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(3.6, 3.4)
	plane.flip_faces = true
	seat.mesh = plane
	seat.material_override = SurfaceLibrary.get_material("fabric", Color("2c3036"))
	seat.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED
	seat.position = Vector3(0, chair_seat_height, 0)
	root.add_child(seat)


func _build_cabinet(root: Node3D, r: Rect2) -> void:
	var h := 3.8
	root.position = BattleSpace.rect_center_world(r)
	var body := SurfaceLibrary.get_material("metal", cabinet_color)
	_box(root, Vector3(r.size.x, h, r.size.y), Vector3(0, h * 0.5, 0), body)
	# Drawers face the player's side (toward +z in the world).
	var front := r.size.y * 0.5 + 0.02
	var drawer_h := (h - 0.3) / 3.0
	for k in 3:
		var y := 0.2 + drawer_h * (k + 0.5)
		var d := _box(root, Vector3(r.size.x - 0.16, drawer_h - 0.1, 0.05), Vector3(0, y, front), SurfaceLibrary.get_material("metal", cabinet_color.lightened(0.06)))
		_box(d, Vector3(0.6, 0.09, 0.08), Vector3(0, 0.08, 0.05), SurfaceLibrary.get_material("chrome"))
		_box(d, Vector3(0.42, 0.2, 0.02), Vector3(0, drawer_h * 0.22, 0.03), SurfaceLibrary.plain(Color("efe8d6"), 0.8))


func _build_books(root: Node3D, r: Rect2) -> void:
	root.position = BattleSpace.rect_center_world(r)
	var y := 0.0
	var count := 3 + _rng.randi_range(0, 1)
	for k in count:
		var bw := r.size.x * (0.82 + _rng.randf() * 0.18)
		var bd := r.size.y * (0.8 + _rng.randf() * 0.2)
		var bh := 0.1 + _rng.randf() * 0.07
		var book := _node("Book%d" % k, root)
		book.position = Vector3(_rng.randf_range(-0.04, 0.04), y, _rng.randf_range(-0.04, 0.04))
		book.rotation.y = _rng.randf_range(-0.12, 0.12)
		var col: Color = book_colors[_rng.randi() % book_colors.size()]
		# Hard covers top and bottom, with the page block set in on three sides.
		var cloth := SurfaceLibrary.get_material("cloth", col)
		_box(book, Vector3(bw, 0.02, bd), Vector3(0, 0.01, 0), cloth)
		_box(book, Vector3(bw, 0.02, bd), Vector3(0, bh - 0.01, 0), cloth)
		_box(book, Vector3(0.03, bh, bd), Vector3(-bw * 0.5 + 0.015, bh * 0.5, 0), cloth)
		_box(book, Vector3(bw - 0.06, bh - 0.04, bd - 0.05), Vector3(0.0, bh * 0.5, 0), SurfaceLibrary.get_material("pages"))
		y += bh


func _build_box(root: Node3D, r: Rect2, o: Dictionary) -> void:
	root.position = BattleSpace.rect_center_world(r)
	var h := 0.75 if o.kind == "box" else 0.55
	var damaged: bool = o.hp < o.max_hp
	var card := SurfaceLibrary.get_material("card", Color(0.92, 0.88, 0.84) if damaged else Color.WHITE)
	var body := _box(root, Vector3(r.size.x, h, r.size.y), Vector3(0, h * 0.5, 0), card)
	if damaged:
		body.rotation = Vector3(0.06, 0.12, -0.05)
		body.scale = Vector3(1.0, 0.86, 1.0)
		body.position.y = h * 0.43
	# Packing tape across the top and down two sides.
	var tape := SurfaceLibrary.plain(Color(0.86, 0.72, 0.45, 1.0), 0.25)
	_box(body, Vector3(r.size.x + 0.01, 0.012, 0.16), Vector3(0, h * 0.5 + 0.004, 0), tape)
	_box(body, Vector3(0.012, h * 0.5, 0.16), Vector3(r.size.x * 0.5 + 0.004, h * 0.25, 0), tape)
	_box(body, Vector3(0.012, h * 0.5, 0.16), Vector3(-r.size.x * 0.5 - 0.004, h * 0.25, 0), tape)
	# The flap seam.
	_box(body, Vector3(r.size.x * 0.98, 0.006, 0.02), Vector3(0, h * 0.5 + 0.012, 0), SurfaceLibrary.plain(Color("6a4a2a"), 0.9))


func _build_crushed_box(r: Rect2, kind: String) -> void:
	var root := _node("Crushed", _cover)
	root.position = BattleSpace.rect_center_world(r)
	var card := SurfaceLibrary.get_material("card", Color(0.85, 0.8, 0.75))
	var flat := _box(root, Vector3(r.size.x * 1.15, 0.08, r.size.y * 1.05), Vector3(0, 0.04, 0), card)
	flat.rotation.y = 0.3
	for k in 3:
		var bit := _box(root, Vector3(0.25, 0.03, 0.18), Vector3(_rng.randf_range(-0.7, 0.7), 0.02, _rng.randf_range(-0.7, 0.7)), card)
		bit.rotation.y = _rng.randf() * TAU


# --- Spill and clutter -----------------------------------------------------------

## A puddle traced around the spill tiles with a soft, irregular edge.
func _build_spill(field: Field) -> void:
	var rects: Array[Rect2] = []
	for z in field.slow_zones:
		if z.kind == "spill" and z.has("rect"):
			rects.append(z.rect)
	if rects.is_empty():
		return
	var bounds := rects[0]
	for r in rects:
		bounds = bounds.merge(r)
	# Sample a soft distance field and walk its 0.5 contour with marching squares.
	var step := 0.1
	var pad := 0.4
	var origin := bounds.position - Vector2.ONE * pad
	var cols := int(ceil((bounds.size.x + pad * 2) / step)) + 1
	var rows := int(ceil((bounds.size.y + pad * 2) / step)) + 1
	var noise := FastNoiseLite.new()
	noise.seed = 11
	noise.frequency = 1.6
	var value := func(p: Vector2) -> float:
		# Signed distance to the union of the spill tiles (negative inside).
		var d := INF
		for r in rects:
			var q := Vector2(clampf(p.x, r.position.x, r.end.x), clampf(p.y, r.position.y, r.end.y))
			var sd := p.distance_to(q)
			if r.has_point(p):
				sd = -minf(minf(p.x - r.position.x, r.end.x - p.x), minf(p.y - r.position.y, r.end.y - p.y))
			d = minf(d, sd)
		return d + noise.get_noise_2d(p.x * 3.0, p.y * 3.0) * 0.12 - 0.08
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for cy in rows - 1:
		for cx in cols - 1:
			var p := origin + Vector2(cx, cy) * step
			var inside := 0
			var corners := [p, p + Vector2(step, 0), p + Vector2(step, step), p + Vector2(0, step)]
			for c in corners:
				if value.call(c) < 0.0:
					inside += 1
			if inside == 4:
				_quad(st, corners)
			elif inside > 0:
				# Partial cell: keep it when its centre is inside, for a slightly ragged edge.
				if value.call(p + Vector2(step, step) * 0.5) < 0.0:
					_quad(st, corners)
	st.generate_normals()
	var m := MeshInstance3D.new()
	m.mesh = st.commit()
	m.material_override = SurfaceLibrary.get_material("spill")
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_scenery.add_child(m)


func _quad(st: SurfaceTool, c: Array) -> void:
	var y := 0.018
	var w: Array[Vector3] = []
	for p in c:
		w.append(BattleSpace.to_world(p, y))
	st.set_normal(Vector3.UP)
	st.add_vertex(w[0])
	st.add_vertex(w[2])
	st.add_vertex(w[1])
	st.add_vertex(w[0])
	st.add_vertex(w[3])
	st.add_vertex(w[2])


## Things a child leaves on the floor, outside the taped battlefield.
func _build_clutter(map: Vector2) -> void:
	# A pencil lying along the bottom edge.
	var pencil := _node("Pencil", _scenery)
	pencil.position = BattleSpace.to_world(Vector2(4.5, -1.6), 0.14)
	pencil.rotation.y = 0.08
	_cylinder(pencil, 0.14, 4.4, Vector3.ZERO, SurfaceLibrary.plain(Color("e8b53a"), 0.5), Vector3(0, 0, PI * 0.5))
	_cylinder(pencil, 0.145, 0.35, Vector3(2.35, 0, 0), SurfaceLibrary.get_material("chrome"), Vector3(0, 0, PI * 0.5))
	_cylinder(pencil, 0.14, 0.4, Vector3(2.7, 0, 0), SurfaceLibrary.plain(Color("e58a95"), 0.8), Vector3(0, 0, PI * 0.5))
	var tip := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = 0.14
	cone.height = 0.6
	tip.mesh = cone
	tip.material_override = SurfaceLibrary.get_material("timber")
	tip.rotation.z = PI * 0.5
	tip.position = Vector3(-2.5, 0, 0)
	pencil.add_child(tip)
	# A coin, a crumpled paper ball, an eraser and a toy brick.
	_cylinder(_scenery, 0.42, 0.06, BattleSpace.to_world(Vector2(-1.4, 3.2), 0.03), SurfaceLibrary.plain(Color("e0b86a"), 0.45, 0.6))
	var ball := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.55
	sphere.height = 1.0
	sphere.radial_segments = 9
	sphere.rings = 6
	ball.mesh = sphere
	ball.material_override = SurfaceLibrary.get_material("paint")
	ball.position = BattleSpace.to_world(Vector2(map.x + 1.8, 8.6), 0.5)
	ball.rotation = Vector3(0.4, 0.9, 0.2)
	_scenery.add_child(ball)
	var eraser := _box(_scenery, Vector3(0.9, 0.35, 0.5), BattleSpace.to_world(Vector2(map.x + 1.4, 2.0), 0.175), SurfaceLibrary.plain(Color("e9837f"), 0.9))
	eraser.rotation.y = 0.5
	var brick := _box(_scenery, Vector3(1.0, 0.6, 0.5), BattleSpace.to_world(Vector2(-1.6, 9.4), 0.3), SurfaceLibrary.plain(Color("d63c32"), 0.3))
	brick.rotation.y = -0.3
	for k in 4:
		_cylinder(brick, 0.12, 0.14, Vector3(-0.375 + 0.25 * k, 0.37, 0), SurfaceLibrary.plain(Color("d63c32"), 0.3))
	# Dust bunnies along the skirting.
	for k in 5:
		var dust := MeshInstance3D.new()
		var s := SphereMesh.new()
		s.radius = _rng.randf_range(0.12, 0.25)
		s.height = s.radius * 1.4
		dust.mesh = s
		dust.material_override = SurfaceLibrary.get_material("fabric", Color("9c958c"))
		dust.position = BattleSpace.to_world(Vector2(_rng.randf_range(-3.0, map.x + 3.0), map.y + wall_gap - 0.4), 0.1)
		_scenery.add_child(dust)


# --- Helpers ---------------------------------------------------------------------

func _node(n: String, parent: Node) -> Node3D:
	var node := Node3D.new()
	node.name = n
	parent.add_child(node)
	return node


func _box(parent: Node, size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	m.mesh = b
	m.material_override = mat
	m.position = pos
	parent.add_child(m)
	return m


func _cylinder(parent: Node, radius: float, height: float, pos: Vector3, mat: Material, rot := Vector3.ZERO) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = radius
	c.bottom_radius = radius
	c.height = height
	c.radial_segments = 16
	m.mesh = c
	m.material_override = mat
	m.position = pos
	m.rotation = rot
	parent.add_child(m)
	return m
