class_name AppRoot
extends Node

## Application flow for the slice (vertical_slice_plan.md section 24):
## Mission Select -> Team Preview -> Battle -> Results -> Mission Select.
##
## Owns which screen is showing and the best result this session. It does not keep
## a battle alive between screens: each start instances a fresh battle scene and
## frees it when the results appear.

@export_group("Content")
@export var mission: MissionDefinition
## The roster the team preview reads; the battle scene instances the same file.
@export var unit_profiles: UnitProfiles
## Instanced for each battle.
@export var battle_scene: PackedScene

@export_group("Screens")
@export var mission_select: MissionSelect
@export var team_preview: TeamPreview
@export var results_screen: ResultsScreen

var _battle: BattleRoot
var _best := {} # best star result this session


func _ready() -> void:
	mission_select.mission_chosen.connect(show_team_preview)
	mission_select.quit_requested.connect(get_tree().quit)
	team_preview.back_requested.connect(show_mission_select)
	team_preview.start_requested.connect(start_battle)
	results_screen.retry_requested.connect(start_battle)
	results_screen.return_requested.connect(show_mission_select)
	show_mission_select()


func _show(screen: Control) -> void:
	for s: Control in [mission_select, team_preview, results_screen]:
		s.visible = s == screen


func show_mission_select() -> void:
	mission_select.show_mission(mission, _best)
	_show(mission_select)


func show_team_preview() -> void:
	team_preview.show_squad(unit_profiles.definitions_of(Defs.Faction.PLAYER))
	_show(team_preview)


func start_battle() -> void:
	_show(null)
	_free_battle()
	_battle = battle_scene.instantiate()
	add_child(_battle)
	_battle.battle_finished.connect(_on_battle_finished)
	_battle.start(0, SliceDialogue.PRE_BATTLE)


func _on_battle_finished(result: Dictionary) -> void:
	if result.victory and (_best.is_empty() or Stars.count(result.stars) > Stars.count(_best)):
		_best = result.stars
	_free_battle()
	results_screen.show_result(result)
	_show(results_screen)


func _free_battle() -> void:
	if _battle != null:
		_battle.queue_free()
		_battle = null
