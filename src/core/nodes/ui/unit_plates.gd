class_name UnitPlates
extends Control

## Small HP bars floating above every unit, drawn on screen over the diorama. The
## controlled unit's bar shows its predicted HP if it stopped where it is: the HP
## it would lose pulses, and a red ✕ appears when it would be Broken.
##
## Every bar carries its unit's type icon (Smash, Pierce, Bind) on its left. While a
## unit is controlled, each unit it could fight shows the type matchup on the right
## of its bar (Fire Emblem's weapon triangle arrows): a green ▲ when the controlled
## unit is strong against it, a red ▼ when it is strong against the controlled unit,
## nothing when neutral. Units the controlled unit could Basic Attack from where it
## stands get a gold reticle.

## Status -> the letter shown under the bar, in this order.
const STATUS_PIPS := {
	"pinned": "P", "taped": "T", "guard_beam": "G", "spotlight": "L", "canopy": "C", "raincheck": "R", "steady_sip": "S",
	"heated": "H", "dazzled": "D",
}

@export var bar_width := 56.0
@export var bar_height := 7.0
@export var focus_bar_width := 92.0
@export var focus_bar_height := 11.0
@export var player_color := Color("5aa8f0")
@export var enemy_color := Color("ec5a50")
@export var neutral_color := Color("62c86c")
@export var loss_color := Color("ffdf6b")
@export var broken_color := Color("ff3b30")

@export_group("Matchups")
## Size the type icons are drawn at, in screen pixels.
@export var type_icon_size := 18.0
@export var advantage_color := Color("5ee07a")
@export var disadvantage_color := Color("ff5a4a")
@export var arrow_size := 9.0
@export var in_reach_color := Color("ffd25a")

var _cards: Dictionary = {} # unit id -> UnitCard
var _focus: Unit = null
var _predicted := -1
var _risk := ""
## The controlled unit whose type matchups are shown, and the units it can hit from here.
var _matchup: Unit = null
var _in_reach: Array = []
var _type_icons := {}


func setup(cards: Dictionary) -> void:
	_cards = cards
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	for t in [Defs.DmgType.SMASH, Defs.DmgType.PIERCE, Defs.DmgType.BIND]:
		_type_icons[t] = SpriteLib.load_ui("type_" + Defs.TYPE_NAMES[t].to_lower())


## Shows the type matchups against `u` on every other unit's bar; pass null to clear.
func set_matchup(u: Unit) -> void:
	_matchup = u


## Marks the units the controlled unit could Basic Attack from where it stands.
func set_in_reach(units: Array) -> void:
	_in_reach = units


## Shows the predicted HP on `u`'s bar; pass null to clear.
func set_prediction(u: Unit, predicted_hp := -1, risk := "") -> void:
	_focus = u
	_predicted = predicted_hp
	_risk = risk


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var font := get_theme_default_font()
	for id in _cards:
		var card: UnitCard = _cards[id]
		var u := card.unit
		if u.broken or not card.visible:
			continue
		var head := card.global_position + Vector3(0, 1.75 if u.is_large() else 0.95, 0)
		if cam.is_position_behind(head):
			continue
		var sp := cam.unproject_position(head)
		var focused := u == _focus and _predicted >= 0
		var w := focus_bar_width if focused else bar_width
		var h := focus_bar_height if focused else bar_height
		var rect := Rect2(sp - Vector2(w * 0.5, h), Vector2(w, h))
		draw_rect(rect.grow(2), Color(0.06, 0.04, 0.08, 0.85))
		var col := _faction_color(u)
		var frac := float(card.shown_hp) / u.max_hp
		if focused:
			var pfrac := float(_predicted) / u.max_hp
			draw_rect(Rect2(rect.position, Vector2(w * pfrac, h)), col)
			# The part it would lose blinks between warning yellow and the bar colour.
			var pulse := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 140.0)
			var lose := broken_color if _risk == "Broken Risk" else loss_color
			draw_rect(Rect2(rect.position + Vector2(w * pfrac, 0), Vector2(w * (frac - pfrac), h)), col.lerp(lose, pulse))
			var label := "%d" % card.shown_hp if _predicted == card.shown_hp else "%d → %d" % [card.shown_hp, _predicted]
			_text(font, Vector2(rect.position.x, rect.position.y - 5), label, 15, Color.WHITE)
			if _risk == "Broken Risk":
				_cross(rect.end + Vector2(10, -h * 0.5), 7.0)
		else:
			draw_rect(Rect2(rect.position, Vector2(w * frac, h)), col)
		# Type icon on the left of the bar.
		var icon: Texture2D = _type_icons.get(u.dmg_type)
		if icon != null:
			var isz := type_icon_size * (1.2 if focused else 1.0)
			draw_texture_rect(icon, Rect2(Vector2(rect.position.x - isz - 4, rect.get_center().y - isz * 0.5), Vector2(isz, isz)), false)
		var right := rect.end.x + (22.0 if focused and _risk == "Broken Risk" else 6.0)
		if _matchup != null and u != _matchup and _matchup.is_hostile_to(u):
			var rel := Defs.type_relation(_matchup.dmg_type, u.dmg_type)
			if rel != 0:
				_arrow(Vector2(right + arrow_size, rect.get_center().y), rel > 0)
				right += arrow_size * 2 + 4
		if _in_reach.has(u):
			_reticle(Vector2(right + 8, rect.get_center().y), 7.0)
		# Status pips under the bar.
		var x := rect.position.x
		for s in STATUS_PIPS:
			if u.status.has(s):
				_text(font, Vector2(x, rect.end.y + 13), STATUS_PIPS[s], 12, Color("bfe3ff"))
				x += 10
		if u.frozen:
			_text(font, Vector2(rect.position.x, rect.end.y + 13), "watched", 12, Color("d8c8ff"))
		if u.pending_join:
			_text(font, Vector2(rect.position.x, rect.end.y + 13), "joins next phase", 12, Color("b8f0c0"))


func _faction_color(u: Unit) -> Color:
	if u.pending_join or u.faction == Defs.Faction.NEUTRAL:
		return neutral_color
	return player_color if u.faction == Defs.Faction.PLAYER else enemy_color


func _text(font: Font, p: Vector2, s: String, size: int, c: Color) -> void:
	draw_string_outline(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, 4, Color(0.05, 0.03, 0.06))
	draw_string(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, c)


## A matchup arrow centred on `c`: up and green for an advantage, down and red against.
func _arrow(c: Vector2, up: bool) -> void:
	var r := arrow_size
	var pts := PackedVector2Array([c + Vector2(0, -r), c + Vector2(r, r * 0.7), c + Vector2(-r, r * 0.7)]) if up \
		else PackedVector2Array([c + Vector2(0, r), c + Vector2(r, -r * 0.7), c + Vector2(-r, -r * 0.7)])
	var outline := PackedVector2Array(pts)
	outline.append(pts[0])
	draw_polyline(outline, Color(0.06, 0.04, 0.08), 4.0, true)
	draw_colored_polygon(pts, advantage_color if up else disadvantage_color)


## A small gold target reticle: this unit is in reach of a Basic Attack from here.
func _reticle(c: Vector2, r: float) -> void:
	var pulse := 0.75 + 0.25 * sin(Time.get_ticks_msec() / 180.0)
	var col := Color(in_reach_color, pulse)
	var dark := Color(0.06, 0.04, 0.08, 0.9)
	draw_arc(c, r, 0, TAU, 20, dark, 4.0, true)
	draw_arc(c, r, 0, TAU, 20, col, 2.0, true)
	for d in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
		draw_line(c + d * (r - 3), c + d * (r + 4), dark, 4.0)
		draw_line(c + d * (r - 3), c + d * (r + 4), col, 2.0)
	draw_circle(c, 1.6, col)


func _cross(c: Vector2, r: float) -> void:
	draw_line(c + Vector2(-r, -r), c + Vector2(r, r), Color(0.1, 0.0, 0.0), 5.0)
	draw_line(c + Vector2(-r, r), c + Vector2(r, -r), Color(0.1, 0.0, 0.0), 5.0)
	draw_line(c + Vector2(-r, -r), c + Vector2(r, r), broken_color, 3.0)
	draw_line(c + Vector2(-r, r), c + Vector2(r, -r), broken_color, 3.0)
