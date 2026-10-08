class_name TeamPreview
extends Control

## The squad about to deploy, one `UnitCard` each. Reports start or back.

signal start_requested
signal back_requested

@export var card_grid: GridContainer
## Instanced once per squad member.
@export var card_scene: PackedScene
@export var back_button: Button
@export var start_button: Button


func _ready() -> void:
	back_button.pressed.connect(back_requested.emit)
	start_button.pressed.connect(start_requested.emit)


func show_squad(defs: Array[Dictionary]) -> void:
	for c in card_grid.get_children():
		c.queue_free()
	for def in defs:
		var card: UnitCard = card_scene.instantiate()
		card_grid.add_child(card)
		card.show_unit(def)
