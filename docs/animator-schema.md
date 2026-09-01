# Animator schema — the `CompileController` authoring surface

The YAML language `CompileController` compiles into a `.controller` (`animator.md` owns the tool contract — PASS/FAIL, atomicity, advisories). This document is the surface you author against: every key, the accepted values, and the traps. The **enforcement mechanism is the parser + validator** — they refuse unknown keys, bad values, and semantic defects **by name and line**, so a wrong guess is a legible error, never silent corruption. Author against this, and iterate on the error text when unsure.

The three fixtures under `vrc-unity-tools/fixtures/animator-substrate/` (`debounce`, `smoother`, `codec`) are the runnable companions — each compiles clean, lints PASS, and is emulator-verified. Snippets below are drawn from them. The definitive grammar is `AnimatorSchemaYaml.cs` (parse) + `ControllerEmit.cs` (emit) + `SchemaValidation.cs` (validate), and on the read side `ControllerDecompile.cs` + `AnimatorSchemaEmit.cs` (serialize); when this doc and those disagree, the code wins — tell someone.

The surface is the compile↔decompile round-trip for the controller **graph**: the layers, states, transitions, motions, and behaviours you author both compile and survive a `DecompileController` read ([Decompile output](#decompile-output)). Authoring metadata a `.controller` does not store — `basis`, `role`, and per-param `aap`/`scratch`/`vrc` (they live in the descriptor / `VRCExpressionParameters`) — decompiles to canonical form, not its authored value (`avatar-root` / `fx`; params rebuild as name+type+ default only), and [`menu:`](#menu) does not decompile at all. The much-shrunken [Not yet in the schema](#not-yet-in-the-schema) section lists what a compile still rejects.

## YAML subset

A bounded block/flow YAML: 2-space block mappings and `- ` sequences, flow `{k: v}` / `[a, b]`, `#` comments, single/double quotes. Scalars infer: `true`/`false`/`on`/`off` → bool, `~` or empty → null, integer → int, decimal → float, else string (quote a string that would otherwise infer, e.g. `"on"`). Inference applies to **names in value position** too — a state named `On`/`Off` makes `to: On` parse as a boolean; prefer names that aren't YAML literals (`Idle`/`Disabled`) over quoting every reference.
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
menu: [ … ]                  # ordered list of expression-menu controls (optional)
_notes: anything             # any TOP-LEVEL key starting `_` is compile-ignored (Decompile's output channel)
```

`basis:` has no default — omit it and the compile refuses (an unframed clip path is a silent-misbinding landmine). `role: base-fx` requires at least three layers. A `_`-prefixed key is ignored **only at the document top level**; nested `_` keys hit "unknown field".

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
- **`aap: true`** documents that clips write this float as an animator-parameter curve (the AAP idiom). It is a legibility marker — emission binds *any* clip write of a declared parameter name as a param curve regardless of the flag (see [clips](#clips)). Set it anyway so intent reads.
- **`scratch: true`** = an internal/working param. It is still a real animator parameter; it is only excluded from the emitted `VRCExpressionParameters` legibility asset.
- **`vrc:`** drives that asset. `synced`/`saved` set the flags; `type` overrides the listed value-type when it differs from the animator type (a bool read as a float DBT weight). `osc: true` records "this name must survive the build" as intent — the flag itself takes no compile action beyond storing that intent. Independent of the flag: VRChat's OSC interface replaces spaces in a parameter name with underscores (a resulting collision can crash the client), and `# * , ? [ ] { }` are OSC pattern metacharacters — compile surfaces any declared non-scratch parameter whose name hits either hazard as a RunLog advisory.

**The params asset.** The compiler emits a `<controller>_Parameters.asset` listing every declared param **except** VRC built-ins and `scratch:` ones — *even unsynced ones* (`networkSynced=false`, zero sync-bit cost), so a human reading the merged FX sees them. A consumer references that asset by GUID (a VRCFury `FullController` names it in `prms:`), so this list **is** the avatar's expression-parameter contract and legibility is only why *unsynced* params appear on it. The two exclusions differ in consequence: a VRC built-in is supplied by VRChat and costs nothing to omit, while a dropped **custom** name is simply absent from that contract. Nothing to declare beyond `parameters:`; `vrc:` only tunes the entries.

## layers and states

A layer wraps a **root state machine**: named states, nested sub-machines, Entry/AnyState ladders, and one `default`. `states:`, `machines:`, `entry:`, `any:`, `behaviours:`, and `default:` are the **machine body** — the identical keys a layer's root and every sub-machine carry, so nesting recurses.

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
        motion: { clip: hold_on }                     # holds a FLOAT aap; see §clips on why not the output
        behaviours:
          - driver: { set: { Debounced: 1 } }         # the bool output is driver-written, and no clip binds it
        transitions:
          - { to: Idle, when: [ RawInput is false ] }
    default: Idle            # a direct state OR direct sub-machine of this machine; the machine enters here
                             #   (a default outside this machine is `defaultState:` — §Cross-machine addressing)
```

State fields: `motion`, `speed`, `speedParam`, `motionTimeParam`, `mirror`, `writeDefaults`, `behaviours`, `transitions`. Transition ladders are **first-match, top to bottom** per source state (list order is priority).

### sub-machines and Entry/AnyState ladders

```yaml
    machines:                                            # nested sub-machines (same machine body, recursively)
      Aim:
        states: { … }
        entry: [ { to: Ready, when: [ Loaded is true ] } ]     # Entry ladder — conditions only
        any:   [ { to: Reset, when: [ Abort is true ], canTransitionToSelf: false } ]
        default: Ready
```

`entry:` / `any:` are ordered, first-match transition lists. `canTransitionToSelf` is valid **only** on an `any:` rung (fail-loud on `entry:`). A `default:` naming a direct sub-machine enters it as an unconditional catch-all, ordered after any `entry:` rungs — the one place the key emits a rung rather than a state reference (§Cross-machine addressing has the mechanism split and the `defaultState:` form).

### layout

`layout:` records Unity graph node positions so a hand-arranged controller survives `DecompileController → edit → CompileController`. A machine-body key (root and every sub-machine may carry one), it is authored by hand only rarely — `DecompileController` writes it, and only for a machine whose nodes sit off their defaults, so a block's **presence signals a human arrangement; its absence, don't-care.**

```yaml
    layout:
      nodes: { Idle: [300, 0], Aim: [600, 0] }   # states + sub-machine nodes, by name; [x, y]
      entry: [50, 0]                             # the four special nodes
      any:   [50, 60]
      exit:  [50, 120]
      parent: [50, -60]                          # the "up" node; sub-machines only
```

- **`nodes` keys are `EscapeSegment`-encoded** (an addressing form — a `/` in a name becomes `\/`), **not** the raw literal a `states:` key carries. One node's name has two representations by design: literal as its own key, escaped as an address. In double-quoted YAML the backslash then doubles (`"A\\/B"`).
- **Absent → grid.** No block ⇒ every node lands on the compiler's default grid; a hand-authored document needs no coordinates.
- **Partial → listed win, rest grid.** List only the nodes you place. This is how you drop a new state into an existing arrangement: add its `nodes` entry near its siblings' coordinates; omit it to grid-fallback.
- **Unknown node → compile error.** A `nodes` key naming no state/sub-machine of its machine fails (a leftover after a rename/delete, or a typo).

Overlap is **unmanaged by design** — a placed or gridded node may land on another; a one-drag fix for the human, not the compiler's concern.

**Arranging for legibility.** A committed multi-state machine earns a hand-authored `layout:` — the grid erases the structure the states encode. Make the arrangement tell the machine's story: lifecycle descends from the default state below `entry`; same-stage alternatives fan left/right at one height; the more exceptional a path, the further outboard its lane.

The house grid (nodes are 200 wide): `entry` at `[50, 120]` with the default state at `[30, 180]` beneath it; rows every 70–100, one pitch per machine; same-row neighbors ≥210 apart, 240 the norm; columns on the ~120 half-grid, so a child can center between two parents. Specials pack tightly above `entry` in 40s, `exit` then `any` — full stack `any` `[50, 40]`, `exit` `[50, 80]` — and stay there while unused. A machine that actually exits through `exit` moves it one row below the content, still in the stack column, and the rest of the stack closes up (no hole where it was); a used `any` keeps its stack spot (its edges radiate legibly from there). An off-grid nudge is a deliberate tool for separating near-collinear transitions — read one as intent, place one only for that reason. Node overlap and transitions that visually merge are authoring defects to fix; plain crossings in a dense graph are not.

## transitions and conditions

```yaml
transitions:
  - { to: Active, when: [ Work greater 0.5 ], exitTime: 1.0, duration: 0 }
  - { to: Exit,   when: [ Done is true ] }          # `to: Exit` is the exit transition
```

Transition fields: `to` (a target address — below — or `Exit`), `when` (condition list, empty = unconditional), `exitTime`, `duration`, `fixedDuration` (default **true**), `interruption`, `ordered` (default **true**), `mute` / `solo` (bool, default-elided when false), `name` (a plain label; state/`any:` ladders only, refused on an `entry:` rung whose emit path can't carry it — and correspondingly **dropped** when decompiling a vendor rung that has one, reported as a per-rung Note rather than a refusal, since refusing would strand real packages over a field nothing reads at runtime; entry rungs carrying a cosmetic name are uncommon but not rare). `canTransitionToSelf` is an `any:`-ladder-only field. Unset `duration`/`exitTime`/`interruption` inherit `defaults`.

**Conditions are strings, right-anchored: the last two space-separated tokens are the op and the value; everything before is the parameter, verbatim** — interior spaces survive unquoted (`when: [ Hair ribbon is true ]`); separators are strict single spaces. A parameter carrying a flow delimiter (`,` `]` `}`) or other quote-triggering character emits as one quoted scalar. An op-lookalike parameter (one literally named `X is true`) is ambiguous read left-to-right — right-anchoring is the reader's only disambiguator. `value` is `true`/`false` or a number. The operator must match the parameter's declared type (validated):

| Param type | Valid ops | Notes |
|---|---|---|
| `bool`  | `is`, `isNot` | `is true` / `is false` — value folds into Unity's If/IfNot correctly |
| `int`   | `greater`, `less`, `equals`, `notEqual` | discrete compares |
| `float` | `greater`, `less` | Unity forbids float equality — no `equals`/`notEqual` |

**Trap — the never-firing transition is a compile error.** A state→state transition with **no condition and no exit time** can never fire; the graph lint fails the compile (`deadTransition`). An unconditional hop needs `exitTime` (and its source state a motion, or the 1 s fallback any non-positive state length takes — §clips — see the codec fixture). A motionless state's exit-time still advances; that is not an error.

### Cross-machine addressing

A `to:` target names a state or sub-machine by one of these disjoint forms (`ControllerEmit.ResolveName`):

- **bare `Name`** — resolves in the referencing machine's **own** scope (its direct states + direct sub-machines) only.
- **`Sub/State`** — a path from the **layer root**: each non-final segment a sub-machine, the last a state or sub-machine.
- **`/Name`** — absolute from the layer root. This is the only way to hit a **top-level** entity from inside a nested machine (a bare single segment would read as local).
- **bare `/`** — the layer-root state machine itself ("re-enter the layer at its default").

`default:` is always a bare **local** name (a direct state or sub-machine of its own machine), never a path. A default state living **outside** the machine is a different key — `defaultState:`, below.

### `defaultState:` — a default outside the machine

Unity's `m_DefaultState` points at a state anywhere **inside the machine's own sub-tree**, not just a direct child, so a machine can boot a state nested several machines down — what the animator window writes for "Set as Layer Default State" on a nested node. `defaultState:` carries that: a **root-relative address**, always naming a **state**.

Three things are refused rather than approximated: a path resolving to a sub-machine (the field cannot hold one), and a state **outside the carrying machine's sub-tree** — an ancestor's state or a sibling branch, which Unity accepts from a script and then silently discards, leaving the previous default in place. The address is root-relative in **every** spelling, a lone segment included; it does *not* take `to:`'s local reading, so a bare `defaultState: P` inside machine `M` names the layer root's `P` and is therefore refused as outside `M`. Write `M/P`.

```yaml
    entry:
      - { to: Preset 0, when: [ FacePreset equals 0 ] }
    defaultState: Preset 0/Neutral      # no rung matched ⇒ boot Neutral, nested inside Preset 0
```

It is a second key rather than a path form of `default:` because the two are **independent facts that co-exist**: a machine can carry a foreign default *and* a trailing unconditional entry rung, and one key cannot express both. Keeping them apart also preserves the addressing invariant `to:` relies on — an address selects *which node*, never what happens on arrival.

**Decompile spends the key only where a rebuild would otherwise lose the default.** Unity auto-fills an *empty* ancestor slot as states are added, landing on the **first state added anywhere in the sub-tree** — not, as it looks, the child machine's own default. So when the default already equals that first state, a recompile re-derives it for free and the bare `default:` form (or no key at all) is faithful; anything else needs `defaultState:` written out. A machine holding a direct state therefore always needs it, since that direct state claims the slot first.

**Name escaping.** A literal `/` or `\` inside a state/machine name is escaped `\/` / `\\` **in an addressing/path context**; a path splits on **unescaped** `/` only. A bare local reference and non-path scalars (a state's own name key) stay unescaped.

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

Tree `kind` (case-sensitive): `1d`, `simpleDirectional2d`, `freeformDirectional2d`, `freeformCartesian2d`, `direct`. A tree carries `param` (blend X) and `paramY` (2D only); `direct` uses per-child `directWeight` instead, and may set `normalized: <bool>` (the Direct "Normalized Blend Values" toggle — sum-to-1 vs raw additive; omitted ⇒ Unity's default). An optional `name:` labels the tree (any scalar except a line break). Omitted, the compiler generates one — `<State>_BlendTree` for a root tree, `<parent>_<childIndex>` nested — and Decompile emits `name:` only when the actual name differs from that formula. Each child is a motion **plus** its placement:

- **1D**: `threshold: <n>`
- **2D**: `x`/`posX` and `y`/`posY`
- **Direct**: `directWeight: <paramName>`
- any child: `timeScale` (negative is legal — reversed motion), `mirror`, `cycleOffset`.

**Trap — a `direct` tree's state duration is data, and every child curve plays against it.** A state whose motion is a direct tree with weight-sum ≥ 1 takes effective length Σ(child weight × child length) — live weights make it change per frame's readings — and each child clip's curves are sampled at normalizedTime × that child's own length, so a curve keyed in seconds plays stretched by the duration ratio (measured: a 0.1 s ease beside 0.5 s siblings at reading-driven weights ran ~11× slow, stretching MORE as the weights rose); below a weight-sum of 1 the duration normalizes instead. `set:` values are immune. `exitTime` reads the same data-dependent duration — exploitable as a weight-scaled dwell, and the reason a dwell child gets padded deliberately. Author timing intent inside such a state only three ways: every child tiny and near-equal (the stretch collapses toward real frames), a deliberate exitTime dwell built on the formula, or move the timed curve to a plain single-clip state.

Trees nest (a child with `tree:`) and refs chain across `.asset` files. A **bare** `ref: { guid }` that doesn't resolve fails the compile. Marking it `ref: { guid: …, unresolved: true }` instead **tolerates** a genuinely-missing asset: the motion slot emits null (a clean-empty state) and the compile writes a RunLog advisory naming the owning state + the verbatim GUID. This is the round-trip's one lossy step (a dangling vendor ref decompiles back with the same marker) — not a license to author against an asset you could fix.

A **path** `ref:` to a project `.anim` may resolve to a hand-owned clip or to one a clips file authored via `CompileClips` — the controller cannot tell them apart, which is exactly what lets a clip be *promoted* from YAML to human ownership with no controller edit (§clips; compile the clips file first — `animator.md`).

## clips

Float-curve clips keyed by name — embedded inline under a controller (below), or emitted as external `.anim` assets from a clips file (§external clips). Three forms:

```yaml
clips:
  timer:   { seconds: 0.2 }                           # duration-only → an inert carrier (below)
  hold_on: { set: { Level: 1.0 } }                    # constant write, held for the clip length
  toggle:  { set: { "Prop/Renderer.enabled": 1 } }    # scene binding (below)
  fade:                                               # keyframed
    length: 0.5
    curves: { "Head/Light.m_Intensity": [ [0, 0], [0.5, 3] ] }  # [time, value] pairs; m_-prefixed — below
```

- `seconds:` (alias `length:`) declares the length. A `set`/`curves` clip with no `seconds` derives its length from the keys, flooring at one frame (1/60 s) — the floor is why a single key at `time: 0` still emits a one-frame clip rather than a zero-length one.
- **A non-positive state length becomes an effective 1 s, so `exitTime` reads as literal seconds** (measured). This is one animator fallback with two doors — the empty state, and any clip whose length is 0 — not two separate defaults. It is also why the one-frame floor above is load-bearing rather than cosmetic: an unfloored zero-length clip would silently dwell `exitTime` **seconds** instead of `exitTime × 1/60`, a 60× error, and would survive the `.anim` round-trip as the floored one-frame form (`animator.md`), changing timing with both directions reporting OK.
- **Curve tangents.** A `curves:` value is normally the bare list `[[t,v],…]` — **flat** tangents, the default: the segment eases between keys, so a two-key "ramp" bows instead of running straight. For a straight proportional ramp give the map form `{ tangents: linear, keys: [[t,v],…] }`; for a hard step (a `0→1→0` pulse) give `{ tangents: stepped, keys: [[t,v],…] }` — the value holds each key until the next, then snaps. `tangents:` takes `flat`, `linear`, or `stepped`, per curve. Round-trip keeps flat curves in the bare-list form (byte-identical to documents predating this option) and emits the map form where a curve is linear or stepped — see `vrc-patterns/blendtree-math` for a worked frame-time rig. `auto`/`free` can't be **authored** — the parser rejects any token but `flat`/`linear`/ `stepped` (Unity recomputes auto/clamped-auto; free carries explicit tangent values the `[t,v]` form can't express). On **decompile**, an unweighted all-zero-tangent curve normalizes to flat (it interpolates identically), while a curve with non-zero, mixed, or **weighted** tangents is refused as a fork to a hand-owned `.anim`, not flattened.
- **Binding resolution.** A bare identifier naming a **declared parameter** binds as an animator-parameter curve — the AAP / param-write mechanism (`aap_min: { set: { Smoothed: 0.0 } }`). **The parameter check runs first and wins outright**, so a declared name containing `/` (`Lantern/GlowSmooth`) is a parameter curve, never the scene binding its spelling suggests — no need to rename around the slash. The one name shape to avoid is a declared parameter that *also* parses as a valid scene binding (a `/` **and** a `.` resolving to an allowlisted component, e.g. a parameter literally named `Prop/MeshRenderer.m_Enabled`): it shadows that binding, and a controller carrying both is a decompile refusal, since the two produce the same key. **A parameter curve writes only `float` parameters**: on a `bool` or `int` the curve is emitted, is inert, and still *binds* the parameter — which hands it to the animation system and locks out every other writer (`runtime.md` §Animator has the ownership rule). `RuleNonFloatParamCurve` refuses it, so this is a compile failure rather than a silent dead clip; drive a bool or int output from a parameter driver and let no clip animate it. Anything else is a scene binding parsed as **`path/Component.property`**: split on the last `/`, then the **first** `.`. So `Prop/Renderer.enabled` → path `Prop`, `Renderer`, `enabled`. The split takes the first dot because a component type never contains one but a property can, so `Body/SkinnedMeshRenderer.blendShape.Smile` and `Hat/MeshRenderer.material._Color.r` resolve — blendshapes and material sub-properties are authorable inline. `Component` resolves by simple name in a fixed **namespace allowlist** — `UnityEngine`, `UnityEngine.Animations`, `VRC.SDK3.Dynamics.{Constraint,Contact,PhysBone}.Components` — and must be a `Component` (`GameObject` is special-cased). So VRC constraints (`Cage/VRCPositionConstraint.GlobalWeight`, `….Sources.source0.Weight`), contacts (`Recv/VRCContactReceiver.allowOthers`), and native constraints (`Node/PositionConstraint.m_Weight`) bind inline. **`property` is the *serialized* field name, not the C# scripting name** — `Light.m_Intensity`, not `Light.intensity`. Built-in Unity components mostly carry the `m_` prefix; VRC components read naturally only because their public fields *are* their serialized names, which is why `PositionConstraint.m_Weight` above is spelled unlike its neighbours. A wrong property name compiles clean and animates nothing, so settle a new built-in binding with `AnimationUtility.GetEditorCurveValueType` (null ⇒ it resolves to nothing) rather than against the component's API. A **path-less `Animator.<property>`** binding is the empty-path degenerate: component `Animator` (resolved in `UnityEngine`), property a **humanoid muscle** (`Animator.RightHand.Index.1 Stretched`) — a rig-agnostic muscle curve for a Gesture/Action-playable pose (grip, expression), since humanoid muscles retarget across any rig. Decompile emits this form for a path-`""` `Animator` binding whose property is not a declared parameter, so it round-trips. Anything else — UI, TMP, arbitrary scripts, a non-Component like `Time` — is refused fail-loud, as is a simple name matching in more than one allowlisted namespace. A refusal here is a fork, not a dead end: author the clip by hand as a human-owned `.anim` (§external clips), and see `animator.md` for when a recurring refusal should widen this allowlist instead. Decompile enforces the same vocabulary through the emit resolver (a binding whose `type.Name` doesn't resolve back to the same type is a named refusal), so the two directions can't drift.
- **Transform vector properties animate as a unit.** The animator evaluates `m_LocalPosition` / `m_LocalScale` / `localEulerAngles` as whole vectors: a state whose motion binds only some components drives the unbound ones to **0**, not leave-at-rest (measured in-game — a y-only slide clip collapsed every box on a display rail to x=0). Write all three components in every such clip, rest values baked in. Coverage counts across the state's whole blend tree (the union of its clips' bindings), which is how a summed DBT readout legitimately splits axes across leaves (`vrc-patterns/box-tracker`).
- **PhysBone bindings compile but barely animate.** VRChat captures PhysBone simulation properties (Spring/Pull/Stiffness, …) at avatar initialization: animating them has no live effect, and the animate-then-toggle-`m_Enabled` workaround is explicitly unsupported and may break without notice (creators.vrchat.com/common-components/physbones §Changing PhysBone Properties). The dependable animated surface is `m_Enabled` itself.
- **Carrier.** A `seconds`-only clip (no `set`/`curves`) emits a flat curve on a reserved scratch Animator parameter (`_CompilerNull` — declared on the controller on first use, kept out of the emitted VRCExpressionParameters) purely to give the clip an honest length: it animates nothing and resolves against any avatar root, so the broken-binding lint stays clean. This is why a dwell timer is `{ seconds: N }` and never a hand-written empty clip. A clip with neither content nor `seconds` is refused, and `_CompilerNull` is reserved — a document may not declare it.

### external clips and ownership

The same `clips:` grammar lives in two places. **Inline** under a controller's own `clips:`, a clip embeds as a hidden sub-asset (the default, unchanged). **In a clips file** — a schema document with a top-level `clips:` (plus `schema:`, `basis:`, and any `parameters:` its AAP bindings need) and **no `layers:`** — `CompileClips` (`animator.md`) emits each clip as a standalone, *visible* `.anim` a human can open and edit. A controller reaches such a clip through the ordinary `motion: { ref: "<outDir>/<clip>.anim" }` (§motions) — no new directive — so one controller mixes embedded and external clips freely.

**Choosing the mode.** The pattern library and any self-contained, regenerable artifact embed *everything* — the clip is a projection of its YAML, and the human owns the YAML, not the clip. In human-agent real-avatar work, route per clip on one question: **is the `.anim` or the YAML the better surface to see, change, and repath this clip's content?**

- **Embed** — *generated plumbing*: a blend-tree leaf, a constant endpoint, an AAP / smoother / codec member, or any near-identical grid the compiler emits from a few YAML numbers. Its content regenerates trivially and a rename or retune is faster in the YAML source; external files would only litter the folder. Every all-animator-parameter (AAP) clip is this — and so are the ~8 lilToon endpoints of a `color-adjust` / `hsv` rig, *even though they target a material*: a scene/material binding is necessary for external but not sufficient.
- **Externalize** — a *hand-authored artifact* a human sculpts and enters as a unit: a blendshape or transform pose, an expression, a toggle's visible target — especially multi-key / multi-binding, or reused across states. The `.anim` and the Animation window are genuinely the better authoring surface, and out-of-band repaths (`RepathClips`) only stick on a clip the compiler doesn't own.

The decidable proxy: *if editing the YAML would beat editing the clip for every change you'd make, embed.*

*Where a clip is defined is what owns it,* and that is the whole design:

- **Authored in a clips file** → agent/YAML-owned. An out-of-band edit to the `.anim` (a hand-tweak, a `RepathClips` pass) makes it diverge from its stamp, so the next compile **refuses to clobber it** rather than silently overwriting; a forced recompile reverts to the YAML, which is the source. Promote the clip before a human needs those edits to persist.
- **A standalone `.anim` referenced by `ref:` and in no clips file** → human-owned. No compile ever writes it. The plain "hand-edit one pose" case is this from the start: make the `.anim`, ref it by path, no clips file needed.

**Promotion — handing a clip to a human — is deleting it from the clips file** (the emit-only mechanism that makes this a no-op: `animator.md`). It is clean *because the controller refs by path, not by a name that would go unresolved once the file stops authoring it* — so no controller edit is needed. One-way, no sync-back; promote a YAML clip before a human needs to own edits to it.

## behaviours (state-machine behaviours)

A `behaviours:` list (on a state or any machine's root) of **single-key maps** — `{ <kind>: { … } }`. All seven VRC SMB kinds are implemented; an unknown kind or field is fail-loud by name. Enum-valued fields take a **camelCase token**, never a raw number — the token→enum maps are `ControllerEmit`'s `*Tokens` dictionaries, the single authority both compile and decompile read.

```yaml
behaviours:
  - driver:
      localOnly: false                                # optional; default false
      set:  { bit0: 1, Debounced: 0 }                 # ChangeType.Set  — name: value
      add:  { Work: -0.5 }                            # ChangeType.Add
      copy: { Work: OscFloat }                        # ChangeType.Copy — dest: source
      random: { Roll: { min: 0, max: 7, preventRepeats: true } }
```

`random`'s four fields are the SDK's, and the SDK draws them by DESTINATION type: `min`/`max` plus `preventRepeats` for an Int, `chance` alone for a Bool or Trigger, `min`/`max` for a Float. The schema accepts all four on any entry rather than resolving the destination's type here, so an entry the SDK would ignore is yours to get right. `preventRepeats` defaults false and is emitted only when true — the example above is an Int roll, the one shape that uses all three of its fields.

`copy` takes either a source-name string, or a range map to remap while copying:

```yaml
copy: { VelXOut: { source: VelX, sourceMin: -1, sourceMax: 1, destMin: 0, destMax: 1 } }
```

Any of `sourceMin`/`sourceMax`/`destMin`/`destMax` present turns on `convertRange`. Unknown driver fields fail loud (`set`/`add`/`copy`/`random`/`localOnly` only).

**Refused — a driver may not touch a parameter a clip binds, in either direction.** The animation system owns a bound parameter; `runtime.md` §Animator holds the mechanism and its measured scope. A driver write (`set`/`add`/`copy`/`random`) to one reaches no animator reader; a `copy` whose **source** is one reads the declared default, not what the clip is producing. `driverOnAnimatedParam` fails the compile on both. Give the driver a parameter no clip in this controller animates — including when the consumer is outside the animator (an OSC-out signal, a `saved:` value), where the write is misdirected rather than pointless. To read a clip-computed value *inside* the animator, use a blend tree or a transition condition.

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

**`layerControl` vs `playableLayer` asymmetry (the SDK's, not ours):** `playableLayer.layer` is an **enum token** (which playable), while `layerControl.layer` is an **int index** (which layer *within* the `playable:` playable). `playAudio` carries the full `VRCAnimatorPlayAudio` surface — see `ControllerEmit.PopulatePlayAudio` for every field.

## menu

An optional ordered list of expression-menu controls, emitted as `<controller>_Menu.asset` beside the params asset. A module's menu is thus regenerable from its YAML rather than hand-maintained (`vrc-patterns/CONVENTIONS.md` §The README owns when an entry ships one).

```yaml
menu:
  - button: Tag                      # the KIND is the key, the control NAME the value
    param: SelectiveAnimation/Tag
  - toggle: Wear
    param: Outfit/Worn
    value: 1                         # default 1; the value written while the control is active
  - radial: Saturation
    param: Color/Sat                 # rides subParameters — a radial writes nothing on press
    icon: assets/Sat.png             # relative to THIS document; any kind may carry one
  - submenu: Colors
    controls: [ … ]                  # same grammar, recursively
```

Four kinds: `button`, `toggle`, `submenu`, `radial`. Fields are `param`, `value` (not on a radial — its parameter *is* the position, so a `value:` would have nowhere to go and is refused), `icon`, and `controls` (submenu only, and required — an empty submenu is a dead end). A bare `submenu` needs no `param`; every other kind without one is refused as a control that would do nothing.

**An `icon` is a path in either of two spellings.** A value starting `Assets/` or `Packages/` is a project path; anything else resolves against the *document's own directory* — the portable form, and the one a library entry wants, since the same entry compiles both from its installed package path and from an arbitrary filesystem `--root`. Backslashes and `..` segments are normalized in both; an absolute path is refused outright, as it would resolve only on the machine that wrote it. Resolution stays in **asset-path space** whenever the document is in the AssetDatabase, because a mounted package's `Packages/<name>/…` names no folder on disk: doing the arithmetic on the filesystem sends it to wherever the bytes actually live, outside the project, and every icon in a mounted package then resolves to nothing.

**Whether a bad icon is fatal depends on the document, not on the icon.** The compiler adjudicates an icon only when it can — when the *document* is in the AssetDatabase. There, resolution is authoritative and anything unresolved fails the compile: there is no marker distinguishing an intended-dangling icon from a typo, and a silently icon-less control is exactly what an author would not notice. When the document is **outside** the AssetDatabase the compiler has nothing to ask and cannot tell a correct path from a wrong one, so it never fails — it emits a null icon and records a compile advisory, whatever the spelling. That is the vrc-patterns gate, which compiles every entry from a filesystem `--root` into a host that does not load the entry's package; failing there would make the field unauthorable by the library it exists for. The in-project compile that regenerates `built/` is where a typo is caught, and every committed icon passes through it.

Two consequences worth knowing before relying on the field. **The gate cannot see an icon** — neither side of its menu comparison can resolve one, so an entry whose `built/` and yaml disagree about an icon still passes. And an out-of-project compile cannot check that an icon is even an image; that too waits for the in-project compile. Icons survive composition onto a host avatar (`menus.md`).

**A control's `param` is checked against the *wire* type** — `vrc.type ?? type`, the type the params asset lists and VRChat reads the control against, not the animator type. A `radial` therefore needs a float *on the wire*: a `{ type: float, vrc: { type: bool } }` param is a bool to the menu, and a knob on it would carry only 0 and 1. The param must also survive into the params asset, so a `scratch:` one is refused (validation) and a VRC built-in is refused (emit) — both are excluded from that asset, leaving a control that is inert on the avatar with nothing in the built menu to show it.

**A page holds `VRCExpressionsMenu.MAX_CONTROLS` controls, and going over is a compile error, not an advisory.** The SDK's own menu inspector truncates `controls` to that cap the moment a human opens the asset, so an over-long menu silently *loses* controls rather than degrading — split it into sub-menus. `MenuLimits.MaxControlsPerMenu` mirrors the constant for the System.*-only validator; a real emit asserts the two agree and fails loud if the SDK ever moves it. The cap is **per page**, so a full page plus a sub-menu holding another full page is legal.

**The whole tree is one asset.** Sub-menu pages emit as sub-assets of the root file, so a consumer's `menus:` row references one GUID and no page can be orphaned into a loose asset nobody points at. A recompile churns the pages wholesale — a renamed or deleted sub-menu is destroyed, not left inside the file. The root object is overwritten in place, so its GUID survives a recompile exactly as the controller's and the params asset's do; dropping the `menu:` block deletes the asset.

**Emit-only, deliberately — there is no `menu:` on the read side.** A `.controller` stores no menu, so a menu could never ride the controller round-trip; `DecompileController` takes a controller and nothing else and emits no `menu:` block, the same asymmetry `parameters:` already has with its `VRCExpressionParameters` (above). This is a decision, not a gap: transcribing a menu asset back to YAML is rare and mechanical. The consequence is that decompile-equality cannot see menus at all, which is why the vrc-patterns gate needs a **separate menu pass** — and, for the same reason, a separate params pass (`vrc-patterns/CONVENTIONS.md` §The gate owns both).

**The asymmetry has one edge sharper than the params asset's.** Losing `vrc:` metadata on a decompile *degrades* a rebuilt params asset; losing `menu:` **deletes a file other assets reference by GUID**. `Decompile → edit → Compile` back into the folder the controller came from removes `<controller>_Menu.asset`, and a consumer's FullController `menus:` row then dangles — and the gate stays green, because both sides agree the menu is absent. The compile logs a warning whenever it deletes a menu for a document declaring none; that warning is the whole defence. Round-tripping an entry that ships a menu means re-adding the block before recompiling.

## Decompile output

`DecompileController` (the read door; contract in `animator.md`) reachability-walks a built controller and serializes it back to this schema. What the read side layers on top of the authoring surface:

**The `_notes:` block.** Any **top-level** `_`-prefixed key is compile-ignored — Decompile's output channel. It emits `_notes: { orphans: N, unresolved: [guids…], tolerances: [notes…] }`: the count of unreachable sub-assets it dropped, the dangling motion GUIDs it recovered, and the import tolerances it applied. Inert on re-compile.

**Layout.** Each arranged machine emits a `layout:` block ([above](#layout)); a machine whose nodes all sit at the default grid/constants emits none, so decompiling a never-touched controller adds no coordinate noise.

**Import tolerances** (applied silently, listed in `_notes.tolerances`):
- **Mixed Write Defaults** → the layer's **modal** WD value becomes the layer policy and the minority states keep an explicit `writeDefaults:` override (tie → `true`); re-emit reproduces the same per-state mix.
- **`timeParameterActive` with an empty parameter** (a stray flag on some vendor Gesture states — not the norm; most states that scrub motion time name a real parameter) → normalized to unbound motion time (no `motionTimeParam:`).

**Named refusals.** A construct the schema's shape can't round-trip makes Decompile return a bare `FAIL:` naming each and write **no** yaml — it refuses to approximate; iterate on the message. Two kinds. *Out of vocabulary:* anything the decoder doesn't model (synced layers, a `Trigger` param, an IK-pass layer, an unsupported SMB or motion type, a clip binding on a component type outside the §clips allowlist, an embedded clip's object-reference (PPtr) curve — a material swap has no schema form (a standalone `.anim` swap stays an untouched `ref:`), an unknown driver `ChangeType`…), enforced not by a blocklist but by a **completeness sweep** — it refuses **any** non-default field it doesn't explicitly consume on a state, transition, blend tree, or VRC behaviour, so an unmodeled field (a state's `cycleOffset`/`iKOnFeet`/`tag`, a transition `offset`, a future SDK addition) fails loud instead of silently dropping. *Not expressible in the canonical form:* sibling states or sub-machines with identical names, a direct state and sub-machine sharing a name, or two siblings differing only in whitespace (the name-keyed maps collide or reorder); a real node named `Exit` addressed bare (collides with the exit keyword); driver operations that interleave change-types or repeat a `(type, name)`; two distinct embedded clips sharing a name; **two clip bindings that reconstruct to the same `set:`/`curves:` key** (a declared parameter whose name also reads as `path/Component.property` shadows the scene binding of that name — the map would keep one curve and drop the other); **a default state the layer root cannot address** (a `m_DefaultState` outside this layer, or a broken reference to a deleted state — either would decode to no key and rebuild booting whichever state was added first); a condition parameter whose whitespace can't survive the single-space grammar; any emitted string containing a line break.

**The fixpoint.** A controller you **own** (decompile) round-trips exactly — DecompileController→CompileController→DecompileController reaches a fixpoint. The single acknowledged lossy step is a genuinely-broken vendor motion ref (`unresolved` → null slot → empty child).

## Not yet in the schema

A compile rejects these — listed so an "unknown field" error reads as deferred, not a syntax slip:

- **AvatarMask emission.** A layer's `mask:` references an existing `AvatarMask` by path; the compiler never **emits** one (external refs only). *Referencing* one is fully covered — a project-local `.mask` round-trips GUID-identical through the path ref, exactly as an SDK/`Packages/` one does — so what is deferred is authoring a mask from the document, not masked layers.
- **Menu puppets, and the two control fields beside `icon`.** [`menu:`](#menu) covers button/toggle/submenu/radial; `TwoAxisPuppet`/`FourAxisPuppet` are out of vocabulary (`menus.md`: effectively unused here), and with them `labels`, which only a puppet renders. `style` is out for a different reason: the SDK's own control inspector never binds it, so authoring it would author a field nothing reads. A rig needing a puppet authors its menu asset by hand and keeps it in `assets/`, out of `built/` — a recompile overwrites `built/` wholesale, so a hand-authored menu left there is destroyed rather than merged.
- **CustomObjectSync-scale parameterized codegen** — its own future slice.
- **An NDMF build-time pass** — the compiler writes assets, not a build hook.

Three constructs that used to sit here have moved, and it is worth knowing *where* each landed, because two are now authorable and the third never will be. A destination-state playback offset is the schema field **`offset:`** on a state or AnyState transition (refused on entry ladders and `onExit` lists, which are `AnimatorTransition`-backed and hold no timing). A sub-machine's outgoing edges are **`onExit:`**, authored inside the machine's own body under `machines:` — never on a layer root, which has no parent to exit to. A **driver repeating an operation on one parameter** is a *named decompile refusal*, not a widen: the schema holds one entry per parameter, so a recompile could not reproduce it as authored, and a repeat is usually a mistyped parameter name — check it against sibling states rather than looking for the field.
