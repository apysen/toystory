# Project Toy Story (working title)

A turn-based tactics game about household objects that become fantasy warriors when humans aren't watching. Built in Godot 4.7, with compact battlefields, free movement, and a lit 3D room presented as a miniature diorama.

Positioning matters: move around furniture, take cover, pick your matchups, and use powerful **Arts** without drawing too much human attention.

## Gameplay

- **Move, then act.** Steer a character freely within its movement area, then choose an attack, Art, or another action. Movement can be undone before committing an action.
- **Player and enemy phases.** Activate your squad in any order, then respond to the enemy's next turn.
- **Noise and Human Gaze.** Arts generate Noise. Too much attracts a human's gaze, temporarily turning exposed fighters back into ordinary objects. Noise-generating Arts are disabled while Gaze is active.
- **Readable tactics.** Movement areas, reach rings, combat forecasts, cover indicators, and danger previews help you judge a position before committing.
- **Distinct characters.** A Lamp Warden, Stapler Rogue, Toaster Pyromancer, Teacup Cleric, and Umbrella Lancer bring household personality to their combat roles.

## Project status

This is an in-development game. Characters are being migrated from pixel-art sprite cards to scripted, rigged 3D models, with theatrical animations and effects timed to their actions. Design documents include plans as well as implemented systems.

## Getting started

### Requirements

- **Godot 4.7.2**, the project's configured development version, using the **Forward Plus** renderer.
- **PowerShell** to use the included test runner.
- For rebuilding character assets: **Blender 5.2**, plus **Python and Pillow** for supporting art tools. These aren't needed to run the game with its existing exported assets.

### Run in the editor

1. Clone this repository.
2. Open Godot's project manager and import `project.godot` from the repository root.
3. Let Godot finish importing the assets.
4. Press **F6** to run the current scene or **F5** to run the game. The main scene is `scenes/app/app.tscn`.

### Run from the command line

From the repository root, with the Godot executable available as `godot` on your PATH:

```powershell
godot --headless --path . --import
godot --path .
```

## Tests

Run the suite without performance probes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -SkipPerformance
```

Run a subset or list the available tests:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Filter "lamp_*"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -ListOnly
```

Omit `-SkipPerformance` to include performance probes. Tests that inspect rendered frames open a game window; other probes run headless.

The runner finds `godot` or `godot4` on PATH, with a fallback to the project's Steam installation. To use a different installation, pass its executable path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -SkipPerformance -GodotExecutable "C:\path\to\godot.exe"
```

## Repository layout

| Path | Purpose |
| --- | --- |
| `assets/` | Models, sprites, shaders, audio, and UI assets |
| `data/` | Authored mission resources |
| `scenes/` | Application, battle, unit, and UI composition scenes |
| `src/core/models/` | Definitions and shared game vocabulary |
| `src/core/entities/` | Mutable battle state |
| `src/core/rules/` | Scene-independent gameplay rules |
| `src/core/nodes/` | Scene components and presentation |
| `src/core/persistence/` | Saved settings |
| `tests/` | Unit tests, integration probes, and fixtures |
| `scripts/` | Test and maintenance runners |
| `tools/` | Asset generators, animation scripts, and project checks |
| `docs/` | Design and development guides |

Data flows from authored definitions through pure rules and battle state to scene components and presentation. Models and rules do not depend on UI or rendering.

## Character assets

Characters are generated from Python scripts rather than edited by hand in Blender. Shared modelling and animation helpers live in `tools/toy3d.py` and `tools/toyanim.py`; individual toys have `build_<name>_3d.py` and `animate_<name>_3d.py` scripts.

Exported models live under `assets/models/`, with animation event JSON files that synchronize gameplay effects with contact, launch, and recovery frames. See [AGENTS.md](AGENTS.md) for the modelling, live Blender workflow, export, and verification conventions.

## Documentation

- [Gameplay design](docs/gameplay_design.md)
- [Characters, Arts, and stats](docs/character_abilities_stats.md)
- [Story bible](docs/story_bible.md)
- [Project structure](docs/project_structure.md)
- [Battle composition and Inspector wiring](docs/battle_composition.md)
- [Vertical slice plan](docs/vertical_slice_plan.md)
- [Working agreements and asset pipeline](AGENTS.md)
