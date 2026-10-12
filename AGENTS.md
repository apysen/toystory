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
| Blender, headless | `D:/Blender/blender.exe --background --python tools/animate_<name>_3d.py` (a fallback only: the owner wants the work done live, below) |
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

- **Lighting (fixed 2026-10-11):** the board sits under a desk whose underside shades it from the
  `Sun`. Units under it are lit by `UnderDeskGlow`, which casts shadows (energy 1.6, range 14),
  and the room's ambient light (0.4). Before, the sun pointed upward and the glow cast no
  shadows, so everything was flat and bright (the owner's note). The `Sun` shines down on the
  open floor beyond the desk. Near-white palettes bloom: the Teacup's whites and Lamp's cream
  sit 8% under their sprites'.

- HD-2D diorama: a modelled, lit 3D room, a free orbit camera and a minimal HUD.
  Units used to be pixel-art sprite cards; they are being replaced by 3D models one
  character at a time (Lamp Warden, Stapler Rogue, Toaster Pyromancer, Teacup Cleric and Umbrella
  Lancer so far).
- Battle interface reading aids and feel (2026-10-12, the owner's picks from the Midnight Suns, Fire Emblem, XCOM and
  Into the Breach discussion): the movement area's lit rim (`reach_area.gdshader`), reach rings and reticles, cover
  shields, type matchup arrows and triangle, the danger toggle (V / Y), strike
  close-ups, hit-stop, shake, damage numbers and the signature letterbox. `docs/battle_composition.md` maps them; the
  test is `tests/integration/battle_ui.gd`. Move-first stays: the full Midnight Suns action-first flow was rejected
  because it would weaken positioning, and so was walking up to a target out of reach (removed
  2026-10-12, the owner's call: Attack lists only what is in reach from where the unit stands).
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

Current characters: `lamp_warden` (Lamp), `stapler_rogue` (Stapler), `toaster_pyromancer`
(Toaster), `teacup_cleric_v2` (Teacup) and `umbrella_lancer` (Umbrella). The Toaster's line art is
drawn by `tools/draw_toaster_details.py` (run it first), Umbrella's by `tools/draw_umbrella_details.py`.

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

Build, animate, check, render and export **live in the owner's open Blender through the MCP**, not
headless (the owner's rule, 2026-10-11): they look at the work in Blender. Leave the result in the
session and hide the other toys standing on the origin; `toy3d.export_glb` exports only the rig's
own actions, so other toys in the session don't leak into the GLB. Headless
(`D:/Blender/blender.exe --background --python tools/animate_<name>_3d.py`) is a fallback only.

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
  to its GLB, and `SCALE` shows a model bigger than built (Umbrella 1.16x, to the squad's height). It swaps in `assets/shaders/unit_model.gdshader`, which matches the card
  lighting and fades by an instance uniform. It reads `<glb>_events.json`. It loops
  `LOOPS` and turns `STANDING` clips toward the camera. It strips root motion from the
  skeleton's root bone and scales the travel loop to the unit's real speed.
- `UnitCard` hosts the model and hides its sprite card. The Gaze object form stays a
  sprite card. `play_art(id)` plays a clip named after the Art when one exists.
- `EventPlayer`: a model's strike waits `contact_time("attack")` (the `hit` event) and
  then the projectile flies. Sprite units keep the old lunge timing.
- Events JSON keys: `attack.hit` (contact or shot frame, seconds), `pin.hit`,
  `intercept_guard.brace` / `.impact`, `flashbulb.flash`, `guard_beam.beam` / `.release`,
  `spotlight.stamp` / `.beam_up` / `.land`, `staple_burst.shot_1` .. `.shot_4`,
  `staple_storm.volley_1` / `.volley_2`, the Toaster's `attack` / `eject` `.slam` / `.hit` /
  `.reload`, `flash_bake.stomp` / `.charge` / `.fire` / `.fire_end`, `overheat.slam` / `.rise` /
  `.erupt` / `.land` / `.reload`, Umbrella's `move_start.lift`, `move_end.land`,
  `lunge.charge`, `lunge_run.speed` (2.6), `lunge_strike.hit`, `canopy.open`, `raincheck.open` /
  `.shield` / `.end`,
  `move.speed` (m/s the run was authored for, 1.8).
- Stapler's staples are a VFX model, `assets/models/vfx/staples.glb` (`Staple`,
  `StapleHeavy`), built by `tools/build_staples_3d.py` (no rig; headless run builds,
  renders previews and exports). `EffectsLayer.staple` flies one straight from a muzzle,
  legs first, drawn 2.2x its built size so it reads at battle zoom; `EventPlayer` fires
  them from the `gun_R` / `gun_L` bones on the clips' shot frames.
- The Toaster's toast is a VFX model too, `assets/models/vfx/toast.glb` (one toasted slice),
  built by `tools/build_toast_3d.py`. `EffectsLayer.toast` launches one from a slot bone
  (`toast_front` / `toast_back`) in a hot, tumbling arc. In his model each slice is tagged
  in UV2.y (1 front, 2 back); the unit shader hides a launched slice until the clip's
  `reload` and browns it after (`UnitModel.set_slice`). Godot flips glTF's V on import, so
  the shader reads `1.0 - UV2.y`.
- Effect sprites are smooth vector art, never pixel art (the owner's rule, 2026-10-11).
  - `tools/draw_vfx.py` draws every sheet: hit spark, crit burst, heal sparkle, Gaze poof,
    Suction swirl, the Cutting Line slash, and the Tea Lash, staple and toast fallbacks.
  - Each is drawn in Pillow with an ink outline and soft glow, at 4x and scaled down, in the
    pixel originals' frames and timing.
  - Sheets sit at 4x the battle's pixel density, which their JSON meta `"scale"` says;
    `SpriteLib.load_vfx` / `EffectsLayer` show them filtered at the right size, with mipmaps on in
    their import.
  - A new effect gets a function there.
- Fire is particles built in Godot (`FireFX`), not modelled: `UnitFire` keeps the Toaster's
  palm flames burning on his `flame_R` / `flame_L` bones (rocket jets back along his hands
  in `move`) and his vents' fire (`vent_R` / `vent_L`, for Heated and Overheat);
  `EffectsLayer` has Flash Bake's cone, Overheat's swirl and pillars, and smoke. No light
  rides on the model: a fire light that close washes the whole model out.
- Additive light and fire must not take the room's fog (`fog_disabled`, `disable_fog`): fog
  tints the whole quad and shows its square edges.
- Art light (flares, beams, bubbles, stage lights) is built in Godot by `ArtLights`, not
  modelled: `EventPlayer` starts each piece on the clip's event, at bone positions read
  from the model (`UnitCard.bone_point`). An Art whose clip is the strike (Flashbulb) lands
  its hits without the attack swing.
- Every character gets an integration test like `tests/integration/lamp_model.gd`,
  `stapler_model.gd`, `toaster_model.gd`, `teacup_model.gd` and `umbrella_model.gd`: the model shows, the expected clips exist (and removed ones do not),
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
  (lamp light, Stapler's eyes), sampled at the swatch's middle. One draw call. A character
  with line art uses a detail atlas instead (below): the same swatches in its top-left
  corner, the art beside them.
- **Line art, not painted cells:** patterns (flame hems, cuff bands, trims, emblems) are
  clean vector line art Claude draws by script (`tools/draw_<name>_details.py`, Pillow, drawn
  at 4× and scaled down) on a 1024 px detail atlas (`toy3d.Character(detail=...)`,
  `DETAIL_SIZE`, palette in the top-left `PALETTE_PX`), laid over the cloth with
  `Builder.map_detail(faces, region, uv_at, wrap)`. Never stepped palette cells. Plan each
  character's line art with its model. Every toy now has it (2026-10-11): Lamp's tabard
  (`tools/draw_lamp_details.py`), Stapler's scarf wrap and bandage seams
  (`tools/draw_stapler_details.py`, `toy3d.bandage(region=...)`; `map_detail(wrap_v=True)` for a
  ring of tube).
- **No painted-on shading:** no fold streaks, darker cells in fold valleys or drawn fold lines.
  Folds are real geometry and the scene's light shades them, also as the cloth moves. Inside
  faces keep their lining colour (a dark cape lining is the fabric, not shading).
  (Lamp's and Stapler's painted folds were removed 2026-10-11. Lamp's greaves keep a lighter
  band on their rolled edges, part of the armour's trim.)
- **Only real light sources glow:** eyes, vents, lamp bulbs and fire. The rest of the model is
  lit by the room; never hang a light on a model (one that close washes the whole model out).
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
- **Nothing floats:** every piece of a model physically connects to the body, even by a few
  millimetres: a head sits on a neck, a cape starts tucked under what it hangs from, a
  brooch is half sunk into the cloth it pins, gear is fixed to the belt it rides on.
  `toy3d.island_gaps(obj)` finds every group of pieces that touches nothing else on the
  model; it must come back empty after every build.
- **No coplanar faces:** two faces lying on each other flicker in Godot. Layers (a trim band,
  a decal-like plate, a vent's glow) stand at least about 1 mm off what is under them.
- **Props that sink stay inside:** something pushed into its holder (toast into the
  toaster) is sized so it disappears completely and never pokes through the bottom.
- **Keep character structure:** e.g. Lamp's desk-lamp arm is his neck, his lantern swings on
  its own bone, and Stapler's head is a stapler set back inside the hood.

## 5. Rig conventions

- One deform bone per rigid part: `root`, `hips/spine/chest`, `head` (plus neck links where
  the character has them), `upperarm/forearm/hand_{R,L}`, `thigh/shin/foot_{R,L}`, plus cloth
  chains and props (`staff`, `shield`, `lantern`, `gun_{R,L}`).
- Blender-only controls (never exported): `ik_hand_*` and `ik_foot_*`, which copy their rotation to
  the hand or foot, and `pole_knee_*` targets. Each knee pole angle is calibrated so the rest pose
  is unchanged.
- Effect bones carry what Godot draws, not mesh: `flame_{R,L}` over the palms, `vent_{R,L}` at
  the vents (the Toaster's fire), and sliding props on their own bones (`toast_front`,
  `toast_back`, `lever`).
- A flag the shader needs per part goes in UV2.y (UV2.x is the cloth sway): the Toaster's
  slices are 1 and 2. Godot flips glTF's V, so shaders read `1.0 - UV2.y`.
- The game strips the root bone's motion. Clips that travel move the root (Lamp's
  `intercept_run`), and the game tweens the unit. Anything that must stay visible (a spin)
  turns the hips and swings the IK and pole targets round the body instead.

## 6. Animation conventions

- **Generated by script** at **60 fps**, every bone keyed on every frame. Loops are seamless.
  A clip is a function of the frame: a loop is a function of its phase, the rest are
  `keyed([(frame, pose), ...])` smooth curves.
- **Pose format:** `{bone: {"rot": (x, y, z) degrees about world axes at the bone's head,
  "loc": (x, y, z) metres world offset, "shrink": (k, k, k)}}`. +x leans or tips forward (and
  swings hanging bones back), +y tilts to his left, +z turns to his left. Hands and feet are
  placed through their IK targets, so a moving body must carry its hands (`lowered`). `shrink`
  (0 full size to 1 gone, about the bone's head) is keyed only on the bones a rig lists in its
  `scaled_bones` property (a prop put away, like the Teacup's book, or her tea drained).
- **`settle(pose)`** runs on every pose and applies the physics fix-ups:
  - cloth cancels the body's lean so it hangs with gravity;
  - capes and cloaks only swing back, away from the legs;
  - cloth lags the body's turns (from turn speed, not absolute angle, in spins);
  - props like Lamp's lantern hang from their knob.
- **Clip set:** use the game's names from `docs/character_abilities_stats.md`.
  - Standard: `idle`, `move`, `attack`, `hurt`, `broken`.
  - Art clips named after the Art's id (`spotlight`, `pin`, `staple_burst`, `staple_storm`).
  - Character extras where the game needs them (Lamp's `intercept_run` and `intercept_guard`).
  - **No** `art`, `ready`, `gaze_in` or `gaze_out` clips on 3D models (decided 2026-10-09):
    those moments show idle.
- **Long, theatrical clips:** attacks and Arts take their time (the owner: "the animations
  are part of the charm"). Give each one anticipation, a build-up, the payoff on the event
  frame and a recovery: Toast Pop is 3.7 s, Eject 4.8 s, Flash Bake 3.8 s. Hurt stays quick.
- **Mirrored hands:** a hand rotation is given for the right hand and the left mirrors it
  (y and z negated), so both roll outward alike and turn back to idle the way they came.
  Check every return to idle for a wrist spinning the wrong way.
- **Arms swept back:** place the hand where it ends up if you just swing the arm back: it
  rolls over with the arm (palm down, fingers trailing). Then tilt the wrist for what the
  hand does (the Toaster's fingers point straight back so his fire jets behind him, not into
  the floor).
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
- **Launched props hand over to the game:** on the frame after a prop is launched, the clip
  sinks it out of sight inside its holder, and Godot flies the real one from there and hides
  the slot until the clip's `reload`. Changes of colour (toast browning) are shader state set
  by the game, never baked into a clip.
- **Prop offsets turn with their parent:** a pose's `loc` on a child bone is in its rest frame
  and follows the parent's rotation (toast moves along its slots however the head tilts).
- **Physical posing:**
  - Deep sinks fold the thighs into belts and skirts, so lean from the back and keep the
    hips' share of a lean small.
  - Bent far over (Eject's almost-flat fold), the cape lies along the back past about 20° of
    lean and its lower links droop off it (`settle`).
  - Keep head nods inside what the head clears (the Toaster's about 10°).
  - Tipping the head back pushes hoods into cloaks.
  - Dropped hands swing into side gear, so hang them out to the side.
  - Arms swung far back meet the cloak.

## 7. Verification checklist (every character change)

1. Rebuild from scripts. `rest` clip report is empty, `toy3d.island_gaps(obj)` is empty (nothing
   floats), and every vertex group has a bone.
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
   Ask the owner first whether they want any other model or animation changes.
6. `godot --headless --import`, set palette imports lossless, run the full test suite, and
   capture real game frames in a window (scratchpad scripts) to check the effects: fire,
   flying props, light, nothing glowing or vanishing that shouldn't.
7. For tooling refactors, diff the old and new GLB. A character must come out identical.

## 8. Working with the project owner

- When asked "do you know what I mean?", "thoughts?", "any questions?" or "don't edit yet",
  explain the understanding and plan (list the questions), then **wait** for an answer.
- Show model renders for approval **before** rigging and animating, and again after
  big look changes. The owner judges by eye: compare against the concept side by side.
- Consult on each ability's animation before animating it: propose the motion (beats,
  timing, what the game draws) and wait for the owner's answer.
- After model or animation changes, ask whether there are more before exporting, importing
  into Godot and running the tests.
- Integrating a signature Art includes its action-ring icon (`tools/bake_action_icons.py`).
- The owner often sends requests while work is running: fold each one in and say how it was
  handled.
- Translate requests into concrete changes and say what will change. Offer options
  with a recommendation when there's a real choice (lean angle, arm style, arc vs straight).
- Report limitations and remaining overlaps plainly. Never claim clean when it isn't.
- Do not commit unless asked. Keep generated previews and scratch files out of the repo
  (`source/` is gdignored; temporary captures go in the scratchpad).

## 9. Character notes

**Lamp Warden** (`lamp`, about 8.6k tris, 27 bones):
- **Look:** a desk lamp for a head on an articulated arm (the neck; no knob on the crown), a
  robe, mantle, tabard and cape, a staff with a hanging lantern, and a shield.
  - The staff stands out in front of his right side: the upper arm drops down and halfway
    forward, the forearm reaches straight ahead to it.
  - The cape is a layer under the mantle: it starts just inside the mantle's hem, comes out
    as wide as the mantle and copies the mantle's skin weights down to row 69.
  - The shield's plate, face and sun are ringed slabs, so the sun lies flush on the curve.
- **Clips:**
  - idle;
  - move (sprint, feet under the hips, toes forward);
  - attack (Pole Strike, hit 0.45 s);
  - intercept_run (every step lands like the sprint's) and intercept_guard (Watchful: steps
    out to a wide, staggered brace; brace 0.2 s, impact 0.3 s);
  - flashbulb (throws the lamp head out; flash 0.45 s);
  - guard_beam (staff levelled at the ally; beam 0.37 s to release 0.93 s);
  - spotlight (signature, 2.2 s: stamp 0.37 s, sky beam 0.8 s, light lands 1.1 s);
  - hurt, broken.
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
  - staple_storm (signature Staple Storm: leaping spin, then two volleys all round, volley_1 1.17 s
    and volley_2 1.32 s; in the game, a ring of staples flies out on each volley);
  - hurt, broken.
- **Known:** some skirt-against-thigh and belt contact in the deepest crouches (run about 120
  triangle pairs, broken about 100, staple_storm about 80), hidden under the cloth.

**Toaster Pyromancer** (`toaster`, about 8.9k tris, 33 bones; 27 deform), look agreed against
the concept:
- **Head:** a rounded steel toaster on a neck, glowing vents for eyes, gold rivets, a lever on
  his left side (its own bone, resting halfway down its slot) and two slices of toast standing
  one behind the other (`toast_front`, `toast_back`, 11 cm tall so a pressed lever sinks them
  right in).
- **Cloth:** a cream robe with drawn line art (flame hem, red front bands, sleeve stripes and
  flaming cuffs), a red scarf wrap with a sun brooch, a red cape tucked under the scarf.
- **Gear:** a brown belt with a satchel fixed on his left hip; open black gloves palm up with
  a `flame` bone over each palm; steel legs. No wrist bands.
- **Clips** (all long and theatrical, the owner's choice):
  - idle (wide stance, left flame raised beside his head, right low by his hip);
  - move (rocket glide: no steps, arms swept back with the hands rolled over and the fingers
    pointing straight back, the fire jetting behind him; 1 s loop);
  - attack (Toast Pop, 3.7 s: sizes up the target, wind-up and lever slap at 0.87 s, only the
    front slice sinks, a heating rattle, the pop at 2.27 s, a browned slice back at 2.87 s);
  - eject (4.8 s: slap 0.67 s, long strain, folds forward about 80° so the slots aim at the
    target, blast 2.83 s, recoil half a step back and return, reload 4.2 s);
  - flash_bake (3.8 s: stamp 0.3 s, hands drawn back to the hips from 0.73 s, palms thrust
    out and the cone from 1.73 s to 2.43 s, slid back 4 cm, shakes his hands out);
  - overheat (signature, 5.4 s: slam 0.53 s, shudder, arms up, lifts 32 cm at 1.83 s, erupts
    at 2.5 s launching the toast, hangs, floats slowly down, lands 4.4 s, slices back 4.93 s);
  - hurt, broken (2.5 s, the vents go dark).
- **Game:** Overheat strikes every enemy within 1.6 m (Might 7) and burns 20% of his max HP,
  never the last point; a slice flies at each enemy struck, front and back slots in turn.
- **Known:** the left forearm cuff touches the lever tab for about 4 frames at each slap (about
  20 triangle pairs); robe/belt contact in Eject's deep fold (about 170), hidden by the belt.

**Teacup Cleric v2** (`teacup`, `tools/build_teacup_cleric_v2_3d.py` and
`tools/animate_teacup_cleric_v2_3d.py`; v2 replaced v1 in the game, 2026-10-11). The animate script's
`export_game()` writes `assets/models/teacup/teacup_cleric.glb` and `teacup_cleric_events.json`; its
sources, previews, contact sheets and cloth colliders stay in `assets/models/teacup/source/v2/`:
- **Clips:** idle, move (fast scurry), attack (Tea Lash, 3.8 s, hit 2.37 s: the dart flies from
  `bend_L`), warm_pour (4.8 s, hit 2.9 s), steady_sip (3.5 s, hit 2 s), tea_break (signature, 6 s:
  burst 3.6 s, hit 3.8 s, return 4.67 s), hurt, broken.
- **Game:** Tea Break heals every ally within 1.6 m (Teacup too) for 20% of max HP and removes one
  negative status each (`Battle.allies_in`, `_cleanse`). `EventPlayer` lands her heals on each clip's
  `hit`; Tea Break pushes the camera in and runs an amber ground ring on `burst`.
- **Tea effects (Godot):**
  - **Bent tea:** `TeaRibbon` strips (`tea_ribbon.gdshader`). They follow her `bend_*` bones or
    paths `EventPlayer` runs between the clip's events: Tea Lash's stream out of the cup to her
    hovering hand (a `tea_strand` joining the two), then the rope and the dart, Warm Pour's
    figure of eight, arc and spiral, Steady Sip's thread and blue ward, and Tea Break's column,
    ring, burst, spirals, rain and return.
    Tea leaving or entering her cup is a `_fountain`: it goes straight up 14 cm clear of the rim
    before it bends toward her hands, so it never cuts through the porcelain (the owner's note).
    Steady Sip's thread lobs to the ally in a medium arc that peaks about 0.6 m over the cup. It's
    drawn as a strand along the curve (`_tea_thread`), so it stays smooth at any frame rate. They are her own tea brown with the crest's tan down
    the middle and don't glow (the owner's pick, 2026-10-11; amber light is only Tea Break's floor
    ring and the heal sparkles). `EffectsLayer.tea_width` / `tea_length` scale them.
  - **The cup:** `UnitTea` on the model keeps the steam, the hurt splash, and broken's stream and
    puddle. `TeaLevel` (a `SkeletonModifier3D`) holds the tea a third lower per hit until the next
    attack or Art refills it. Godot gives the skin the modified pose but scripts read the clip's,
    so check `UnitTea.lowered()`.
  - **Slosh (the owner's pick, 2026-10-11):** the tea is plain brown (the crest ring was taken out).
    It's tagged UV2.y = 3 with its radius in UV2.x.
    - The unit shader heaves it in waves (`tea_slosh`), and `TeaLevel` tips it about in the cup,
      as far as the room under the rim allows.
    - It's hardest while she runs. There, drops spill over the rim at each high point and lower the
      tea, at most a third of the way.
  - **Particle gotchas:**
    - Droplets use `tea_drop.gdshader`: blended particles not yet born draw as black discs, and the
      shader discards them. Continuous emitters are pre-warmed.
    - A one-shot burst at explosiveness 1.0 draws nothing, so bursts use 0.95.
    - Drop colours are sRGB.
- **Spring-bone cloth (Godot):**
  - **Data:** `export_game()` also writes `teacup_cleric_springs.json`: all 20 chains, their bones'
    heads and tails, and the collider capsules, in Godot's frame.
  - **`UnitSprings`:** builds one `SpringBoneSimulator3D` from that file. Stiffness, drag, gravity,
    per-link limit and joint radius are set per kind of cloth (`cloth`, an Inspector export).
    - A chain that rests inside a capsule (the body's rough envelopes) gets a slimmer copy, so
      it's never shoved out.
    - `SpringLimit` modifiers record the clip's pose before the simulation and clamp each link
      after it. Godot's springs have no angle limits of their own.
    - Limits per link: sleeve drape 10° (20° over its two links, as agreed), cape 15°, skirt 10°,
      mantle 8°, cords 25°, tassels 30°.
  - **Shader ripple:** her cloth also ripples slightly by its UV2 sway weight (`cloth_ripple`).
  - **Behaviour:** standing, the cloth settles back within about 3° of the clip. Running, turning
    and spinning, it swings out to its limits.
  - **Known:** at the fastest moments of Tea Break's spin, the cape's side corner can kick out
    into a slight point (its three columns swing separately).
- **Palette:** her ivory, cream, warm cream and gold sit 8% under the sprite's (in the build's
  `PALETTE` and the line-art script), the owner's pick: at full brightness the battle room's bloom
  haloed her porcelain gold.
- **Built pose (the owner's pick, 2026-10-11):** the concept's stance instead of the neutral pose in
  §4: upper arms down under the mantle, forearms out and up (book out on her right, left hand
  raised). Her bell sleeves are modelled hanging under gravity, so their ivory outsides face the
  front only with the arms out. (`TEACUP_ARM_POSE=neutral` still rebuilds the forward pose.)
- **Hanging chains:** the sleeves' drapes (`sleeve_1..2`), the brooch cords (`cord_1..3`) and the
  tabard tassels (`tassel_0..2`) hang on their own bones; `settle()` hangs them with gravity against
  collider capsules, and the chains and capsules are written to `teacup_cleric_v2_colliders.json`
  for Godot spring bones.
- **Book:** pinched one-handed at the foot of the spine (`TEACUP_BOOK=d`, the owner's pick): the hand
  under the book beside the spine with the cover's bottom edge in its web, the palm and four fingers
  rising up that cover's back (fingers rooted on the palm, as the owner asked), and the thumb round
  under its foot and up its pages beside the gutter, holding them open.
  - **Book rig:** the book is on its own `book` bone (child of `hand_R`, up the spine from its foot
    in her palm). Each cover is on a hinge bone along the spine (`cover_R`, `cover_L`), and the
    thumb is on `thumb_R`. She shuts the book by lifting the thumb 45° straight off the pages,
    then swinging `cover_R` (the cover under her thumb) 94° onto `cover_L`, which stays in her
    fingers. Both covers hinge on one line, so a thin wedge of pages shows when it's shut. She
    puts the book away (the in-game inventory move, the owner's pick) by dropping her hand out
    at her right side, by and just behind her hip (further back, the bell sleeve drags through
    the robes and cape), and shrinking `book` to nothing in her palm in about 6 frames, with no
    effect; she takes it back out the same way.
  - **Bending:** `bend_R` / `bend_L` are effect bones from each palm out along its normal, the
    path Godot draws her bent tea along.
- **Cloth chains (for Godot spring bones, the owner's pick 2026-10-11):**
  - **Coats:** above the belt they follow the body (hips → spine → chest, like the tabard).
    Below it, the three robe layers hang on a ring of six two-link chains
    (`skirt_{FL,L,BL,BR,R,FR}_1..2`).
  - **Cape:** in three columns (`cape_L_*`, `cape_*`, `cape_R_*`).
  - **Mantle:** four edge bones on its lower half between the arms (`mantle_{FL,FR,BL,BR}`).
  - **In the clips:** the skirt and mantle bones stay at rest. The side cape columns are placed
    each frame where the middle column carries them (`follow_cape`), so the cape moves as one
    piece; turned about their own tops, they swing into the coat.
  - **The colliders JSON:** `springs` lists every chain for Godot; `chains` is only what
    `settle()` hangs.
  - Her model has 71 bones.
- **Bell sleeves (the owner's request, 2026-10-11):**
  - **Bell bone:** each bell is on `bell_{R,L}` (child of the forearm, from the elbow's ring to
    the opening), and the drape hangs from it.
  - **Slide:** `settle()` slides the bell up to 5.5 cm back toward the elbow as the forearm rises
    past her built angle, so the cuff comes out.
  - **Drape on a raised arm:** held 45% of the way to the bell (`DRAPE_HOLD`). It swings at most
    20° off it (60° as the forearm hangs down; `DRAPE_SWING`), because it's sewn along the
    forearm.
  - **Rest gap:** the sleeve rests 6 mm above the arm.
  - **Elbow blend:** the forearm takes the sleeve from just before the elbow.
  - **Collision:** upper-arm capsules keep the drape out. The bell/under-sleeve pairs are
    clip-checked; the slim upper arm hidden inside the upper sleeve is not.
  - **Tried and dropped:** turning the bell about the forearm to hang its slack downward. It
    barely helped, and it swung the bell into the robes on a forearm pointing down.
- **Tea:** a disc of concentric rings with a stylised wave and a tan crest ring on its own `tea` bone
  (child of `head`), 12 mm under the rim, tagged UV2.y = 3. `settle()` keeps it level with the world
  but at most `TEA_MAX_TILT` (about 4°) off the cup's own tilt, so it never reaches the rim; the
  colliders JSON carries it for Godot's TeaSlosh shader (to come).

**Umbrella Lancer** (`umbrella`, about 13.4k tris, 54 bones; 48 deform; the plan and the owner's
answers are in `docs/umbrella_animation_plan.md`):
- **Look:** an open umbrella worn as a wide hat (gold drops on `hat_tip_0..7`), a blank cream face,
  a teal scarf (the owner's pick: the green of his livery), silver plate, a teal tabard with a lion
  and fleur, teal pauldrons, a teal cape the same inside and out (gold hem and fleurs both sides).
  - **Cape:** it lies on his back and skirt from the shoulder blades down and hangs almost straight
    past them, flaring only a little at the hem (the owner's note: standing off his back, it stuck
    out). Its first bone pivots at its top edge. In `settle()` it goes with every lean forward and
    hangs off his shoulders on a lean back.
  - **The lance:** a real stick umbrella's layout, about 1 m: eight ribs hinged at the notch, a
    sliding runner and eight stretchers, all on bones; `canopy(deg)` in the animate script opens it
    (72 degrees in the float). The canopy is a cloth shell with a lining, so it shows the same panels
    inside as out (the owner's note) and the ribs under it.
  - **Rig:** the `lance` bone hangs off `root`, not the hand. `settle()` carries it in his left fist
    from the fist's own grip each frame (`_gL` pseudo-bones: grip point, shaft and wrist directions in
    the body's space), so `broken` can let go of it. His arms reach only 13.9 cm; a grip out of reach
    is pulled in toward the shoulder, and `grip_check()` reports any fist short of its grip.
  - **Right arm:** it hangs relaxed at his side in every clip (the owner's pick), with gravity under
    the shoulder (`_hangR`), except where it pumps (the charge), flourishes (the bow) or rests on a
    knee (broken).
- **Clips:** idle (umbrella shouldered pike-style, head tipped 12 degrees right to clear it);
  move_start (0.6 s: crouch, spring, it pops open at the top; `lift` 0.22 s), move (Mary Poppins
  float 20 cm up, canopy tilted to his heading), hover (the float standing still), move_end (0.7 s:
  toes first, it snaps shut, back on his shoulder; `land` 0.28 s); attack (Tip Thrust, 3.4 s, hit
  2.2 s); lunge (1.5 s lead-in, ends couched), lunge_run (couched run loop, 2.6 m/s), lunge_strike
  (hit 0.2 s); canopy (3.2 s, open 1.2 s); raincheck (signature, 5.2 s: open 1.1 s, twirl, shield
  2.77 s, end 4.17 s with a bow); hurt (0.6 s); broken (2.5 s: the umbrella pops open, flies out of
  his hand and lands over him like a little tent).
  - The umbrella only ever leaves or reaches his shoulder out to his side (`OUT_BACK`, `OVER`,
    `UPRIGHT`), outside the hat's brim.
- **Game:**
  - **Size:** built from his smaller sprite (0.77 m to the hat's cross), he is shown 1.16x
    (`UnitModel.SCALE`, the owner's pick) so he stands 0.89 m, the squad's average. The whole model
    node scales: clips, springs and bone positions follow, and `event_time(.., "speed")` and the
    travel loops' pace scale with it.
  - **Float:** `UnitModel` floats a model that has `move_start`: moving launches him, stopping
    hovers, `land_after` (3 s of game time) still lands him, and `UnitCard.land_now()` (called as
    his action ring opens) lands him at once. Any other clip asked for aloft waits for the landing.
    Dust (`EffectsLayer.dust`) kicks up on `lift` and `land`.
  - **Lunge:** `EventPlayer` plays the lead-in, runs the dash's `move` event as `lunge_run` (never
    the float) and the strike as `lunge_strike`.
  - **Canopy:** shimmer and "Half Cover" over each neighbour on `open`.
  - **Raincheck:** he faces the nearest enemy that can shoot; the camera pushes in; vector rain
    (`EffectsLayer.rain`, `rain_streak` and `rain_splash` from `tools/draw_vfx.py`) falls over 2 m
    from `open` to `end`. Rules: until the next Player Phase, a ranged enemy attack on an ally
    within 2 m (centre to centre) that could reach him goes to him for 80% damage
    (`Battle.raincheck_interceptor`, before Watchful).
  - **Dev:** `UnitProfile.dev_in_squad` (on for Umbrella, the owner's request for testing) starts
    him in the squad at `dev_squad_tile`; `SliceFixtures` leaves it off, so the rule tests check the
    real slice.
- **Known contact** (triangle pairs, every frame): knee cops under the skirt hem in crouches and
  the run (up to 180, `lunge_run`), sitting in broken (shins under the tabard, up to about 170),
  the cape's top tucked into the scarf wrap (8-22), the umbrella past the brim as Raincheck swings
  it to the front (42; the owner's allowance for Arts).

### Planned, agreed in principle

- Spring-bone physics on the cloth chains plus a shader wind ripple from the UV2 sway weight
  (done).
  Full soft-body cloth is ruled out for cost and clipping.
  - Decided 2026-10-11: physics is Godot's alone, not baked in Blender. The game tweens units and
    strips root motion, so only runtime springs react to travel and turns.
  - The clips keep `settle()`'s gravity hang as the base the springs move from.
  - Built for every toy (2026-10-11):
    - The Teacup's 20 chains come from her own export (above).
    - Lamp (cape, tabard, lantern), Stapler (cloak, scarf) and Toaster (cape) get theirs from
      `toy3d.export_springs(obj, SPRINGS)`. Each animate script lists its chains in `SPRINGS` and
      calls it after `export_glb`.
    - `toy3d.export_springs` sizes a capsule round each limb and the trunk from the mesh skinned
      to it. Lamp's staff is left out because its bone doesn't run along the pole.
    - `UnitSprings.cloth` holds each kind's tuning.
  - Standing, every toy's cloth settles back onto its clip (within about 2°); running, stopping
    and turning, it swings out to its limits.
  - Their rigs keep their single chains. Splitting cloth into more chains, as on the Teacup, would
    mean rebuilding the model.
