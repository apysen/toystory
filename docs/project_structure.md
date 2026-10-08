# Toy Story project structure

This guide defines the layout of the Godot 4.7 project for the household-object
tactics game. It follows the same structure as Sporekeeper
(`D:\GameDev\sporekeeper\docs\project_structure.md`): typed components under
`src/core/`, composition scenes under `scenes/`, authored data under `data/`.
Choose a location by responsibility, data lifetime and dependency direction, not by
the first screen that happens to use a file. Create folders when their first files
are added rather than committing empty directories.

## Intended layout

**This tree is the target, not an inventory.** A folder here is a decision about where
something goes *when it is built*. `tools/check_structure.gd` enforces the direction
that matters: every source folder that exists must be described here.

```text
assets/                         Imported source art and audio; shared presentation
  audio/                        Effects (sfx/) and the room themes (music/)
  portraits/                    Conversation portraits, one per speaker
  sprites/                      Battle sprites, cover, Gaze objects, effects, UI icons
  ui/                           Shared Godot themes and the styles that dress panels
data/                           Authored Resource instances; no state from a battle
  missions/                     One MissionDefinition per map
docs/                           Design documents, structure and composition guides
scenes/                         Godot composition scenes grouped by feature
  app/                          The application root and its screen flow
  battle/                       The battle composition root
  units/                        The mission roster (UnitProfiles)
  ui/
    hud/                        The battle HUD
    dialogue/                   The conversation box
    menus/                      Mission select, team preview, results, their cards
scripts/                        Maintenance and test runners (`run_tests.ps1`)
src/core/
  entities/                     Mutable state; no scene references
    battle/                     `Unit` and `Board`: the live battlefield
  models/                       Immutable authored definitions and shared vocabulary
    arts/                       The Art and item catalogue
    battle/                     `Defs`: enums and prototype tuning constants
    dialogue/                   Authored conversation lines
    missions/                   `MissionDefinition`: map, cover, terrain, wording
  rules/                        Pure, scene-independent game rules
    battle/                     `Battle` (phases, actions, Noise, Gaze), mission setup,
                              and the star objectives
    combat/                     Damage, hit, crit, counters and the movement forecast
    enemies/                    Enemy AI archetypes and the Paper Cutter telegraph
  nodes/                        Scene-bound typed components
    app/                        Application flow between screens
    art/                        Sprite, environment and portrait loaders
    battle/                     Battle root, board drawing, camera, playback,
                              effects, audio and playtest metrics
    ui/                         HUD, dialogue box, menus and their view logic
    units/                      `UnitProfile` and the `UnitProfiles` roster container
  persistence/                  `settings_store.gd` owns `user://settings.cfg`
tests/
  fixtures/                     Shared setup helpers and the playtest bot
  integration/                  Real scenes driven through a whole battle
  unit/                         Pure rules, definitions and state
tools/                          Offline checks, screenshot renders, asset and audio
                              generators; no runtime code
```

## Dependency direction

Authored scenes compose `src/core/nodes/`. Nodes may use `rules`, `entities` and
`models`; models and rules never depend on nodes, scenes, UI or rendering. `data/`
holds instances of model Resources and no mutable battle state.

```text
authored data -> pure rules and battle state -> scene-bound nodes -> UI/VFX
```

The live battle (`Battle`, `Board`, `Unit`) is a plain object graph the rules own.
Presentation reads it and the events it emits; it never mutates it. Player intent
travels inward through `BattleRoot`'s public commands.

## Where new files belong

- A new map: a `MissionDefinition` in `data/missions/` and, if it fields a different
  roster, its own `UnitProfiles` scene under `scenes/units/`.
- A new combatant: a `UnitProfile` child in the roster scene. Its stats are edited in
  the Inspector, not in a script.
- A new rule (an Art, a terrain, an AI behaviour): `src/core/rules/<domain>/`, with its
  vocabulary in `src/core/models/` and a test in `tests/unit/`.
- A new screen or HUD region: a script in `src/core/nodes/ui/` and its own scene in
  `scenes/ui/<area>/`, instanced where it sits. It reports intent with typed signals.
- New art or sound: `assets/`. Presentation code loads it when present and falls back
  to graybox or silence when it is not, so the game always runs.

## Tests

Run every test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -ListOnly
```

The runner imports once, runs `tools/check_structure.gd`, then every script under
`tests/` that `extends SceneTree`. `tests/unit/battle_rules.gd` checks the rules on the
authored mission and roster; `tests/integration/ui_smoke.gd` plays a full battle
through the real battle scene with the playtest bot.

See `docs/battle_composition.md` for the scene trees and the Inspector map.
