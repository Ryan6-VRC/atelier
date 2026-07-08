# Animator schema — the `CompileController` authoring surface

The YAML language `CompileController` compiles into a `.controller` (`unity.md` owns the tool contract —
PASS/FAIL, atomicity, advisories). This document is the surface you author against: every key, the
accepted values, and the traps. The **enforcement mechanism is the parser + validator** — they refuse
unknown keys, bad values, and semantic defects **by name and line**, so a wrong guess is a legible error,
never silent corruption. Author against this, and iterate on the error text when unsure.

The three fixtures under `vrc-unity-tools/fixtures/animator-substrate/` (`debounce`, `smoother`, `codec`)
are the runnable companions — each compiles clean, lints PASS, and is emulator-verified. Snippets below are
drawn from them. The definitive grammar is `AnimatorSchemaYaml.cs` (parse) + `ControllerEmit.cs` (emit) +
`SchemaValidation.cs` (validate); when this doc and those disagree, the code wins — tell someone.

**Pair-1 scope.** The write half shipped first; the read half (`DecompileController`) and the constructs
it needs are not all authorable yet. The [Not yet in the schema](#not-yet-in-the-schema) section lists
exactly what a compile will reject, so you don't spend time guessing at syntax that isn't wired.

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

A layer is a **flat** state machine: named states, per-state transition ladders, and one `default` state.

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
    default: Idle            # must name a state in this layer; the machine enters here
```

State fields: `motion`, `speed`, `speedParam`, `motionTimeParam`, `mirror`, `writeDefaults`, `behaviours`,
`transitions`. `default:` must name a declared state. Transition ladders are **first-match, top to bottom**
per source state (list order is priority).

## transitions and conditions

```yaml
transitions:
  - { to: Active, when: [ Work greater 0.5 ], exitTime: 1.0, duration: 0 }
  - { to: Exit,   when: [ Done is true ] }          # `to: Exit` is the exit transition
```

Transition fields: `to` (a state name, or `Exit`), `when` (condition list, empty = unconditional), `exitTime`,
`duration`, `fixedDuration` (default **true**), `interruption`, `ordered` (default **true**),
`canTransitionToSelf`. Unset `duration`/`exitTime`/`interruption` inherit `defaults`.

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
instead. Each child is a motion **plus** its placement:

- **1D**: `threshold: <n>`
- **2D**: `x`/`posX` and `y`/`posY`
- **Direct**: `directWeight: <paramName>`
- any child: `timeScale` (negative is legal — reversed motion), `mirror`, `cycleOffset`.

Trees nest (a child with `tree:`) and refs chain across `.asset` files. **Trap:** a `ref: { guid }` must
resolve at compile time in pair 1 — an unresolvable GUID fails the compile even with `unresolved: true`
(that marker is for Decompile's lossless round-trip, not authoring against a missing asset).

## clips

Inline, float-curve clips keyed by name. Three forms:

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
- **Binding resolution.** A bare identifier naming a **declared parameter** binds as an animator-parameter
  curve — the AAP / param-write mechanism (`aap_min: { set: { Smoothed: 0.0 } }`). Anything else is a scene
  binding parsed as **`path/Component.property`**: split on the last `/`, then the **first** `.`. So
  `Prop/Renderer.enabled` → path `Prop`, `Renderer`, `enabled`. The split takes the first dot because a
  component type never contains one but a property can, so `Body/SkinnedMeshRenderer.blendShape.Smile` and
  `Hat/MeshRenderer.material._Color.r` resolve — blendshapes and material sub-properties are authorable
  inline.
- **Carrier.** A `seconds`-only clip (no `set`/`curves`) emits a flat curve on a reserved scratch Animator
  parameter (`_CompilerNull` — declared on the controller on first use, kept out of the emitted
  VRCExpressionParameters) purely to give the clip an honest length: it animates nothing and resolves against
  any avatar root, so the broken-binding lint stays clean. This is why a dwell timer is `{ seconds: N }` and
  never a hand-written empty clip. A clip with neither content nor `seconds` is refused, and `_CompilerNull`
  is reserved — a document may not declare it.

## behaviours (state-machine behaviours)

A `behaviours:` list (on a state or a layer's root machine) of **single-key maps** — `{ <kind>: { … } }`.
**Pair 1 implements `driver` only**; any other kind (`tracking`, `playableLayer`, `locomotion`,
`poseSpace`, `playAudio`, `layerControl`) compiles to a fail-loud error.

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

## Not yet in the schema

A compile will reject these — they are listed so you don't mistake an "unknown field" error for a syntax
mistake:

- **Sub-state machines, AnyState ladders, explicit Entry ladders.** A pair-1 layer is one flat machine; a
  state can only transition to another state or `Exit`, and `default:` is the sole entry. (The model has the
  fields; the parser doesn't bind them yet.)
- **Behaviour kinds other than `driver`** — they land with pair 2's fixtures.
- **`unresolved: true` guid refs against a genuinely missing asset** — pair-1 emit still requires the GUID
  to resolve.
