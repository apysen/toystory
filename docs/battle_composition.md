# The battle scene and the app flow

Launching the project opens `scenes/app/app.tscn`: Mission Select, Team Preview, the
battle, Results, and back to Mission Select. The composition rules are Sporekeeper's
(`D:\GameDev\sporekeeper\docs\sporekeeper_composition_conventions.md`):

- Reusable behaviour has a `class_name`, so it is a real Godot type.
- Scenes are composition roots. Components are authored children, wired with typed
  `@export` references. Gameplay code does not use `$`, `get_node()` or groups.
- A region with rules of its own is its own scene, instanced where it sits. It reports
  intent upward with typed signals and takes narrow commands (or one `setup()` call)
  downward. A parent does not reach into a sub-scene's children.
- Authored definitions, mutable battle state, pure rules and presentation stay apart.
- Designer-facing tuning lives on the component or definition that consumes it.

## App scene

```text
AppRoot                    (src/core/nodes/app/app_root.gd)
├── UnitProfiles           (scenes/units/unit_profiles.tscn) - read by the team preview
└── Menus (CanvasLayer)
    ├── MissionSelect      (scenes/ui/menus/mission_select.tscn)
    ├── TeamPreview        (scenes/ui/menus/team_preview.tscn, one SquadCard per unit)
    └── ResultsScreen      (scenes/ui/menus/results_screen.tscn)
```

`AppRoot` instances `scenes/battle/battle.tscn` for each battle and frees it when the
results appear, so no battle state survives between screens.

| Sub-scene | Reports |
| --- | --- |
| `MissionSelect` | `mission_chosen`, `quit_requested` |
| `TeamPreview` | `start_requested`, `back_requested` |
| `ResultsScreen` | `retry_requested`, `return_requested` |

## Battle scene

The battle is an HD-2D diorama: a modelled, lit 3D room with the pixel-art units on
camera-facing cards, a free orbit camera, and a small interface on top.

```text
BattleRoot (Node3D)        (src/core/nodes/battle/battle_root.gd)
├── GameplayComponents
│   ├── UnitProfiles       (scenes/units/unit_profiles.tscn)
│   ├── AudioSettings
│   ├── PlaytestMetrics
│   └── BattleAudio
│       └── Music
├── World
│   ├── WorldEnvironment   SSAO, SSIL, glow, fog, filmic tone, grade
│   ├── Sun                warm afternoon light with soft shadows
│   ├── UnderDeskGlow
│   ├── Diorama            the room, built from the mission and the Field
│   ├── GroundOverlays     movement area, reach rings, cones, Gaze, telegraphs
│   ├── Units              one UnitCard per unit, added at start
│   ├── ThreatArcs
│   └── Effects
├── BattleCamera
│   └── Camera3D           depth of field follows the zoom
├── EventPlayer
└── Interface (CanvasLayer)
    ├── UnitPlates         HP bars over units; predicted HP on the controlled one
    ├── BattleHud          (scenes/ui/hud/battle_hud.tscn) objective, turn, Noise, minimap
    ├── ActionRing         (scenes/ui/hud/action_ring.tscn)
    ├── BattlePreview      (scenes/ui/hud/battle_preview.tscn)
    ├── DialogueBox        (scenes/ui/dialogue/dialogue_box.tscn)
    └── PauseMenu          (scenes/ui/menus/pause_menu.tscn)
```

`BattleRoot` owns the player's turn flow and coordinates its peers. It implements none
of their rules:

| Mode | What the player does |
| --- | --- |
| IDLE | Free camera. Click a unit or Tab / RB to take control. |
| CONTROL | Steer the unit inside its movement area; arcs and predicted HP follow it. Undo, let go, or open the ring. |
| MENU | The action ring is open. |
| TARGET | Pick a target or aim a cone; the battle preview shows the exchange. Confirm acts and ends the unit's turn. |
| BUSY / DONE | Playback / battle over. |

| Component | Owns |
| --- | --- |
| `Battle` (rules, not a node) | Phases, free movement, actions, Noise, Human Gaze, telegraphs, objectives; emits events |
| `Field`, `ReachField` (rules) | Furniture, slow zones, line of sight, cover; movement areas and paths |
| `Forecast`, `Exchange` (rules) | The threat forecast while moving; the head-to-head preview |
| `BattleSelection` (view model) | Mode, controlled unit, action, targets, aim, forecast. Written by `BattleRoot` only |
| `Diorama` | The room and furniture, cover damage, tape patches |
| `UnitCard` | One unit's sprite card, shadow, silhouette and faction ring; animations and Gaze form |
| `GroundOverlays` | Every floor marking |
| `ThreatArcs` | The thin pulsing enemy arcs and push/pull arrows |
| `BattleCamera` | Orbit, tilt, zoom, pan, following the controlled unit, gliding to enemies |
| `EventPlayer` | Turning battle events into movement, animation, effects, sound and notices |
| `EffectsLayer` | One-shot bursts, projectiles, floating numbers, the Gaze puff |
| `BattleAudio`, `AudioSettings` | Effect voices, the battle theme; the volume slider's bus and saved setting |
| `PlaytestMetrics` | The section 26 playtest numbers and the per-battle JSON file |

| Sub-scene | Reports |
| --- | --- |
| `BattleHud` | `end_turn_requested`; its `Minimap` reports `focus_requested(point)` |
| `ActionRing` | `chosen(action_id)`, `cancelled`, `hovered(action_id)` |
| `BattlePreview` | nothing; it shows an `Exchange.preview` |
| `DialogueBox` | `finished` |
| `PauseMenu` | `opened`, `closed`, `main_menu_requested`. `BattleRoot` decides what pausing stops (everything but the menu and the music) |
| `UnitProfiles` | nothing; `BattleRoot` reads the definitions when a battle starts |

The battle reports upward: `battle_finished(result)` after the closing conversation
has played, or `battle_abandoned` when the player leaves from the pause menu.

## Editing in the Inspector

| Select this node | Adjust |
| --- | --- |
| Any child of `UnitProfiles` | Identity, faction, type, footprint, start tile, stats (Move and reach in metres), Arts, item, AI archetype, Heavy Frame, Expected Behavior, recruiter |
| `BattleRoot` → `Mission` | Open `data/missions/under_the_desk.tres`: map size, full and half cover, footprints per kind, cover durability, spill tiles, camera start, mission wording |
| `BattleRoot` → Control | Unit move speed, cone aim step, click slack |
| `Diorama` | Room size, wall and rug colours, painter's tape, desk height and extent, chair seat height, book and cabinet colours |
| `GroundOverlays` | Colours of every floor marking |
| `ThreatArcs` | Arc colours by attack type, the crit threshold, line and arrowhead width, arc height |
| `BattleCamera` | Orbit speed, pitch limits, zoom range, follow sharpness, pan speed, depth-of-field offsets |
| `World/Sun`, `World/WorldEnvironment` | Light colour and angle; ambient, SSAO, SSIL, glow, fog, grade |
| `EventPlayer` | Walk and shove speed, attack lunge, pause after strikes |
| `EffectsLayer` | Floating text size, projectile speed |
| `BattleAudio`, `AudioSettings` | Effect folder, voices and volume; the battle theme; volume bus and first-run volume |
| `PlaytestMetrics` | Output folder, the Vacuum "path-blocked" threshold |
| `Interface/BattleHud` | Banner, toast and notice timing |
| `Interface/ActionRing` | Ring size, icon size, back-of-ring scale, turn time |

A profile is copied into a `Unit` when a battle starts, so editing one changes the
next battle and never a battle already running. Rule constants shared by every unit
(Noise threshold, Gaze radius, type bonuses, melee reach) are in
`src/core/models/battle/defs.gd`; Arts are in `src/core/models/arts/arts.gd`.

## Generated assets

| What | Command |
| --- | --- |
| Floor, timber, paint, fabric, metal, chrome, cardboard, cloth, pages, spill textures | `python tools/gen_textures.py` |
| Action ring icons | `python tools/bake_action_icons.py` |
| Enemy and transition animation drafts | `python tools/bake_unit_anims.py` |
| Enemy portraits | `python tools/bake_portraits.py` |
| UI skin | `python tools/bake_ui_skin.py` |
| Battle theme | `python tools/gen_music.py` |
| Sound effects | `python tools/gen_sfx.py` |
