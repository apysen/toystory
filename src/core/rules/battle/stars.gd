class_name Stars
extends RefCounted

## The three optional objectives as text and as a count. `Battle.stars()` decides
## which were earned; this only counts and prints them.


static func glyph(on: bool) -> String:
	return "★" if on else "☆"


static func count(s: Dictionary) -> int:
	return int(s.recruit) + int(s.turns) + int(s.unbroken)


static func text(s: Dictionary) -> String:
	return "%s%s%s" % [glyph(s.recruit), glyph(s.turns), glyph(s.unbroken)]
