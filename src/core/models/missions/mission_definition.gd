class_name MissionDefinition
extends Resource

## One authored tactical map: its size, its furniture and its terrain, plus the
## wording the menus print about it (vertical_slice_plan.md sections 5-13).
##
## Pure data. Who fights on the map is the roster in `UnitProfiles`; how the map
## becomes a live `Board` is `MissionSetup`. Nothing here holds state from a battle.

@export_group("Identity")
@export var mission_id := ""
@export var title := ""
@export_multiline var blurb := ""
@export var objective_text := ""
## Shown under the objective on the mission card and the battle's top bar.
@export var optional_objectives := PackedStringArray()

@export_group("Map")
## Width and height in metres. The layout is authored on a 1 m grid whose
## bottom-left tile is (1, 1).
@export var map_size := Vector2i(15, 11)
## Impassable furniture that blocks sight: tile -> art kind.
@export var full_cover: Dictionary[Vector2i, String] = {}
## Waist-high cover: tile -> art kind. Kinds listed in `cover_durability` can be destroyed.
@export var half_cover: Dictionary[Vector2i, String] = {}
## Hit points of each destructible cover kind. Kinds not listed are durable.
@export var cover_durability: Dictionary[String, int] = {}
## Spilled-drink tiles: entering one costs extra movement.
@export var spill_tiles: Array[Vector2i] = []
## Footprint in metres each furniture kind takes inside its tile. Kinds not listed
## fill the whole tile.
@export var kind_footprints: Dictionary[String, Vector2] = {}
## Kinds whose tiles form one piece of furniture (the cabinet spans four tiles).
@export var merged_kinds := PackedStringArray()
## Where the camera starts, in tiles.
@export var camera_start_tile := Vector2i(4, 3)


func footprint(kind: String) -> Vector2:
	return kind_footprints.get(kind, Vector2.ONE)
