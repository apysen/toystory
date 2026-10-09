# AGENTS.md

Working agreements for agents (and people) on **Toy Story**, the Godot 4.7
household-object tactics game. It collects the conventions agreed while building
the game and its 3D characters: where code and scenes go, how the 3D toys are
modelled, rigged, animated, built and wired into Godot, and how to work with the
project owner. The longer guides it points to stay the source of truth for their
topics.

| Topic | Read |
| --- | --- |
| Folder layout and dependency direction | `docs/project_structure.md` |
| Battle and app scene trees, Inspector map, generated assets | `docs/battle_composition.md` |
| Characters, Arts, stats, ability names | `docs/character_abilities_stats.md` |
| Rules and game design | `docs/gameplay_design.md` |
| Character concept sheets (motion and look reference) | `assets/concept/animations/<name>.png` |

---

## 1. Environment and tools

| Tool | Where / how |
| --- | --- |
| Godot 4.7.2 | `E:/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe` |
| Tests | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -SkipPerformance` (add `-Filter "lamp_*"` for one) |
| Import after new assets | `godot --headless --path . --import` |
| Blender 5.2 | `D:/Blender/blender.exe` |
| Blender, live | The **Blender MCP** server (`execute_blender_code`, window screenshots) drives the open Blender session |
| Blender, headless | `D:/Blender/blender.exe --background --python tools/animate_<name>_3d.py` builds, animates, checks and exports in a clean session |
| Python helpers | Plain `python` (Pillow) for contact sheets, GLB inspection and file edits |

### Skills used for the 3D work

Both are user-level Claude skills installed in `~/.claude/skills/` (not in the
repo). Load them when modelling or scripting Blender:

| Skill | Source | Used for |
| --- | --- | --- |
| `3d-modeling` | omer-metin | Production modelling judgement: closed manifold parts, consistent normals, apply transforms before export, game-ready triangle budgets, LOD/texel thinking, glTF export checks, topology that deforms. |
| `blender-3d-modeling` | Andrew1326 | Procedural Blender Python: building meshes from code with `bmesh`, modifiers (the preview outline is a Solidify inverted hull), curves, parametric shapes, running scripts headless. |

Both are guidance only. The project's own rules below win where they differ (e.g.
the toys use one palette-textured material and flat low-poly parts, not unwrapped
UVs or subdivision).

---

## 2. Godot structure and composition

Toy Story mirrors **Sporekeeper**'s structure
(`D:\GameDev\sporekeeper\docs\sporekeeper_composition_conventions.md`).

- Code lives in `src/core/{models,entities,rules,nodes,persistence}`. Models and rules never
  depend on nodes, scenes, UI or rendering. Data flows: authored data → pure rules and
  battle state → scene-bound nodes → UI/VFX.
- Scenes under `scenes/` are composition roots. Reusable behaviour has a `class_name`.
  Components are authored children wired with typed `@export` references. Gameplay code does
  not use `$`, `get_node()` or groups.
- A region with its own rules is its own scene. It reports intent upward with typed signals
  and takes narrow commands or one `setup()` call downward. A parent never reaches
  into a sub-scene's children.
- Run-level helpers sit under a `GameplayComponents` parent on the root (e.g. `BattleRoot`
  → `GameplayComponents/{UnitProfiles, AudioSettings, DisplaySettings, BattleSpeedSettings, ...}`).
- Designer tuning lives as `@export` on the component or definition that consumes it.
  Unit stats are edited on `UnitProfile` nodes in the Inspector, not in scripts.
- Settings are saved only through `src/core/persistence/settings_store.gd`. It owns
  `user://settings.cfg`, with sections audio, display and gameplay. Example: Battle Speed is
  `BattleSpeedSettings` (steps 1/1.5/2/3×). The pause menu's button steps it; `EventPlayer`
  applies it as `Engine.time_scale` only while events play back, so steering stays real time.
- Every folder that exists must be described in `docs/project_structure.md`
  (`tools/check_structure.gd` fails the test run otherwise). Never leave
  `tools/__pycache__` behind: Python tool scripts set `sys.dont_write_bytecode = True`
  before importing shared modules.
- GDScript: tabs, static types, `##` doc comments that say what a thing is for. Match the
  comment density and naming of the surrounding code.

### Look and facing

- HD-2D diorama: a modelled, lit 3D room, a free orbit camera and a minimal HUD.
  Units used to be pixel-art sprite cards; they are being replaced by 3D models one
  character at a time (Lamp Warden and Stapler Rogue so far).
- Every character faces its last horizontal move. Sprite art is drawn once at a base
  facing and mirrored. 3D models turn to their heading, and in standing clips (idle, hurt,
  broken) they turn three-quarters toward the camera.

---

## 3. 3D character pipeline

Each toy is generated entirely by scripts. **Never hand-edit a `.blend`**: change the
script and rebuild.

| File | Role |
| --- | --- |
| `tools/toy3d.py` | Shared modelling: `Character` config, sprite space (`P`, `H`), `Builder` with primitives (lathe, tube, strap, box, sphere, ring, slab), `cloth` panels with tears and ragged holes, `bandage`, `chain_weights`, `follow_limbs`, hands, palette material, rig with IK and knee poles, `clip_report`, export, preview camera |
| `tools/toyanim.py` | Shared animation: curves (`wave`, `smooth`, `keyed`), pose maths (`mix`, `add`), feet (`step`, `plant_path`, `knee_ahead`, `feet_in`), `lowered`, keying, per-frame `clip_check`, contact-sheet renders, events JSON, the Blender clip-player tab |
| `tools/build_<name>_3d.py` | One character's palette, parts, joints, clip-check pairs and checks |
| `tools/animate_<name>_3d.py` | One character's poses, clips, `settle` fix-ups and events |

Current characters: `lamp_warden` (Lamp) and `stapler_rogue` (Stapler).

### Outputs

```text
assets/models/<folder>/<name>.glb                     skinned mesh + deform skeleton + clips
assets/models/<folder>/<name>_events.json             clip timings the game reads
assets/models/<folder>/<name>_<name>_palette.png      extracted by Godot's importer
assets/models/<folder>/source/  (.gdignore)           .blend copy, previews, contact sheets
```

After a first import, set both extracted palette PNGs' `.import` to lossless with no
mipmaps (`compress/mode=0`, `mipmaps/generate=false`, `detect_3d/compress_to=0`) and
reimport, so the colours stay exact.

### Running

```python
# live, through the Blender MCP
exec(open("tools/animate_stapler_rogue_3d.py").read())   # also execs the build script
obj, tris, rest = BUILD["build_stapler"]()                # Lamp: BUILD["build"]()
animate_stapler(obj)                                      # Lamp: animate_all(obj)
clip_check(obj, every=1)                                  # {clip: {pair: (tris, frame)}}
toy3d.export_glb(obj)
```

Headless: `D:/Blender/blender.exe --background --python tools/animate_<name>_3d.py`.
Prefer headless for a final export when other toys are loaded in the live session.

In a live session, animating a toy adds a sidebar tab (3D view, **N**) named after it,
with a button per clip that shows and plays it (and hides the other toys, which all stand
on the origin) plus **Stop**.

### Action naming and export

- Actions are named `<Toy>|<clip>` (e.g. `StaplerRogue|idle`). Toys share clip names, and
  unprefixed actions overwrite each other inside one Blender session.
- `toy3d.export_glb` exports only the rig's own actions (by action slot). It writes each
  as an NLA track named by the bare clip, with the IK baked by per-frame sampling and
  deform bones only.
- Verify an export by reading the GLB's animation list (no foreign clips such as another
  toy's `intercept_run`). When refactoring, diff the new GLB against the old one: mesh
  attributes, joints, inverse binds and every channel.

### Godot integration

- `src/core/nodes/battle/unit_model.gd` (`UnitModel`): `MODELS` maps a unit id or sprite
  to its GLB. It swaps in `assets/shaders/unit_model.gdshader`, which matches the card
  lighting and fades by an instance uniform. It reads `<glb>_events.json`. It loops
  `LOOPS` and turns `STANDING` clips toward the camera. It strips root motion from the
  skeleton's root bone and scales the travel loop to the unit's real speed.
- `UnitCard` hosts the model and hides its sprite card. The Gaze object form stays a
  sprite card. `play_art(id)` plays a clip named after the Art when one exists.
- `EventPlayer`: a model's strike waits `contact_time("attack")` (the `hit` event) and
  then the projectile flies. Sprite units keep the old lunge timing.
- Events JSON keys: `attack.hit` (contact or shot frame, seconds), `pin.hit`,
  `intercept_guard.brace` / `.impact`, `move.speed` (m/s the run was authored for, 1.8).
- Every character gets an integration test like `tests/integration/lamp_model.gd` and
  `stapler_model.gd`: the model shows, the expected clips exist (and removed ones do not),
  timings match, Arts play their own clips, a strike plays through.

---

## 4. Modelling conventions

- **Reference:** the pixel sprite (128 px idle frame) sets size and stance. The concept sheet
  sets the look, and the model should match it as closely as possible. The design doc's
  names win over concept-sheet names.
- **Scale and orientation:** 128 px = 1 m (`BattleSpace.PIXELS_PER_METRE`), with the sprite's foot
  pivot at the origin so the model stands at the card's size. The model faces **-Y** in
  Blender (+Z in Godot); the character's right is -X.
- **Built pose:** model in a neutral, rig-friendly pose. Expressive stances belong
  in the idle clip.
- **One mesh, one material:** every face samples a swatch of a 16×16 palette texture
  (4×4 swatches) of the sprite's exact colours, plus a matching emission texture for glows
  (lamp light, Stapler's eyes), sampled nearest. One draw call.
- **Budget:** about 8k triangles was the first target. Raise it when the look needs it: Stapler
  is about 13k. Low segment counts sized to what reads at battle scale; flat shading for
  faceted cloth.
- **Parts:** every part is a closed solid tagged with its part name and skinned to one
  bone (`Builder.finish`). Body parts blend hips → spine → chest. Every vertex group must
  have a bone (`toy3d.build` asserts this).
- **No clipping:**
  - Every pair of parts that must not touch is listed in `CLIP_CHECKS`. Check it at rest, in
    arm and leg stress poses (`pose_test`, thigh kicks, head turns and nods), and on every
    frame of every clip.
  - Overlapping surfaces at the same radius flicker, so keep layers apart.
  - Parts may be tucked inside something that hides them (a hood hem inside the scarf
    wrap); leave those pairs out of the checks deliberately.
- **Anatomy:** human-shaped hands closed on their grip with the correct left/right
  chirality, natural elbows (behind the hand, about 140-160°), legs connected to feet, and
  proportions from the sprite.
- **Cloth (cloaks, capes, scarves, skirts, tabards):**
  - Build as `toy3d.cloth` panels: a grid with even rows down its length, closed with walls
    so it stays a solid.
  - Add a sway weight in UV2.x (0 pinned → 1 at the hem) and a bone chain (`cloak_1..3`,
    `scarf_1..2`).
  - Tears are dropped cells. Holes are ragged outlines punched through one or more cells,
    never square. The cloth round a hole takes the colour of the cell it replaces, so
    painted streaks run straight through and don't outline it.
  - Torn hems have long, irregular points.
- **Cloth over limbs:** `follow_limbs` weights cloth near a limb to follow it:
  - a mantle or shirt shoulder lifts with a raised arm;
  - a skirt swings with the thigh under it;
  - the edge it hangs from stays pinned.

  Fitted armholes are cut round the whole sleeve with their edge snapped onto a smooth line
  just clear of it. The body under an armhole is painted the shirt's colour, so a gap never
  shows black.
- **Gear must visibly hang from what holds it:**
  - straps go over the belt;
  - pouches sit on the cloth under them and are tilted to its flare;
  - strips are clipped to the belt;
  - bandoliers lie on the shirt.

  Stiff items (a satchel) are rigid on the hips, with the cloth just under them held
  still. Flexible items (staple strips) take the weights of the cloth surface beneath them.
- **Joined parts must touch:** for example, a pistol's top arm sits on its base at a hinge.
- **Keep character structure:** e.g. Lamp's desk-lamp arm is his neck, his lantern swings on
  its own bone, and Stapler's head is a stapler set back inside the hood.

## 5. Rig conventions

- One deform bone per rigid part: `root`, `hips/spine/chest`, `head` (plus neck links where
  the character has them), `upperarm/forearm/hand_{R,L}`, `thigh/shin/foot_{R,L}`, plus cloth
  chains and props (`staff`, `shield`, `lantern`, `gun_{R,L}`).
- Blender-only controls (never exported): `ik_hand_*` and `ik_foot_*`, which copy their rotation to
  the hand or foot, and `pole_knee_*` targets. Each knee pole angle is calibrated so the rest pose
  is unchanged.
- The game strips the root bone's motion. Clips that travel move the root (Lamp's
  `intercept_run`), and the game tweens the unit. Anything that must stay visible (a spin)
  turns the hips and swings the IK and pole targets round the body instead.

## 6. Animation conventions

- **Generated by script** at **60 fps**, every bone keyed on every frame. Loops are seamless.
  A clip is a function of the frame: a loop is a function of its phase, the rest are
  `keyed([(frame, pose), ...])` smooth curves.
- **Pose format:** `{bone: {"rot": (x, y, z) degrees about world axes at the bone's head,
  "loc": (x, y, z) metres world offset}}`. +x leans or tips forward (and swings hanging
  bones back), +y tilts to his left, +z turns to his left. Hands and feet are placed through
  their IK targets, so a moving body must carry its hands (`lowered`).
- **`settle(pose)`** runs on every pose and applies the physics fix-ups:
  - cloth cancels the body's lean so it hangs with gravity;
  - capes and cloaks only swing back, away from the legs;
  - cloth lags the body's turns (from turn speed, not absolute angle, in spins);
  - props like Lamp's lantern hang from their knob.
- **Clip set:** use the game's names from `docs/character_abilities_stats.md`.
  - Standard: `idle`, `move`, `attack`, `hurt`, `broken`.
  - Art clips named after the Art's id (`spotlight`, `pin`, `staple_burst`, `heavy_duty`).
  - Character extras where the game needs them (Lamp's `intercept_run` and `intercept_guard`).
  - **No** `art`, `ready`, `gaze_in` or `gaze_out` clips on 3D models (decided 2026-10-09):
    those moments show idle.
- **Clips with a direction:** the head and neck face where he is going, and the neck centres
  with the body (not just a head turn).
- **Moving clips:** legs stay close under the hips with knees forward. Wide stances only for
  planted poses.
- **Natural gait:** arms swing opposite to the legs, unless the clip deliberately locks the arms
  (Stapler's Naruto run sweeps them back).
- **Pistols and props follow the arm:** swinging an arm back rolls the pistol under the hand,
  purple top to the ground, as it would physically.
- **Travel speed:** the run is authored for the game's run speed, 1.8 m/s (`move.speed`), so
  feet match the floor. `UnitModel` scales playback for slower moves.
- **Hit timing:** hits and shots land on the clip's contact frame, published as `hit`, and the
  game waits for it.
- **Game handoffs:** actions that depend on the game (turning toward an enemy, running into a
  guard spot) are split into clips at the handoff.
- **Physical posing:**
  - Deep sinks fold the thighs into belts and skirts, so lean from the back and keep the
    hips' share of a lean small.
  - Tipping the head back pushes hoods into cloaks.
  - Dropped hands swing into side gear, so hang them out to the side.
  - Arms swung far back meet the cloak.

## 7. Verification checklist (every character change)

1. Rebuild from scripts. `rest` clip report is empty, and every vertex group has a bone.
2. Stress poses: arms raised sideways and forward, thigh kicks and strides, head turns,
   nod and lean.
3. `clip_check(obj, every=1)`. Fix what shows and remove poses that cause contact. Report
   the remaining contact honestly with numbers (triangle pairs, clip, frame).
4. Renders:
   - concept turnarounds side by side with the model (front, back, sides, three-quarter);
   - the 128 px sprite-scale view;
   - close-ups of trouble spots;
   - animation contact sheets (`toyanim.render_strips`).
5. Export, then check the GLB's clip list and per-bone sample counts.
6. `godot --headless --import`, set palette imports lossless, run the full test suite.
7. For tooling refactors, diff the old and new GLB. A character must come out identical.

## 8. Working with the project owner

- When asked "do you know what I mean?", "thoughts?", "any questions?" or "don't edit yet",
  explain the understanding and plan (list the questions), then **wait** for an answer.
- Show model renders for approval **before** rigging and animating, and again after
  big look changes. The owner judges by eye: compare against the concept side by side.
- Translate requests into concrete changes and say what will change. Offer options
  with a recommendation when there's a real choice (lean angle, arm style, arc vs straight).
- Report limitations and remaining overlaps plainly. Never claim clean when it isn't.
- Do not commit unless asked. Keep generated previews and scratch files out of the repo
  (`source/` is gdignored; temporary captures go in the scratchpad).

## 9. Character notes

**Lamp Warden** (`lamp`, about 8k tris, 27 bones):
- **Look:** a desk lamp for a head on an articulated arm (the neck), a robe, mantle, tabard and
  cape, a staff with a hanging lantern, and a shield.
- **Clips:** idle, move (sprint), attack (Pole Strike, hit 0.45 s), intercept_run and
  intercept_guard (Watchful: brace 0.2 s, impact 0.3 s), spotlight, hurt, broken.
- **Known:** a one-frame belt/upper-arm touch in attack; back swings meet the cape.

**Stapler Rogue** (`stapler`, about 13k tris, 24 bones), look agreed against the concept:
- **Head and hood:** a stapler head set back in a low assassin's hood with a forward-leaning
  point and a pale folded rim. Glowing yellow eyes. No hood emblem.
- **Scarf:** a thick neck wrap with a broad tail with ragged holes and a forked end.
- **Cloak:** flared, with ragged holes and torn points.
- **Cream cloth:** a torn shirt (hem tucked under the belt), sleeves, a skirt, and bandaged
  forearms and shins.
- **Black:** body, trousers, gloves and boots.
- **Gold accents:** bandolier rings, buckle, rivets.
- **Satchel:** at his right side.
- **Staple strips:** clipped at his left side.
- **Pistols:** two stapler pistols with jaws hinged open.
- **Boots:** low and domed, with steel toes.
- **Clips:**
  - idle (wide stance, right pistol raised);
  - move (Naruto run: 65° lean with hips 20° and back and chest 45°, arms swept back, pistols
    hanging muzzle-back under the hands, feet landing 13 cm behind the hips);
  - attack (Staple Shot, hit 0.3 s);
  - staple_burst (alternating twin shots);
  - pin (charged heavy shot, hit 0.75 s);
  - heavy_duty (leaping spin into a volley; not in `arts.gd` yet);
  - hurt, broken.
- **Known:** some skirt-against-thigh and belt contact in the deepest crouches (run about 120
  triangle pairs, broken about 100, heavy_duty about 80), hidden under the cloth.

### Planned, agreed in principle

- 3D staples as their own VFX model (`assets/models/vfx/`), fired straight from the muzzle.
- Spring-bone physics (`SpringBoneSimulator3D`) on the cloth chains plus a shader wind ripple
  from the UV2 sway weight. Full soft-body cloth is ruled out for cost and clipping.
