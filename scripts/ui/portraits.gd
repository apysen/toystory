class_name Portraits
extends RefCounted
## Conversation portraits: assets/portraits/<id>.png, falling back to the
## character's battle sprite (first idle frame), then to a flat colour.

const IDS := {
	"Lamp": "lamp", "Stapler": "stapler", "Toaster": "toaster", "Teacup": "teacup",
	"Vacuum": "vacuum_256", "Umbrella": "umbrella", "Paper Cutter Captain": "cutter",
}


static func get_portrait(speaker: String) -> Texture2D:
	var id: String = IDS.get(speaker, speaker.to_lower())
	var path := "res://assets/portraits/%s.png" % id
	if ResourceLoader.exists(path) or FileAccess.file_exists(ProjectSettings.globalize_path(path)):
		return SpriteLib._texture(path)
	var art: Variant = SpriteLib.load_unit(id)
	if art != null:
		var sf: SpriteFrames = art.frames
		if sf.has_animation("idle"):
			return sf.get_frame_texture("idle", 0)
	return null


static func fallback_color(speaker: String) -> Color:
	return Color.from_hsv(float(hash(speaker) % 360) / 360.0, 0.35, 0.45)
