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
    ├── TeamPreview        (scenes/ui/menus/team_preview.tscn, one UnitCard per unit)
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

```text
BattleRoot                 (src/core/nodes/battle/battle_root.gd)
├── GameplayComponents
│   ├── UnitProfiles       (scenes/units/unit_profiles.tscn)
│   │   ├── Lamp, Stapler, Toaster, Teacup, Vacuum
│   │   ├── Umbrella       (neutral recruit)
│   │   └── PencilLancerA, RubberBandSnarer, BookendGuard, PencilLancerB,
│   │       TapeDispenser, RobotVacuum, PaperCutterCaptain
│   ├── AudioSettings
│   ├── PlaytestMetrics
│   └── BattleAudio
│       └── Music
├── BattleCamera
├── BoardView
│   ├── Floor              floor art, spill, tape, rubble, grid
│   ├── Overlay            Gaze area, telegraphs, movement and target highlights
│   ├── Units              y-sorted units and cover
│   └── Top                path, threat lines, displacement arrows, cursor
├── Effects
├── EventPlayer
└── Interface (CanvasLayer)
    ├── BattleHud          (scenes/ui/hud/battle_hud.tscn)
    ├── DialogueBox        (scenes/ui/dialogue/dialogue_box.tscn)
    └── PauseMenu          (scenes/ui/menus/pause_menu.tscn)
```

`BattleRoot` owns the player's turn flow (select, move, act, target, end the phase)
and coordinates its peers. It implements none of their rules:

| Component | Owns |
| --- | --- |
| `Battle` (rules, not a node) | Phases, actions, Noise, Human Gaze, telegraphs, objectives; emits events |
| `BattleSelection` (view model) | What is selected, hovered and targeted. Written by `BattleRoot`, read by `BoardView` and `BattleHud` |
| `BoardView` | The tile/pixel mapping and all board drawing; unit and cover views |
| `EventPlayer` | Turning battle events into movement, animation, effects, sound and log lines |
| `EffectsLayer` | One-shot bursts, projectiles, floating numbers, the Gaze puff |
| `BattleCamera` | Pan, zoom, limits and following units during the Enemy Phase |
| `BattleAudio` | Effect voices and the looping battle theme |
| `AudioSettings` | The bus the volume slider drives, how loud 100% is, and the saved volume |
| `PlaytestMetrics` | The section 26 playtest numbers and the per-battle JSON file |

| Sub-scene | Reports |
| --- | --- |
| `BattleHud` | `end_turn_requested`, `action_chosen(action_id)`, `back_requested`, `pause_requested` |
| `PauseMenu` | `opened`, `closed`, `main_menu_requested`. `BattleRoot` decides what pausing stops (everything but the menu and the music) |
| `DialogueBox` | `finished` |
| `UnitProfiles` | nothing; `BattleRoot` reads the definitions when a battle starts |

The battle reports upward: `battle_finished(result)` after the closing conversation
has played, or `battle_abandoned` when the player leaves from the pause menu.
Esc (with nothing selected) or the top bar's Menu button opens the pause menu.

## Editing in the Inspector

| Select this node | Adjust |
| --- | --- |
| Any child of `UnitProfiles` | Identity, faction, type, footprint, start tile, stats, Arts, item, AI archetype, Heavy Frame, Expected Behavior, recruiter |
| `BattleRoot` → `Mission` | Open `data/missions/under_the_desk.tres`: map size, full and half cover, cover durability, spill tiles, camera start, mission wording |
| `BattleAudio` | Effect folder, voices and volume; the battle theme and its volume |
| `BattleCamera` | Pan speed, zoom range and step, follow time, map margins |
| `BoardView` | Map origin, grid colour |
| `EventPlayer` | Walk and shove speed, attack lunge, pauses after strikes and area flashes |
| `EffectsLayer` | Projectile speed, floating text size, draw order |
| `AudioSettings` | Volume bus, 100% output, first-run volume |
| `PlaytestMetrics` | Output folder, the Vacuum "path-blocked" threshold |
| `Interface/BattleHud` | Banner and toast timing, the idle hint, log length |

A profile is copied into a `Unit` when a battle starts, so editing one changes the
next battle and never a battle already running. Rule constants shared by every unit
(Noise threshold, Gaze size, type bonuses) are in `src/core/models/battle/defs.gd`;
Arts are in `src/core/models/arts/arts.gd`.
