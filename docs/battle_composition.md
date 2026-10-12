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
│   ├── DisplaySettings
│   ├── PlaytestMetrics
│   └── BattleAudio
│       └── Music
├── World
│   ├── WorldEnvironment   SSAO, SSIL, glow, fog, filmic tone, grade
│   ├── Sun                warm afternoon light with soft shadows
│   ├── UnderDeskGlow
│   ├── Diorama            the room, built from the mission and the Field
│   ├── GroundOverlays     movement area, danger zone, reach rings, cones, areas, Gaze, telegraphs
│   ├── Units              one UnitCard per unit, added at start
│   ├── ThreatArcs
│   ├── Effects
│   └── ArtLights          3D light from the Arts (flashes, beams, bubbles, stage lights)
├── BattleCamera
│   └── Camera3D           depth of field follows the zoom
├── EventPlayer
└── Interface (CanvasLayer)
    ├── UnitPlates         HP bars over units with type icons; predicted HP, matchup arrows, reach reticles
    ├── CoverShields       cover shields round the controlled unit
    ├── BattleHud          (scenes/ui/hud/battle_hud.tscn) objective, turn, Noise, minimap, type triangle, signature letterbox
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
| CONTROL | Steer the unit inside its movement area; arcs, predicted HP, cover shields and gold rings under what it can hit from here follow it. Undo, let go, or open the ring. |
| MENU | The action ring is open. |
| TARGET | Pick a target or aim a cone; the battle preview shows the exchange. Attack also lists enemies the unit could walk up to (fainter rings): the preview, arcs and HP show from the spot it would attack from, and confirming walks there and strikes in one go. Confirm acts and ends the unit's turn. |
| any but BUSY | V / Y toggles every enemy's danger zone. |
| BUSY / DONE | Playback / battle over. |

| Component | Owns |
| --- | --- |
| `Battle` (rules, not a node) | Phases, free movement, actions, Noise, Human Gaze, telegraphs, objectives; emits events |
| `Field`, `ReachField` (rules) | Furniture, slow zones, line of sight, cover; movement areas and paths |
| `Forecast`, `Exchange` (rules) | The threat forecast while moving, every enemy's danger zone; the head-to-head preview |
| `BattleSelection` (view model) | Mode, controlled unit, action, targets, aim, forecast. Written by `BattleRoot` only |
| `Diorama` | The room and furniture, cover damage, tape patches |
| `UnitCard` | One unit's sprite card, shadow, silhouette and faction ring; animations and Gaze form |
| `GroundOverlays` | Every floor marking. Movement areas and the danger zone are drawn by `reach_area.gdshader` from `ReachAreaTexture`'s smooth masks (a lit rim that fades inward, fainter where furniture stops it, growing out from the unit); `area_style` CLASSIC brings back the old flat sheet |
| `UnitPlates`, `CoverShields`, `TypeTriangle` | HP bars with type icons, matchup arrows and reach reticles; XCOM-style cover shields; the Smash > Pierce > Bind reminder |
| `ThreatArcs` | The thin pulsing enemy arcs and push/pull arrows |
| `BattleCamera` | Orbit, tilt, zoom, pan, following the controlled unit, gliding to enemies, push-ins and screen shake |
| `EventPlayer` | Turning battle events into movement, animation, effects, sound and notices; strike close-ups, hit-stop and shake; the signature letterbox |
| `EffectsLayer` | One-shot bursts, projectiles, Stapler's 3D staples, the Toaster's flying toast and fire (Flash Bake's cone, Overheat's swirl and pillars, smoke), floating numbers, the Gaze puff |
| `ArtLights` | 3D light the Arts throw: Flashbulb's pop, Guard Beam's beam and bubble, Spotlight's ring, sky beam and stage light |
| `BattleAudio`, `AudioSettings` | Effect voices, the battle theme; the volume slider's bus and saved setting |
| `DisplaySettings` | Windowed or fullscreen (pause menu, F11), saved between sessions; also on `AppRoot` so the menus start in the saved mode |
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
| `GroundOverlays` | Colours of every floor marking, the movement area's style and grow-in time |
| `Interface/UnitPlates`, `Interface/CoverShields` | Bar sizes and colours, type icon and arrow size; shield height, size and colours |
| `ThreatArcs` | Arc colours by attack type, the crit threshold, line and arrowhead width, arc height |
| `BattleCamera` | Orbit speed, pitch limits, zoom range, follow sharpness, pan speed, depth-of-field offsets |
| `World/Sun`, `World/WorldEnvironment` | Light colour and angle; ambient, SSAO, SSIL, glow, fog, grade |
| `EventPlayer` | Feel: hit-stop length and freeze, shake strength, strike close-ups (on/off, zoom, how far down, the Battle Speed that skips them). Walk and shove speed, attack lunge, pause after strikes; Flashbulb's glow flare, the signature push-in zoom (Spotlight, Staple Storm, Overheat), how long Spotlight's light holds; the Toaster's vent flare, Overheat's white-hot flare, Flash Bake's flame growth |
| `EffectsLayer` | Floating text size, damage number size, crit scale, pop and colours, projectile speed; staple speed, display scale, stick and fade time, miss distance, trail; toast speed, scale, arc and tumble; Flash Bake's fire speed, size and amount |
| `World/ArtLights` | Light colours; flash energy, range and glare size; beam width; bubble size; ring, sky beam and stage light size, energy and motes |
| `BattleAudio`, `AudioSettings` | Effect folder, voices and volume; the battle theme; volume bus and first-run volume |
| `PlaytestMetrics` | Output folder, the Vacuum "path-blocked" threshold |
| `Interface/BattleHud` | Banner, toast and notice timing; letterbox height and slide time |
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
| 3D toys (Lamp, Stapler, Toaster) | `D:/Blender/blender.exe --background --python tools/animate_<name>_3d.py` (Toaster: `python tools/draw_toaster_details.py` first) |
| Effect models (staples, toast) | `D:/Blender/blender.exe --background --python tools/build_staples_3d.py` / `tools/build_toast_3d.py` |
