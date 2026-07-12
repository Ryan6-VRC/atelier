# Animator schema — the `CompileController` authoring surface

The YAML language `CompileController` compiles into a `.controller` (`animator.md` owns the tool contract —
PASS/FAIL, atomicity, advisories). This document is the surface you author against: every key, the
accepted values, and the traps. The **enforcement mechanism is the parser + validator** — they refuse
unknown keys, bad values, and semantic defects **by name and line**, so a wrong guess is a legible error,
never silent corruption. Author against this, and iterate on the error text when unsure.

The three fixtures under `vrc-unity-tools/fixtures/animator-substrate/` (`debounce`, `smoother`, `codec`)
are the runnable companions — each compiles clean, lints PASS, and is emulator-verified. Snippets below are
drawn from them. The definitive grammar is `AnimatorSchemaYaml.cs` (parse) + `ControllerEmit.cs` (emit) +
`SchemaValidation.cs` (validate), and on the read side `ControllerDecompile.cs` + `AnimatorSchemaEmit.cs`
(serialize); when this doc and those disagree, the code wins — tell someone.

The surface is the compile↔decompile round-trip for the controller **graph**: the layers, states,
transitions, motions, and behaviours you author both compile and survive a `DecompileController` read
([Decompile output](#decompile-output)). Authoring metadata a `.controller` does not store — `basis`,
`role`, and per-param `aap`/`scratch`/`vrc` (they live in the descriptor / `VRCExpressionParameters`) —
decompiles to canonical form, not its authored value (`avatar-root` / `fx`; params rebuild as name+type+
default only). The much-shrunken [Not yet in the schema](#not-yet-in-the-schema) section lists what a
compile still rejects.

## YAML subset

A bounded block/flow YAML: 2-space block mappings and `- ` sequences, flow `{k: v}` / `[a, b]`, `#`
comments, single/double quotes. Scalars infer: `true`/`false`/`on`/`off` → bool, `~` or empty → null,
integer → int, decimal → float, else string (quote a string that would otherwise infer, e.g. `"on"`).
**Refused by name+line:** anchors `&`, aliases `*`, tags `!`, block scalars `|`/`>`, multi-doc `---`, tab
indentation. Duplicate keys in one mapping are refused (names are identity).

## Document skeleton

```yaml
schema: 1                    # required; only 1 is supported (the SDK-drift firewall)
controller: Debounce_Fx      # required; names the output → <outDir>/Debounce_Fx.controller
basis: avatar-root           # REQUIRED — avatar-root | mount-root; frames the paths inline clips bake against
role: fx                     # fx | base-fx | gesture | action | sitting | tpose | ikpose | additive | base

defaults: { … }              # inherited transition/WD settings (below)
parameters: { … }            # map: name → spec
layers: [ … ]                # ordered list of layers
clips: { … }                 # map: name → inline clip
_notes: anything             # any TOP-LEVEL key starting `_` is compile-ignored (Decompile's output channel)
```

`basis:` has no default — omit it and the compile refuses (an unframed clip path is a silent-misbinding
landmine). `role: base-fx` requires at least three layers. A `_`-prefixed key is ignored **only at the
document top level**; nested `_` keys hit "unknown field".

## defaults

Transition and Write-Defaults settings every layer/state/transition inherits unless it overrides them.

```yaml
defaults:
  writeDefaults: on                                    # per-layer and per-state override this
  transition: { duration: 0, exitTime: none, interruption: none }
```

`transition.exitTime` accepts only `none` here (a per-transition `exitTime:` sets an actual value).
`interruption`: `none | source | destination | sourceThenDestination | destinationThenSource`.

## parameters

A map of name → spec. Shorthand is the bare animator type; longform is a map that must carry `type`.

```yaml
parameters:
  RawInput:   bool                                          # shorthand: bool, default false
  Smoothed:   { type: float, aap: true }                    # AAP output (written by a clip curve)
  Work:       { type: float, scratch: true }                # internal residue — kept OUT of the params asset
  GrabToggle: { type: bool, default: true, vrc: { synced: true, saved: true } }
  VelX:       { type: float, vrc: { synced: true, osc: true } }
```

- **`type`** is the *animator* type: `bool | int | float`. `default` for a bool accepts `true`/`false` or a
  number; otherwise a number.
- **`aap: true`** documents that clips write this float as an animator-parameter curve (the AAP idiom). It
  is a legibility marker — emission binds *any* clip write of a declared parameter name as a param curve
  regardless of the flag (see [clips](#clips)). Set it anyway so intent reads.
- **`scratch: true`** = an internal/working param. It is still a real animator parameter; it is only
  excluded from the emitted `VRCExpressionParameters` legibility asset.
- **`vrc:`** drives that asset. `synced`/`saved` set the flags; `type` overrides the listed value-type when
  it differs from the animator type (a bool read as a float DBT weight). `osc: true` records "this name must
  survive the build" as intent — pair 1 stores it but takes no action on it.

**The params asset.** The compiler emits a `<controller>_Parameters.asset` listing every declared param
**except** VRC built-ins and `scratch:` ones — *even unsynced ones* (`networkSynced=false`, zero sync-bit
cost), so a human reading the merged FX sees them. Nothing to declare beyond `parameters:`; `vrc:` only
tunes the entries.

## layers and states

A layer wraps a **root state machine**: named states, nested sub-machines, Entry/AnyState ladders, and one
`default`. `states:`, `machines:`, `entry:`, `any:`, `behaviours:`, and `default:` are the **machine body** —
the identical keys a layer's root and every sub-machine carry, so nesting recurses.

```yaml
layers:
  - name: Debounce           # weight (default 1), mask (AvatarMask asset path), blend (override|additive),
    states:                  #   writeDefaults — all optional, override the defaults/inherited values
      Idle:
        motion: ~                                    # deliberate empty state (no motion)
        behaviours:
          - driver: { set: { Debounced: 0 } }
        transitions:
          - { to: Pending, when: [ RawInput is true ] }
      Pending:
        motion: { clip: timer }
        transitions:
          - { to: Active, when: [], exitTime: 1.0 }  # unconditional, fires when the clip ends
          - { to: Idle,   when: [ RawInput is false ] }
      Active:
        motion: { clip: hold_on }
        behaviours:
          - driver: { set: { Debounced: 1 } }
        transitions:
          - { to: Idle, when: [ RawInput is false ] }
    default: Idle            # a direct state OR direct sub-machine of this machine; the machine enters here
```

State fields: `motion`, `speed`, `speedParam`, `motionTimeParam`, `mirror`, `writeDefaults`, `behaviours`,
`transitions`. Transition ladders are **first-match, top to bottom** per source state (list order is priority).

### sub-machines and Entry/AnyState ladders

```yaml
    machines:                                            # nested sub-machines (same machine body, recursively)
      Aim:
        states: { … }
        entry: [ { to: Ready, when: [ Loaded is true ] } ]     # Entry ladder — conditions only
        any:   [ { to: Reset, when: [ Abort is true ], canTransitionToSelf: false } ]
        default: Ready
```

`entry:` / `any:` are ordered, first-match transition lists. `canTransitionToSelf` is valid **only** on an
`any:` rung (fail-loud on `entry:`). A `default:` naming a direct sub-machine enters it as an unconditional
catch-all, ordered after any `entry:` rungs.

### layout

`layout:` records Unity graph node positions so a hand-arranged controller survives `Decompile→edit→Compile`.
A machine-body key (root and every sub-machine may carry one), it is authored by hand only rarely —
`DecompileController` writes it, and only for a machine whose nodes sit off their defaults, so a block's
**presence signals a human arrangement; its absence, don't-care.**

```yaml
    layout:
      nodes: { Idle: [300, 0], Aim: [600, 0] }   # states + sub-machine nodes, by name; [x, y]
      entry: [50, 0]                             # the four special nodes
      any:   [50, 60]
      exit:  [50, 120]
      parent: [50, -60]                          # the "up" node; sub-machines only
```

- **`nodes` keys are `EscapeSegment`-encoded** (an addressing form — a `/` in a name becomes `\/`), **not**
  the raw literal a `states:` key carries. One node's name has two representations by design: literal as its
  own key, escaped as an address. In double-quoted YAML the backslash then doubles (`"A\\/B"`).
- **Absent → grid.** No block ⇒ every node lands on the compiler's default grid; a hand-authored document
  needs no coordinates.
- **Partial → listed win, rest grid.** List only the nodes you place. This is how you drop a new state into
  an existing arrangement: add its `nodes` entry near its siblings' coordinates; omit it to grid-fallback.
- **Unknown node → compile error.** A `nodes` key naming no state/sub-machine of its machine fails (a
  leftover after a rename/delete, or a typo).

Overlap is **unmanaged by design** — a placed or gridded node may land on another; a one-drag fix for the
human, not the compiler's concern.

## transitions and conditions

```yaml
transitions:
  - { to: Active, when: [ Work greater 0.5 ], exitTime: 1.0, duration: 0 }
  - { to: Exit,   when: [ Done is true ] }          # `to: Exit` is the exit transition
```

Transition fields: `to` (a target address — below — or `Exit`), `when` (condition list, empty = unconditional),
`exitTime`, `duration`, `fixedDuration` (default **true**), `interruption`, `ordered` (default **true**),
`mute` / `solo` (bool, default-elided when false), `name` (a plain label; state/`any:` ladders only, refused
on an `entry:` rung whose emit path can't carry it). `canTransitionToSelf` is
an `any:`-ladder-only field. Unset `duration`/`exitTime`/`interruption` inherit `defaults`.

**Conditions are strings: `<param> <op> <value>`, exactly three tokens.** `value` is `true`/`false` or a
number. The operator must match the parameter's declared type (validated):

| Param type | Valid ops | Notes |
|---|---|---|
| `bool`  | `is`, `isNot` | `is true` / `is false` — value folds into Unity's If/IfNot correctly |
| `int`   | `greater`, `less`, `equals`, `notEqual` | discrete compares |
| `float` | `greater`, `less` | Unity forbids float equality — no `equals`/`notEqual` |

**Trap — the never-firing transition is a compile error.** A state→state transition with **no condition and
no exit time** can never fire; the graph lint fails the compile (`deadTransition`). An unconditional hop
needs `exitTime` (and its source state a motion, or the default 1s empty-state length — see the codec
fixture). A motionless state's exit-time still advances; that is not an error.

### Cross-machine addressing

A `to:` target names a state or sub-machine by one of these disjoint forms (`ControllerEmit.ResolveName`):

- **bare `Name`** — resolves in the referencing machine's **own** scope (its direct states + direct
  sub-machines) only.
- **`Sub/State`** — a path from the **layer root**: each non-final segment a sub-machine, the last a state
  or sub-machine.
- **`/Name`** — absolute from the layer root. This is the only way to hit a **top-level** entity from inside
  a nested machine (a bare single segment would read as local).
- **bare `/`** — the layer-root state machine itself ("re-enter the layer at its default").

`default:` is always a bare **local** name (a direct state or sub-machine of its own machine), never a path.

**Name escaping.** A literal `/` or `\` inside a state/machine name is escaped `\/` / `\\` **in an
addressing/path context**; a path splits on **unescaped** `/` only. A bare local reference and non-path
scalars (a state's own name key) stay unescaped.

## motions and blend trees

A state's `motion` (and a tree child) is exactly one of: a `clip`, a `ref`, a `tree`, or `~` (empty state).

```yaml
motion: { clip: aap_min }                             # an inline clip, by name (must be under clips:)
motion: { ref: "Assets/Anims/Walk.anim" }             # a project-path .anim / .asset motion
motion: { ref: { guid: 0123…, fileID: 7400000 } }     # an FBX-embedded / SDK-proxy motion
motion:                                               # a blend tree
  tree: direct
  children:
    - tree: 1d
      param: Smoothed
      directWeight: SmoothFactor                      # this child's Direct blend-weight param
      children:
        - { clip: aap_min, threshold: 0.0 }
        - { clip: aap_max, threshold: 1.0 }
```

Tree `kind` (case-sensitive): `1d`, `simpleDirectional2d`, `freeformDirectional2d`, `freeformCartesian2d`,
`direct`. A tree carries `param` (blend X) and `paramY` (2D only); `direct` uses per-child `directWeight`
instead, and may set `normalized: <bool>` (the Direct "Normalized Blend Values" toggle — sum-to-1 vs raw
additive; omitted ⇒ Unity's default). An optional `name:` labels the tree (any scalar except a line break).
Omitted, the compiler generates one — `<State>_BlendTree` for a root tree, `<parent>_<childIndex>` nested —
and Decompile emits `name:` only when the actual name differs from that formula. Each child is a motion
**plus** its placement:

- **1D**: `threshold: <n>`
- **2D**: `x`/`posX` and `y`/`posY`
- **Direct**: `directWeight: <paramName>`
- any child: `timeScale` (negative is legal — reversed motion), `mirror`, `cycleOffset`.

Trees nest (a child with `tree:`) and refs chain across `.asset` files. A **bare** `ref: { guid }` that
doesn't resolve fails the compile. Marking it `ref: { guid: …, unresolved: true }` instead **tolerates** a
genuinely-missing asset: the motion slot emits null (a clean-empty state) and the compile writes a RunLog
advisory naming the owning state + the verbatim GUID. This is the round-trip's one lossy step (a dangling
vendor ref decompiles back with the same marker) — not a license to author against an asset you could fix.

A **path** `ref:` to a project `.anim` may resolve to a hand-owned clip or to one a clips file authored via
`CompileClips` — the controller cannot tell them apart, which is exactly what lets a clip be *promoted* from
YAML to human ownership with no controller edit (§clips). Compile a clips file **before** the controller that
refs into its `outDir`: a controller has no back-reference to its clips file, so an unresolved path ref there
usually just means the clips file is uncompiled, not that the asset is missing (`animator.md`).

## clips

Float-curve clips keyed by name — embedded inline under a controller (below), or emitted as external `.anim`
assets from a clips file (§external clips). Three forms:

```yaml
clips:
  timer:   { seconds: 0.2 }                           # duration-only → an inert carrier (below)
  hold_on: { set: { Debounced: 1 } }                  # constant write, held for the clip length
  toggle:  { set: { "Prop/Renderer.enabled": 1 } }    # scene binding (below)
  fade:                                               # keyframed
    length: 0.5
    curves: { "Head/Light.intensity": [ [0, 0], [0.5, 3] ] }   # [time, value] pairs
```

- `seconds:` (alias `length:`) declares the length. A `set`/`curves` clip with no `seconds` derives its
  length from the keys, flooring at one frame (1/60 s).
- **Curve tangents.** A `curves:` value is normally the bare list `[[t,v],…]` — **flat** tangents, the
  default: the segment eases between keys, so a two-key "ramp" bows instead of running straight. For a
  straight proportional ramp (a frame-time `TimeRamp`, a linear sweep) give that curve the map form
  `{ tangents: linear, keys: [[t,v],…] }`; `tangents:` takes `linear` or `flat`, per curve. Round-trip
  keeps flat curves in the bare-list form (byte-identical to documents predating this option) and emits
  the map form only where a curve is linear — see `vrc-patterns/blendtree-math` for a worked frame-time rig.
- **Binding resolution.** A bare identifier naming a **declared parameter** binds as an animator-parameter
  curve — the AAP / param-write mechanism (`aap_min: { set: { Smoothed: 0.0 } }`). Anything else is a scene
  binding parsed as **`path/Component.property`**: split on the last `/`, then the **first** `.`. So
  `Prop/Renderer.enabled` → path `Prop`, `Renderer`, `enabled`. The split takes the first dot because a
  component type never contains one but a property can, so `Body/SkinnedMeshRenderer.blendShape.Smile` and
  `Hat/MeshRenderer.material._Color.r` resolve — blendshapes and material sub-properties are authorable
  inline. `Component` resolves in the **`UnityEngine` namespace only** (Renderer, SkinnedMeshRenderer,
  Light, Transform, …); UI (`UnityEngine.UI`) and VRC-SDK components are out of scope and refused fail-loud.
- **Carrier.** A `seconds`-only clip (no `set`/`curves`) emits a flat curve on a reserved scratch Animator
  parameter (`_CompilerNull` — declared on the controller on first use, kept out of the emitted
  VRCExpressionParameters) purely to give the clip an honest length: it animates nothing and resolves against
  any avatar root, so the broken-binding lint stays clean. This is why a dwell timer is `{ seconds: N }` and
  never a hand-written empty clip. A clip with neither content nor `seconds` is refused, and `_CompilerNull`
  is reserved — a document may not declare it.

### external clips and ownership

The same `clips:` grammar lives in two places. **Inline** under a controller's own `clips:`, a clip embeds as
a hidden sub-asset (the default, unchanged). **In a clips file** — a schema document with a top-level `clips:`
(plus `schema:`, `basis:`, and any `parameters:` its AAP bindings need) and **no `layers:`** — `CompileClips`
(`animator.md`) emits each clip as a standalone, *visible* `.anim` a human can open and edit. A controller
reaches such a clip through the ordinary `motion: { ref: "<outDir>/<clip>.anim" }` (§motions) — no new
directive — so one controller mixes embedded and external clips freely.

**Choosing the mode.** The pattern library and any self-contained, regenerable artifact embed *everything* —
the clip is a projection of its YAML, and the human owns the YAML, not the clip. In human-agent real-avatar
work, route per clip on one question: **is the `.anim` or the YAML the better surface to see, change, and
repath this clip's content?**

- **Embed** — *generated plumbing*: a blend-tree leaf, a constant endpoint, an AAP / smoother / codec member,
  or any near-identical grid the compiler emits from a few YAML numbers. Its content regenerates trivially and
  a rename or retune is faster in the YAML source; external files would only litter the folder. Every
  all-animator-parameter (AAP) clip is this — and so are the ~8 lilToon endpoints of a `color-adjust` / `hsv`
  rig, *even though they target a material*: a scene/material binding is necessary for external but not
  sufficient.
- **Externalize** — a *hand-authored artifact* a human sculpts and enters as a unit: a blendshape or transform
  pose, an expression, a toggle's visible target — especially multi-key / multi-binding, or reused across
  states. The `.anim` and the Animation window are genuinely the better authoring surface, and out-of-band
  repaths (`RepathClips`) only stick on a clip the compiler doesn't own.

The decidable proxy: *if editing the YAML would beat editing the clip for every change you'd make, embed.*

*Where a clip is defined is what owns it,* and that is the whole design:

- **Authored in a clips file** → agent/YAML-owned. An out-of-band edit to the `.anim` (a hand-tweak, a
  `RepathClips` pass) makes it diverge from its stamp, so the next compile **refuses to clobber it** rather
  than silently overwriting; a forced recompile reverts to the YAML, which is the source. Promote the clip
  before a human needs those edits to persist.
- **A standalone `.anim` referenced by `ref:` and in no clips file** → human-owned. No compile ever writes it.
  The plain "hand-edit one pose" case is this from the start: make the `.anim`, ref it by path, no clips file
  needed.

**Promotion — handing a clip to a human — is deleting it from the clips file.** The controller's `ref:` path
keeps resolving and `CompileClips` (emit-only, never pruning) leaves the `.anim` untouched forever after. It
is clean *because the controller refs by path, not by a name that would go unresolved once the file stops
authoring it* — so no controller edit is needed. One-way, no sync-back; promote a YAML clip before a human
needs to own edits to it.

## behaviours (state-machine behaviours)

A `behaviours:` list (on a state or any machine's root) of **single-key maps** — `{ <kind>: { … } }`. All
seven VRC SMB kinds are implemented; an unknown kind or field is fail-loud by name. Enum-valued fields take
a **camelCase token**, never a raw number — the token→enum maps are `ControllerEmit`'s `*Tokens`
dictionaries, the single authority both compile and decompile read.

```yaml
behaviours:
  - driver:
      localOnly: false                                # optional; default false
      set:  { bit0: 1, Debounced: 0 }                 # ChangeType.Set  — name: value
      add:  { Work: -0.5 }                            # ChangeType.Add
      copy: { Work: OscFloat }                        # ChangeType.Copy — dest: source
      random: { Roll: { min: 0, max: 1, chance: 0.5 } }
```

`copy` takes either a source-name string, or a range map to remap while copying:

```yaml
copy: { VelXOut: { source: VelX, sourceMin: -1, sourceMax: 1, destMin: 0, destMax: 1 } }
```

Any of `sourceMin`/`sourceMax`/`destMin`/`destMax` present turns on `convertRange`. Unknown driver fields
fail loud (`set`/`add`/`copy`/`random`/`localOnly` only).

**Trap — a driver cannot durably set a clip-written param.** If a clip writes a parameter every frame (an
AAP), a driver `set`/`add` on that same param is overwritten each frame. The compiler surfaces this as an
advisory in the RunLog; heed it (`runtime.md`).

### the other six behaviour kinds

Each is a flat field map; the enum fields use the tokens shown (fail-loud on an unlisted token).

```yaml
- tracking: { head: tracking, leftHand: animation, eyes: noChange }   # channels: head/leftHand/rightHand/
                                                                       #   hip/leftFoot/rightFoot/leftFingers/
                                                                       #   rightFingers/eyes/mouth
                                                                       # state:  noChange|tracking|animation
- playableLayer: { layer: fx, goalWeight: 1, blendDuration: 0.25 }     # layer: action|fx|gesture|additive
- locomotion:    { disableLocomotion: true }
- poseSpace:     { enterPoseSpace: true, fixedDelay: true, delayTime: 0 }
- layerControl:  { playable: fx, layer: 3, goalWeight: 1, blendDuration: 0.1 }
- playAudio:                                                           # AudioSource by hierarchy path
    sourcePath: "Head/Voice"
    clips: [ "Assets/Sfx/beep.wav" ]                                   # asset paths; fail-loud if missing
    volume: [ 1, 1 ]                                                   # [min, max] range (pitch likewise)
    playbackOrder: roundabout                                          # random|uniqueRandom|roundabout|parameter
    volumeApply: alwaysApply                                           # *Apply: alwaysApply|applyIfStopped|neverApply
    playOnEnter: true
```

**`layerControl` vs `playableLayer` asymmetry (the SDK's, not ours):** `playableLayer.layer` is an **enum
token** (which playable), while `layerControl.layer` is an **int index** (which layer *within* the
`playable:` playable). `playAudio` carries the full `VRCAnimatorPlayAudio` surface — `sourcePath`,
`parameter`, `volume`/`pitch` ranges, the four `*Apply` settings, `clips`, `delaySeconds`, `loop`, and the
four `playOnEnter`/`stopOnEnter`/`playOnExit`/`stopOnExit` flags — see `ControllerEmit.PopulatePlayAudio`
for every field.

## Decompile output

`DecompileController` (the read door; contract in `animator.md`) reachability-walks a built controller and
serializes it back to this schema. What the read side layers on top of the authoring surface:

**The `_notes:` block.** Any **top-level** `_`-prefixed key is compile-ignored — Decompile's output
channel. It emits `_notes: { orphans: N, unresolved: [guids…], tolerances: [notes…] }`: the count of
unreachable sub-assets it dropped, the dangling motion GUIDs it recovered, and the import tolerances it
applied. Inert on re-compile.

**Layout.** Each arranged machine emits a `layout:` block ([above](#layout)); a machine whose nodes all sit
at the default grid/constants emits none, so decompiling a never-touched controller adds no coordinate noise.

**Import tolerances** (applied silently, listed in `_notes.tolerances`):
- **Mixed Write Defaults** → the layer's **modal** WD value becomes the layer policy and the minority states
  keep an explicit `writeDefaults:` override (tie → `true`); re-emit reproduces the same per-state mix.
- **`timeParameterActive` with an empty parameter** (every vendor Gesture ships this) → normalized to
  unbound motion time (no `motionTimeParam:`).

**Named refusals.** A construct the schema's shape can't round-trip makes Decompile return a bare `FAIL:`
naming each and write **no** yaml (it refuses to approximate). Two kinds. *Out of vocabulary:* synced
layers, a `Trigger` param, an IK-pass layer, a mirror/cycleOffset **parameter** binding, a sub-machine's
outgoing (on-Exit) transition, an unsupported SMB or motion type, an unknown driver `ChangeType` or
condition mode — and, as a backstop, **any** non-default top-level field the decoder does not model on a
state, transition, blend tree, or VRC behaviour: a completeness sweep refuses whatever it doesn't explicitly
consume, so a field the schema lacks (a state's constant `cycleOffset`, foot IK `iKOnFeet`, or `tag`; a
transition `offset`; a future SDK addition) fails loud instead of silently dropping. (The sweep covers those
four object families' scalar fields — including `m_Name`, guarded per type: captured where a schema field
models the name, cosmetic-and-ignored otherwise; array-element structs and the layer / state-machine families
stay guarded by the hand decoders.) *Not expressible in the canonical form:*
sibling states or sub-machines with identical names (→ duplicate keys), a direct state and sub-machine
sharing a name (→ an unaddressable sub-machine — a bare name resolves states first), or two sibling
**states** differing only in whitespace (a legibility hazard); a real state/sub-machine named `Exit`
addressed bare (collides
with the exit keyword); driver operations that interleave change-types or repeat a `(type, name)` (the
name-keyed set/add/copy/random buckets would reorder or collapse them); two **distinct** embedded clips
sharing a name (the name-keyed `clips:` map would collapse them); a condition parameter carrying whitespace
or a flow delimiter (it can't survive the `<param> <op> <value>` grammar); a blend-tree or transition `name`
containing a line break (the line-based YAML can't carry it).

**The fixpoint.** A controller you **own** (decompile) round-trips exactly — Decompile→Compile→Decompile
reaches a fixpoint. The single acknowledged lossy step is a genuinely-broken vendor motion ref
(`unresolved` → null slot → empty child).

## Not yet in the schema

A compile rejects these — listed so an "unknown field" error reads as deferred, not a syntax slip:

- **AvatarMask emission.** A layer's `mask:` references an existing `AvatarMask` by path; the compiler never
  **emits** one (external refs only).
- **CustomObjectSync-scale parameterized codegen** — its own future slice.
- **An NDMF build-time pass** — the compiler writes assets, not a build hook.
