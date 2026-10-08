# Vertical Slice: Implementation Notes

How the "Under the Desk" slice code reads the design docs, and where it had to choose.
Rule constants live in `src/core/models/battle/defs.gd` and `src/core/models/arts/arts.gd`; the map is `data/missions/under_the_desk.tres` and every combatant's stats are on its node in `scenes/units/unit_profiles.tscn`, so they're tuned in the Inspector. The scene trees are described in `battle_composition.md`.

## Running

- Open the project in Godot 4.7 (Forward+) and press Play. The flow is Mission Select, Team Preview, pre-battle talk, battle, results.
- All tests: `powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1` (structure check, rule tests, pause menu, full-battle smoke test).
- Screenshots (needs a display): `godot --path . --script res://tools/screenshot.gd -- <out_dir>`.
- Balance check with the bot: `godot --headless --path . --script res://tools/autoplay.gd -- [runs]`.

## Controls

| | Keyboard and mouse | Controller |
|---|---|---|
| Take control of a unit | Click it, or Tab | RB / LB |
| Move the controlled unit | WASD / arrows, or click a spot inside its area | Left stick |
| Undo the move | Z | X |
| Let go of the unit | Esc | B |
| Open the action ring | Space / Enter, or click the unit | A |
| Turn the ring / change target / turn a cone | ← → (or A / D), arrow buttons, mouse | D-pad, left stick |
| Confirm / back | Space / Esc | A / B |
| Orbit, tilt, zoom the camera | Q / E, R / F, mouse wheel; right-drag to orbit and tilt | Right stick, triggers |
| Pan the camera (nobody controlled) | WASD, middle-drag, click the minimap | Left stick |
| End turn | T, or the End Turn button | LB-left bumper (button 4) |
| Pause | Esc with nobody controlled | Start |
| Fullscreen | F11, or the pause menu | Pause menu |

## Scale and space

- Play has no grid. The floor is 15 m x 11 m, authored on a 1 m grid: tile (x, y) is the square from (x-1, y-1) to (x, y) metres, and "up the map" is world -z.
- Units are circles (Normal 0.3 m, Large 0.75 m); ranges are edge-to-edge gaps in metres (old range r tiles = r - 0.4 m; 0.6 m is melee).
- Movement areas come from `ReachField`: Dijkstra over 0.25 m samples with diagonal steps, so the area follows furniture; spill and tape cost three times the distance. The area is measured from where the activation began, which is what makes undo and switching units work.
- The room is closed on four sides with tall walls, and the camera is kept inside it (it pulls in rather than pass through a wall), so nothing outside the room is ever in view.
- Hovering an action on the ring draws its reach; Wait, items, Talk and self-only Arts show none.
- Art drawn facing left says so with `"faces": "left"` in its `_meta.json` (Lamp, Teacup, Toaster, Toolbox); cards mirror from that.
- Sprites are drawn at 128 px per metre on cards. Cards lean back toward the camera (`UnitCard.lean`, 0.75) so a steep camera still sees the character; shadow casters stay upright.

## Choices the docs left open

| Topic | Implementation |
|---|---|
| Enemy stats | Proposed on their `UnitProfile` nodes (the docs only give types and traits). |
| Furniture footprints | Per kind in the mission: desk legs 0.7 m, chair column 0.5 m, books 0.85 x 0.7 m, boxes 0.85 m and 0.65 m, cabinet one 2 x 2 m block. |
| Half cover | Blocks movement, not sight. +25 evasion against a ranged attack (gap > 0.6 m) when it stands within 1.2 m of the target, on the line of the shot. Large units can't use it. |
| Line of sight | Blocked when the line between unit centres crosses full cover. |
| Passing units | Units can walk past non-frozen allies but not enemies, neutrals or frozen objects, and can't end overlapping anyone. |
| Gaze | A 1.6 m circle around the acting unit; a unit is watched when its centre is within the radius plus half its body. |
| Cones | Flashbulb, Flash Bake and Blowback reach 1.8 m past the user's edge with a 40° half-angle, aimed in any direction. |
| Lunge | A clear straight dash of up to 3 m that stops in front of the target, then attacks (Might 6). |
| Robot Vacuum | Never transforms. While any Gaze is active it moves but can't attack; inside the watched area it also can't be attacked. |
| Pencil Lancer | Charge: +20% damage after moving 3 m or more. |
| Rubber Band Snarer | Snap pulls the target 1 m on hit. AI prefers targets tucked against half cover. |
| Tape Dispenser | Tape Lash on hit leaves a 0.55 m sticky patch (x3 cost) and -2 m Move on its next activation. |
| Bookend Guard | Stays within 2 m of its start until 3 enemies are Broken. Forced movement reduced by 1 m. |
| Paper Cutter | Alternates: acts and marks a 5 m Cutting Line (0.9 m wide) aimed at the player's units, then resolves it next Enemy Phase (auto-hit, Might 7, cuts through cardboard). Called off at once if a Human Gaze catches the Captain, and cancelled if it was displaced. |
| Paper Guard | The plan says the Captain starts near cardboard, but none was listed near (13,10), so a box was added at (12,10). |
| Watchful | Lamp intercepts automatically, once per Enemy Phase, for an ally within 0.7 m, unless the hit could take half of Lamp's HP. |
| Adjacent | Talk, Watchful, Canopy and Comforting Presence use an edge gap of 0.7 m. |
| Threat arcs | Red normal, yellow crit 15%+, purple type advantage, blue push/pull (with a floor arrow). Brightness follows the hit chance. Telegraphed lanes are painted on the floor instead. |
| Predicted HP | Expected damage from every threat plus any telegraphed lane the unit stands in. A red X shows when the worst case could Break it. |
| Battle preview | Every strike in order, including counters and Staple Burst's second hit; "HP after" assumes every strike lands, and a strike that would Break its target gets a red X. |
| Items | Each slice character carries Repair Tape (heal 40% max HP). |
| Defeat | Lamp Broken, or every player unit Broken. |
| Neutral Umbrella | Enemies may attack it (low priority). Recruiting turns it player-controlled on the next Player Phase. |

## Performance

- The forecast while moving is about 0.2 ms per query: enemy standing spots are cached per selection in `Forecast.ThreatMap` (about 200 ms to build) and only rebuilt after the board changes.
- The battle runs at roughly 240 fps at 1600x900 on the development machine.
