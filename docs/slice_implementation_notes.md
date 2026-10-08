# Vertical Slice: Implementation Notes

How the "Under the Desk" slice code reads the design docs, and where it had to choose.
Rule constants live in `src/core/models/battle/defs.gd` and `src/core/models/arts/arts.gd`; the map is `data/missions/under_the_desk.tres` and every combatant's stats are on its node in `scenes/units/unit_profiles.tscn`, so they're tuned in the Inspector. The scene trees are described in `battle_composition.md`.

## Running

- Open the project in Godot 4.7 and press Play. The flow is Mission Select, Team Preview, pre-battle talk, battle, results.
- Battle controls: left-click to select, move and target; right-click or Esc to go back; WASD/arrows or middle-drag to pan; mouse wheel to zoom out.
- All tests: `powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1` (structure check, rule tests, full-battle smoke test)
- Screenshots (needs a display): `godot --path . --script res://tools/screenshot.gd -- <out_dir>`

## Scale

- Tiles are 128px (chosen by Apy on 2026-10-08) so each 128x128 character sprite fits its own tile. The 15x11 map is 1920x1408, so the camera scrolls.
- Sprites and map art load from `assets/sprites/...` when present; anything missing draws as a graybox block.

## Choices the docs left open

| Topic | Implementation |
|---|---|
| Enemy stats | Proposed in `under_the_desk.gd` (the docs only give types and traits). |
| Half cover | Impassable. Gives +25 evasion against ranged attacks (distance 2+) when it sits on the side facing the attacker. Large units can't use it. |
| Line of sight | Blocked by full cover between tile centres; grazing a corner doesn't block. |
| Passing units | Units can pass through non-frozen allies but not enemies, neutrals or frozen objects. |
| Gaze centre | The acting unit's tile (its bottom-left tile for Vacuum). |
| Robot Vacuum | Never transforms. While any Gaze is active it moves but can't attack; inside the watched area it also can't be attacked. |
| Pencil Lancer | Charge: +20% damage after moving 3+ tiles. |
| Rubber Band Snarer | Snap pulls the target 1 tile on hit. AI prefers targets next to half cover. |
| Tape Dispenser | Tape Lash on hit makes the target's tile sticky (+2 to enter) and gives -2 Move on its next activation. |
| Bookend Guard | Stays within 2 tiles of its start until 3 enemies are Broken. Forced movement reduced by 1. |
| Paper Cutter | Alternates: acts and marks a 1x5 Cutting Line, then resolves it next Enemy Phase (auto-hit, Might 7, destroys cardboard). Cancelled if the Captain was displaced or is watched. |
| Paper Guard | The plan says the Captain starts near cardboard, but none was listed near (13,10), so a box was added at (12,10). |
| Watchful | Lamp intercepts automatically, once per Enemy Phase, unless the hit could take half of Lamp's HP. |
| Cones | Short cone = one row the user's width in front, then a row one tile wider on each side. |
| Lunge | Dash 1-3 tiles straight, then attack an enemy directly ahead (Might 6). |
| Staple Burst | Two Might 2 attacks; the second retargets if the first target falls. |
| Eject | Push 2 only if the attack hits. |
| Items | Each slice character carries Repair Tape (heal 40% max HP). |
| Defeat | Lamp Broken, or every player unit Broken. |
| Neutral Umbrella | Enemies may attack it (low priority). Recruiting turns it player-controlled on the next Player Phase. |
