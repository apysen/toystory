class_name UnitCard
extends Control

## One squad member on the team preview: portrait, type, stats and Arts.

@export var portrait: TextureRect
@export var name_label: Label
@export var stats_label: Label
@export var arts_label: Label


## `def` is a `UnitProfile.to_def()` dictionary.
func show_unit(def: Dictionary) -> void:
	portrait.texture = Portraits.get_portrait(def.name)
	portrait.visible = portrait.texture != null
	name_label.text = "%s  (%s%s)" % [def.name, Defs.TYPE_NAMES[def.type], ", Large" if def.size > 1 else ""]
	stats_label.text = "HP %d  Pow %d  Def %d  Move %d" % [def.hp, def.pow, def.def, def.mov]
	var arts: Array[String] = []
	for a in def.arts:
		arts.append(Arts.get_art(a).name)
	arts_label.text = ", ".join(arts)
