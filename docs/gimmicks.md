# Gimmick design

Building avatar systems — state machines, constraints, contacts, network sync — that are complex
inside and simple to use. `runtime.md` is the physics this doc builds on; read it first. Compose
these named patterns freely, but the first instinct should be the *parsimonious* system for the
goal, not to stack every pattern that fits. To author an FX layer as a reviewed, recompilable artifact
instead of by hand in the Animator window, see `CompileController` (`animator.md`) — a YAML→controller write
substrate whose worked examples (`fixtures/animator-substrate/`) encode several of the patterns below.
Generalized, installable versions of these patterns live in the `vrc-patterns/` sibling repo (its
routing index is keyed on the pattern names in this doc).

## First principles

1. **Complexity stays local; only primitives cross the wire.** The best gimmicks look, to other
   clients, like ordinary synced params, physbones, and contacts — everything clever runs on each
   client independently. A system another player can interact with *as if it were a plain physbone*
   has the strongest compatibility and zero remote install burden.
2. **Spend synced bits like money.** Free transports first: contacts (sense locally, sync a bool —
   `runtime.md` on why contact outputs aren't "synced"), physbone grab/pose (native sync),
   built-in params (`IsLocal`, gestures, `ScaleFactor`, Voice) — `GestureLeft/RightWeight` is your
   only built-in **analog** hand input, but analog *only during Fist* (flat 1/0 for other gestures).
   Then unsynced animator params. Then the Parameter Compressor tier (slow toggles). Dedicated
   synced bits are for values that must be *exact, frequent, or late-synced*.
3. **One synced value can carry a whole state machine.** See self-syncing mode int, below.
4. **Every magic constant is either derived or empirical — label which.** Empirical constants
   (settle delays, thresholds, pulse timings) are load-bearing; changing them requires a test, not
   a hunch (`runtime.md`, the 90% rule).
5. **Fail visible.** A gimmick that can desync should prefer hiding/parking over showing a wrong
   state (e.g. fall back to an anchored pose when tracking is lost).

## Choosing a transport

| Need | Use | Cost / bound |
|---|---|---|
| On/off, mode, pose index | synced bool/int (or Compressor tier if slow-changing) | 1–8 bits |
| Continuous value, sloppy | physbone `_Stretch`/`_Angle` (native sync) | 0 bits; IK-delayed |
| Continuous value, exact | synced float (8-bit) or float→bool binary encode | 8 bits / n bits |
| Position of another player's part | contact latching + trilateration or crawler | 0 bits; their IK delay |
| Object world position, late-sync, exact | bit-multiplexed absolute sync (Custom-Object-Sync pattern, `references/`) | ~30 bits + seconds of latency |
| Object world position, approximate | physbone drop (grab is the sync) | 0 bits; per-client drift; **no late-sync** |
| Local-only input (hardware, apps) | OSC → unsynced params (+ encode if remotes need it) | 0 bits local |

**PhysBone drop/carry — what actually crosses the wire** (pick by whether the drop must persist for
a late joiner, and by what you can verify without two clients):

| Mechanism | Syncs | Late-syncs? | Emulator-verifiable |
|---|---|---|---|
| Live grab | grabber world point + `_IsGrabbed` | n/a (held) | local grab only |
| Released **pose** | bone rotation vs root | yes in-game | **no** — not reproduced |
| Constraint **sample-and-hold** (GrabProp) | nothing — each client re-derives off `_IsGrabbed` | no (re-run per client) | local behaviour only |
| Absolute (Custom-Object-Sync) | quantized position bits | yes | write/read split visible |

## State machine patterns

- **Self-syncing mode int.** One synced int is both output and input: each state stamps its own
  mode via a `localOnly` driver; remote copies route into the matching state by entry/AnyState
  conditions on the int. Local transitions can key off rich local signals (gestures + contacts);
  remotes need only the int. Reserve value bands with meaning (e.g. 10–19 = world-space family) so
  trees can band-select with float compares.
- **Entry-dispatch hub.** All states exit to Exit; the entry-transition ladder (ordered,
  first-match) is the priority encoder. Beats AnyState when priorities matter (ladder shadowing is
  a real, lintable bug class — `runtime.md`).
- **Remote settle dwell.** Remote copies start in a delay state (seconds) before acting, letting
  late-join parameter values land; local (`IsLocal`) skips it.
- **Debounce / arbitration layer.** Raw contact bools feed a small timer state machine (Empty +
  fixed-length Timer clips, exitTime as the dwell) that emits debounced flags and encodes priority
  between overlapping zones. Keep raw and debounced params distinct.
- **OSC handshake.** For external apps: on load, deliberately invert-then-restore a saved param so
  the app receives a change event; accept app→avatar tuning through ordinary params (bind one to a
  state's speed and even timer durations become externally configurable).
- **Force-release / override broadcast.** A `localOnly=0` driver or a synced bool imposes a state
  on all clients — the escape hatch for "recall my prop no matter who holds it." For physbones it
  takes both halves (`runtime.md`): disable the bone's GO *and* drive `_IsGrabbed` false.

## Blend tree patterns

The **vrc-patterns** library is the catalog of worked, gated examples for these idioms — browse its
*Find by pattern* table. A couple of foundational entries are named below as illustrative anchors; the
library, not this section, is the per-entry index.

- **DBT configuration states.** A state's motion is a Direct blend tree stacking single-purpose
  clips (constraint weights, GO actives, damping levels) all weighted by a constant-1 param: one
  state = one complete rig configuration, WD-ON safe, clips reusable across states. Per-layer cost
  is super-linear, but the optimizers flatten always-on Direct-tree layers on upload (below), so
  collapsing toggles into one DBT is a legibility win, not required for correctness — un-flattened it
  costs more layers but computes the same.
- **Layers are author-time legibility, not runtime structure.** An AAP written by animation this
  frame is invisible to every reader until next frame — whether the reader is another node in the
  same blend tree or a later layer; layer order buys no same-frame data flow. A multi-hop AAP
  feed-forward chain therefore lags exactly one frame per hop, whether it is authored as one tree or
  several ordered layers. Both dominant FX optimizers flatten always-on Direct-tree layers into one
  tree on upload (d4rk's FX-layer pass, on by default; VRCFury's layer→tree pass, managed layers by
  default / all layers under a `DirectTreeOptimizer`, base-FX-authored layers untouched); because
  layer structure never affected AAP timing, the flatten preserves timing and behavior (up to
  sub-tolerance float-summation order). Group layers
  and nesting for readability; design multi-hop AAP math to tolerate the per-hop frame lag either way.
- **AAP exponential smoother.** Two clips write a param at ±range; a 1D tree on `SmoothAmount`
  blends "input" vs "output(feedback)" subtrees → `out += (1−λ)(in − out)` per frame. Gate the
  *input* inside the tree (weight by the enable param) so disabling decays smoothly instead of
  snapping. λ is framerate-dependent — note it, or feed a frametime compensator. Worked + measured in
  `vrc-patterns/blendtree-math` (which also shows why the *linear* smoother limit-cycles and this one
  doesn't).
- **Two-stage AAP compute/consume.** Stage 1 trees select an abstract value (write an AAP); stage 2
  trees map that value plus live signals (voice, tracking state) onto actual bones/shapes.
  Decouples "what pose" from "how it animates."
- **Float→bool binary codec.** Encode: driver Copy with convertRange splits sign/magnitude, a
  binary-walk of states (Add −2^−(b+1) per accepted bit) fills bool params — n frames for n bits.
  Decode: mirrored Adds, or a cascade of nested 1D trees keyed on the bit bools. Used for OSC
  floats and absolute-position sync; budget the frame count (`runtime.md`: one transition/frame).
- **Priority gating via nested 1D trees.** Override chains (touched > gesture > idle) as nesting:
  each level's param fades the entire lower tree out. A razor threshold pair (e.g. 0.20/0.21)
  makes a float act as a switch.
- **Proximity-as-motion-time.** Bind a proximity receiver's float to a pose clip's motion time:
  analog expression intensity by distance, no tree at all.
- **DBT-math library.** The arithmetic idioms (add/subtract/multiply/divide, negate/remap, clamp,
  composed min/max), the smoothing family, and an owned `tangents: linear` frametime rig — each a
  worked, gated, per-primitive-measured example — live in `vrc-patterns/blendtree-math`. Reach here
  when a gimmick needs arithmetic on animator floats without a scripted behaviour.
- **Shader hue/color slider.** Drive a shader's own color property directly (lilToon vec4
  `_MainTexHSVG`, Poiyomi scalar `_MainHueShift`) — the per-channel writes composed in one WD-ON Direct
  tree so H/S/V coexist without the vec4 override/revert traps: `vrc-patterns/color-adjust`.

## Constraint patterns

- **Anchor multiplexer.** One position + one rotation constraint with N candidate sources at
  weight 0; states select exactly one. All "where is this attached" logic collapses into clip data.
- **World anchors.** Per-client drop = FreezeToWorld enabled at upload; cross-client absolute frame
  = never-instantiated-prefab source (see `runtime.md` for the guarantees and the culling caveat).
- **Trilateration cage** (static): 6 proximity receivers at ±axis offsets around a point; the six
  floats drive per-axis nudge clips as DBT weights → the cage centers on the latched sender.
  **Crawler servo** (dynamic): the constraint's sources are its own ± offset children, weights from
  proximity → walks toward a moving target indefinitely. Cage for "attach at", crawler for "chase".
- **Measurement chain.** Sensor transforms (physbone tip, tracked point) → per-axis
  single-`Affects` constraints → sender/receiver pairs = analog signed vector in any reference
  frame you can constrain a rig to.
- **Sample-and-hold drop** (world-drop, zero synced params). A grabbable physbone carries the prop
  live (native grab sync). On release, an animated **pulse of a constraint's `IsActive` 0→1→0**
  snaps a hold-anchor onto the just-dropped spot then freezes it there (a disabled constraint holds
  its object); a source-weight swap hands the visible prop from the grab bone to that anchor,
  re-grabbable in place. Every client runs the same release clip off the synced `_IsGrabbed`, so the
  drop reproduces per-client with no synced param (FreezeToWorld anchors give a shared world frame).
  To others it stays a plain physbone — max compatibility. (A hand-authored GrabProp is this end-to-end
  when its `allowPosing=0`, so the persistence is the constraint hold, not a physbone pose.)
- **Editor/runtime swap.** Alignment helpers and world-locks that would fight editing live on GOs
  toggled by build-time actions (VRCFury `ApplyDuringUpload` or equivalent): editor state for
  authoring, runtime state for the build. Name them for what they are.

## Contact patterns

- **Latching tracker.** Waiting state: filters open, generous identical-position capsules (so all
  probes latch the same target). On trigger: animate filters shut — locked to that sender.
  Acquisition-zone size ⇒ how many senders latch; too big = ghost between two people.
- **Zone touch.** Binary zones: Constant receivers + debounce layer. Graded zones: Proximity +
  threshold hysteresis (enter high, exit low). Self-touch as an animated `allowSelf` opt-in.
  Remote visibility: default localOnly + synced bool; latency-sensitive reactions keep
  remote-firing receivers as the fast path with a synced bool backstopping missed triggers.
- **Anchor handoff protocol.** Constant self-receivers on a prop detect *which* body anchor sender
  it overlaps; gesture + contact conditions move it between anchors (fist = take, open palm =
  place), with guard conditions arbitrating two hands.
- **Cross-base placement verifies in world space.** Bases differ in armature detail down to bone
  rolls, so contact/physbone placement copied between bases can't trust local bone-space offsets —
  verify against a canonical pose in world space (hand contacts sit just below the palms in T-pose
  regardless of how the arm/hand rolls are authored), and expect to re-tweak.

## Packaging and interface

- Ship a gimmick as one self-contained module attaching through explicit seams —
  `nondestructive.md` owns the module model and the MA-vs-VRCFury choice rules. Within those, the
  gimmick ruling is a **mixed seam**: MA `BoneProxy` for anchors whose placement must be visible
  while authoring (VRCFury never modifies the avatar in-editor — `ArmatureLink` alignment snaps
  only at build, so constraint offsets are blind against it), VRCFury for behavior
  (`FullController`/`Toggle`/`ApplyDuringUpload`). The menu front
  travels **inside** the module (it's part of the gimmick's function — the opposite of clothing,
  whose menus are avatar-level: `menus.md`).
- Keep OSC-facing param names in `globalParams`; let everything else take instance prefixes.
- **Variants by prefab composition + config params, never a controller fork** (a forked
  controller drifts from its mainline silently). A behavioral knob that isn't a menu control
  becomes a **non-synced param whose default lives in the params asset and which no menu drives**
  — envvar-style: one controller mainline reads it, each variant/install sets its default.
- In-game UX: prefer physical affordances (grab, touch, gesture-near-contact) over menu depth —
  but an affordance is the *primary* interface, never the **only** path: every affordance-reachable
  intent is also menu-reachable (deep in the menu is fine). It drives the same intent param, so it
  costs no extra synced bits, and it buys a rescue hatch for a mistuned affordance, a drive surface
  the emulator can reach without simulating contacts, and desktop parity (contact/PB affordances
  are VR-gated).
  The menu front splits three ways:
  - **Enable** — one synced **unsaved** bool wired as the state machine's master gate, so
    *off is the reset* (drops holds, stops tracking) and the gimmick never resurrects "on" at
    avatar load. When states are exclusive, fuse enable+mode+recall into **one int** with banded
    values (off=0, attach 1–9, world 11–19, transient 21+) instead of a bool plus a mode int.
  - **Options** — the tunable surface; `saved` per-param by preference-vs-transient.
  - **Failsafe** — an explicit control only when state persists beyond the avatar (world-placed
    props): a *recall* value distinct from *off*, so the user can summon without resetting.
  Sensing params (physbone `_IsGrabbed`/`_Stretch`, contact receivers, proximity) are never
  synced and never menu-exposed — only intent costs bits. And some gimmicks are correctly
  **frontless** (passive always-on FX, OSC-contract systems): "expose it in the menu" first asks
  whether a menu is the right front at all.
- In-editor UX: the prefab drops in at avatar root; anchors self-place (ArmatureLink/BoneProxy);
  anything the installer must hand-place is a defect.

## Verification

The bar for a gimmick claim: it **compiles, passes `Check*`, and behaves in the emulator** — lint the
assets, diff the built non-destructive stack, drive/observe in play mode, induce grab/pose, verify
mirror-detection. Beyond that — network timing, IK delay, culling, feel — name the specific behavior
that needs two clients in-game and hand it off. Mechanics and recipes: `verify.md`.
