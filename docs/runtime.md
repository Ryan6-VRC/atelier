# VRChat runtime ground truth

How the VRChat client actually runs an avatar: the animator, network, contact, physbone, and
constraint behaviors that gimmick design lives or dies on. Established empirically — treat it as
physics. Confidence markers: unmarked = verified or confirmed by repeated use; **(~)** = believed
true, not pinned; anything here can be re-pinned via an emulator or two-client test.
The companion design doc is `gimmicks.md`.

**The 90% rule.** Empirically-tuned constants in working systems (delays, pulses, thresholds) are
load-bearing — preserve them verbatim; change one only with a test (now an emulator run, `verify.md`),
not a hunch.

## Animator evaluation

- A layer takes **at most one transition per frame**. N-state chains (bit walks, dispatch hops)
  cost N frames minimum; budget accordingly.
- **Layer weight 0 still evaluates the state machine** — transitions fire and StateMachineBehaviours
  (parameter drivers) run; only the motion output is muted. Driver-only layers at weight 0 are a
  standard idiom.
- **Preserve the first three layers, and their order, in the avatar's own base FX.** Some VRChat
  worlds toggle base-FX layers 0/1/2 to override facial expressions, so those slots are load-bearing
  by *index* — an empty one is often reserved, **not** dead, and dropping or reordering any of the
  first three can break the override. Base-FX only: a merged animator (MA / VRCFury) can't know its
  landed index (it appends lower in the stack), so the convention never constrains it.
- Entry transitions evaluate **in list order, first match wins**. An entry ladder is a priority
  encoder — and a mis-ordered one silently shadows later entries (a real bug class; lintable).
- A state's `motion time` can be bound to a parameter: an analog input scrubs a pose clip's playhead
  with no blend tree. A state's `speed` can be parameter-bound too —
  including from outside over OSC, making timer durations externally tunable.
- Bool parameters can be compared with Greater/Less as floats (0/1); thresholds like >0.008 /
  <0.992 give edge-detection with hysteresis on nominally boolean signals.
- **Parameter type is per-reader, not global.** Unity animators are float-backed and VRChat casts on
  read, so a param's *synced expression* type is independent of how each animator reads it — declare a
  param that only needs discrete values as a 1-bit **bool** (or int) even though the FX animator
  consumes it as a **float** DBT weight/radial: the standard way to fold toggles into one Direct blend
  tree without paying 8 synced bits each. The merged-controller case (int in one, float in another →
  one VRC param) is the same mechanism; ints band-select via float Greater/Less compares
  (e.g. `10 ≤ Mode ≤ 19`).
- Write Defaults: keep it consistent per layer; direct-blend-tree layers want **WD ON** (the one
  sanctioned mix). WD OFF states only write properties their own clip touches — full-face override
  clips must therefore key *every* shape they need to own.
- Transition `interruption` defaults to None; `canTransitionToSelf` on AnyState transitions re-fires
  the state every frame the condition holds — usually you want it off.
- An **AAP** (clip-driven float) reverts to its default whenever no clip animates it, and is walled off
  from Parameter Drivers both ways — a driver can neither set an AAP nor copy *from* one (same isolation
  as built-in params). It persists across frames only via a dedicated save layer, and crosses the wire
  only through an encoded proxy (`gimmicks.md`).

## Parameters and network sync

- Synced expression parameters: bool = 1 bit, int/float = 8 bits, 256-bit budget; synced ints are
  unsigned 0–255. **A float is native 32-bit locally; only its synced copy is 8-bit fixed-point
  [-1,1]** (255 steps ≈ 1/127; −1/0/+1 exact) — drivers/OSC can hold out-of-range or fine-precision
  values locally that remotes never see, so anything remote-visible must survive the quantized
  [-1,1]. PC↔mobile params match by **list position + type, not name** (why the VRCFury mobile
  build aligns param order, below). Sync is batched on a ~0.1 s tick (~10 Hz). All params changed
  within a tick replicate together as one **coherent snapshot** — a step index and its data land
  atomically, so a multiplexing protocol needn't guard against a torn step+data read. The constraint
  is rate and loss, not coherence: a param changed twice inside one tick loses the intermediate, and a
  multi-tick protocol that drops a snapshot pays a full cycle to re-send — so hold each step stable
  across several ticks and latch a coherent set.
- **The synced-param count is only knowable post-build.** The pre-build `VRCExpressionParameters`
  asset under-counts — Modular Avatar params, VRCFury synced toggles, and merged prefabs all inject
  synced params at build. To read the real count, enter play mode and check the
  populated descriptor; for the compressor's effect on it, read the `VRCFuryDebugInfo` "Parameter
  Compressor" component (§VRCFury build-time reshaping). Neither the pre-build asset nor the baked
  `networkSynced` flag is authoritative on its own.
- Synced params **late-sync**: late joiners receive current values. Everything else (animator-local
  params, contact/physbone outputs) is regenerated per-client.
- **IK body motion is smoothed/delayed (~0.5 s); physbone grab/pose sync is not.** Physbone events
  run ahead of the visible remote body. Consequences: remote drop positions need ~1 s of stillness
  to agree across clients; OSC apps compensating for this need activation/release delays.
- Parameter drivers: `localOnly=1` runs only on the wearer's client; `localOnly=0` also runs on
  every remote copy's animator — a driver can force a network-visible effect (e.g. clearing a
  physbone grab param on all clients).
- **Mirror/camera clones replay the wearer's parameter values but do not execute
  StateMachineBehaviours, and traverse the state machine fresh from Entry.** This asymmetry is
  exploitable as a mirror-clone detector (drive a flag on the real avatar; the clone spawns with it
  pre-set and routes differently), yielding local-real / remote / mirror-clone discrimination. The
  emulator reproduces it — the MirrorReflection clone's driver-set params stay at their un-driven
  defaults while the local avatar shows the driven values — so mirror-detection is
  **emulator-verifiable** (`verify.md`).
- **A culled avatar stops running its animator.** VRChat culls what you can't see — off-camera view
  culling, distance-hide, max-avatars-shown, manual/perf hide — and a culled animator simply doesn't
  run. So make animators **deterministic**: resolve to the correct state from current parameter values
  alone (not from history or in-flight transitions), and they self-correct on resume. `IsAnimatorEnabled`
  is *meant* to flip false one frame before a cull, but is unreliable (not fired for view culling) —
  don't lean on it. Distance-hide additionally unloads the avatar (blue diamond) and can restore dirty
  state (World-origin displacement, §Constraints); a manual re-show clean-reloads. Bounds-inflation
  ("anti-cull") keeps the avatar in view to defeat view culling.
- On avatar change, VRChat does not zero the previous avatar's OSC-visible parameters — external
  apps must reset state on `/avatar/change`.
- OSC: `/avatar/parameters/<name>`; ports default 9000/9001 but are **discovered via OSCQuery** —
  never hardcode them (vrc-bridge discovers). Params need not be synced to be OSC
  addressable — but the *name* must survive the build (VRCFury build-time reshaping, below).
  OSC-driven floats sync to remotes only if declared synced;
  otherwise encode them (see `gimmicks.md` float→bool patterns).

## Contacts

- Receiver modes: Constant (0/1 while overlapping), OnEnter (one-frame pulse; honors `minVelocity`,
  tested once at entry), Proximity (0..1; `minVelocity` inert). Proximity is **receiver-scoped**,
  not sender-centered — the value rises as the sender's *nearest surface* reaches the receiver, so
  enlarging the *receiver* lengthens the falloff. The exact model (emulator-confirmed,
  measured to three decimals): `1 − clamp(dist / radius)` where `dist` runs from the sender's nearest point
  to the nearest point on the receiver's **axis segment** — a capsule is a swept sphere (segment
  length = height − 2·radius, world-scaled; **radius alone** sets the falloff length everywhere
  along the axis; uniform scale preserves the shape, it never becomes a sphere unless
  height ≤ 2·radius), a sphere is the same formula against the center, and capsule-vs-capsule
  resolves segment-to-segment with the sender's surface offset by min(gap, sender radius). A box
  receiver's center mode is **Chebyshev per-axis** — `max(|d| / halfExtent)` in box space, not
  spherical — and face mode is a pure linear unlerp along local −Z from the +Z face plane, so box
  falloff is axis-separable by construction (what a diameter-compensated multi-box cage wants).
  The strongest overlapping sender wins (values are not additive).
- **`allowSelf`/`allowOthers` filters are evaluated only at contact acquisition, never re-checked
  on latched contacts.** Animating filters shut after acquisition locks the receiver onto the
  sender(s) it already holds — the core of contact-tracker targeting. Corollaries: waiting-state
  receiver size controls how many senders latch at trigger (several in the zone = all latched);
  filter *changes* affect only future acquisitions (an animated `allowSelf` opt-in works); a latched
  contact that fully breaks (sender exits range) **cannot re-latch while filters are shut** —
  re-entry is a new acquisition, so a multi-receiver rig degrades to partial probe sets whose
  skewed equilibria look like tracking error. A latched contact also survives its filter flipping
  shut mid-overlap — the held value is the latch working (emulator-reproduced), not a bug.
- Disabling a receiver's GO stops simulation but **freezes its parameter at the last written
  value** — nothing zeroes it (measured). Any machine that gates on sensing params across a
  disable must clear them itself (`gimmicks.md` off-state hygiene owns the idiom).
- Contacts are simulated on **every** client from replicated bone positions, but IK delay and
  per-client discrepancy mean remote-side triggers misalign — do not treat contact outputs as
  synced. Default: sense with `localOnly` receivers and sync a bool. When trigger latency matters,
  keep remote-firing receivers as the fast path *and* back them with a synced bool to catch missed
  triggers.
- Built-in senders on every avatar: `Head`, `Hand` (L/R), `Finger*`, `Torso`, `Foot` — remote
  players' bodies are queryable without them wearing anything. Auto head/hand contact placement
  varies per avatar (height/offset) — acquisition shapes should be generous (tall capsules) and
  identically placed if multiple receivers must latch the same target.
- The clamp is a hard floor: a receiver reads **exactly 0 at and beyond its range edge** (and when
  nothing overlaps) — the Custom-Object-Sync "contact bug" (`references/`) is this floor, not a
  defect. Keep the working volume off the boundary or bias the zero point.
- `localOnly=1` means the contact component **does not exist on remote clones**. Default to it:
  cheaper, and polite — because the bug below sums contacts *across* nearby players, local-only
  receivers stay off everyone else's solve. Per-shape limits (editor-enforced): size ≤ 6 units,
  radius ≤ 3, and 16 tags. **~24 receivers clustered in one spot, summed across nearby players,
  makes them read wrong values** — a known, VRChat-tracked bug with no workaround; keep clusters
  small.
- Two receivers writing the **same** param: the **last-enabled** one wins (values aren't summed) —
  order enables when multiplexing receivers onto one param.

## PhysBones

- Grab and pose state are **natively networked** — the free transport for continuous spatial input.
  Two distinct things sync: a **live grab** transports only the grabber's world target point plus an
  `_IsGrabbed` flag — every client re-runs the solve locally, so the chain regenerates per client and
  remote fidelity is bounded by the grabber's IK-delayed hand. A **pose** (grab released with posing
  allowed) instead snapshots each bone's rotation **relative to its parent/root** — this
  **late-syncs in-game** (a late joiner sees the posed chain; the emulator does **not** reproduce it —
  a bone posed locally holds on the wearer but does not transport to a non-local clone) —
  which places nothing absolutely unless the root is already agreed, but is exactly right for
  fixed-frame inputs (control panels, slider/slide-rule interfaces). A "drop"
  implemented by moving or freezing an **underlying transform** (e.g. constraint toggling under the
  bone) is outside physbone sync entirely and does **not** late-sync: anyone loading the avatar
  afterward sees the original position until the next grab.
  `<param>_IsGrabbed`, `_Angle`, `_Stretch`, `_Squish` regenerate per-client from the synced grab
  at zero expression bits; declaring a natively-driven param (physbone outputs, behavior-driven)
  as synced is a no-op that only wastes bits — the local component re-drives it every frame, so the
  synced value never survives to be read (and remotes regenerate their own from the grab regardless).
- The solver runs on a fixed **60 Hz virtual step** (substepped), so physbone behavior is
  framerate-independent until a slow frame hits the substep cap. Grab feeds the hand as the solver's
  tip target and blends toward the solved pose by the chain's grab-movement weight; it does not
  rigidly pin the bone. Remote-grabbed objects still disagree slightly across
  clients (the IK-delayed hand) — exact placement needs a real position sync on top.
- Three independent 0..1 forces shape a chain, each scaled by its own falloff curve along the length:
  **pull** (positional restoring toward the rest/animated pose), **spring** (velocity/momentum
  carried across steps — high spring + low pull = floaty overshoot), and **stiffness** (*angular*
  restoring toward the bone's prior direction). "Springy" is spring; "snappy" is pull; they don't
  substitute for each other.
- Force-release requires **both** halves: disabling the physbone's component/GO breaks an
  in-progress grab network-wide, but a disabled physbone won't set its `_IsGrabbed` back to false —
  pair the toggle with a driver clearing the param.
- Even at pull=1 a chain keeps settling after grab/release — not a pull lag (at pull=1 the pull step
  adds none) but retained momentum via **spring** and angular **stiffness**; zero both for a
  near-instant snap. Systems that snapshot a physbone-descendant position on release still want a
  short delay first.
- `isAnimated` must be on for animated physbone properties to apply; `resetWhenDisabled` controls
  pose persistence across GO toggles. `immobile` is a **0..1 amount** (not a switch) with two modes:
  *All Motion* re-anchors against the full root transform (ignores both movement and rotation — a
  pure sensor), *World (Experimental)* cancels only world translation so avatar rotation still
  drives the chain.

## Constraints (VRC)

- VRC constraints resolve in dependency-ordered execution groups within one frame — a constraint
  whose target is a parent of, or whose source sits inside, another's target runs first, and each
  group's writes are visible to the next. So chains (A←B←C) are consistent per-frame and measurement
  through several hops is sound. Ordering is guaranteed only within one **avatar root**, not across
  avatars.
- Constraints solve **once per rendered frame** (not on the physics tick). A constraint's slot
  relative to the PhysBone solve is derived from the hierarchy relation between its **effective
  target transform** (TargetTransform-aware — the transform it drives, not the component's
  GameObject) and a physbone's **root** transform: target at or above the physbone root ⇒
  **pre-physbone** (the constraint drives the chain); target or any source *inside* the chain ⇒
  **post-physbone** (it reads the solved pose); dependence on IK/animation ⇒ post-local-avatar;
  no relation ⇒ post-physbone. So to steer a physbone-controlled transform the driven target must
  sit at or above that chain's root; to read one, source from inside it. **Trap:** a constraint
  that both drives and reads a physbone resolves to post-physbone — the drive side silently loses,
  so split steering and reading across two constraints. The full per-frame dynamics order is one
  pipeline — pre-physbone constraints → PhysBones → post-physbone constraints → Contacts →
  post-local-avatar constraints — so contact receivers sample **after** the physbone solve.
- `TargetTransform` lets a constraint component live on GameObject X while driving transform Y —
  the "affect that other object" indirection (the target is frozen at play start; edit-mode only,
  not animatable). Combined with GO active toggling this hosts editor-only alignment helpers and
  build-time-only behaviors.
- **Two world-anchor idioms with different guarantees:**
  - `FreezeToWorld=1` (source-less) — locks where the avatar *loads in on each client*; fixed but
    **not cross-client consistent**. Editor-friendly when enabled only at upload (avatar stays
    movable in scene; enabling it in-editor bloats bounds as avatars move).
  - Constraint source pointing at a transform inside a **never-instantiated prefab asset**
    ("World.prefab" trick) — resolves as world origin **for every client**; required under any
    absolute-position sync. Known issue: remote distance-culling can displace the origin between
    hide/shows **(~, no workaround)**.
- Source-weight animation is the universal multiplexer: N sources at weight 0, states select one.
  Weights are **normalized by their sum**, not clamped to [0,1] — only the ratios matter.
  Self-as-source at partial weight = rotational/positional lag ("feel"
  damping). Disabling a constraint freezes its object where it stands — often simpler than weight
  juggling. Normalization has **no magnitude floor** above the write-nothing cutoff: near-zero
  residual weights (~1e-5) still command full-magnitude targets, so the frame a servo rig loses
  tracking kicks up to one probe-offset in a stale direction before any state-machine response
  lands — benign for a target that recedes continuously, pathological for one that teleports.
- A constraint with no sources (or zero total weight) writes **nothing** — it doesn't drive to a
  stored rest, it stops touching the transform, which then keeps whatever pose animation or
  authoring gives it (the "hold" idiom is this hands-off no-op). **`GlobalWeight 0` is not this
  no-op**: an active constraint at GlobalWeight 0 drives its transform to the captured `*AtRest`
  pose every frame — only a zero source-weight sum is hands-off. Per-axis `AffectsPosition/Rotation`
  masks decompose a transform into single-axis measurement/actuation channels.
- A constraint's sources may be **its own children** — feedback loops are legal and resolve
  consistently each frame (the basis of the crawler/cage tracking patterns in `gimmicks.md`).
- `Locked` bakes offsets at edit time; constraint state re-initializes on activation. The capture is
  the inspector's Lock/Activate **button routine** — script-setting `Locked = true` captures nothing,
  leaving `*AtRest`/offsets at type defaults, so code building constraints must set them explicitly
  or the constraint silently drives to the wrong rest.
- `Sources` is a bare field of **struct** type, and `IsActive` a bare bool defaulting **false** (the
  inspector's Activate button sets it). Reflection or `dynamic` access (`execute_code`) boxes the
  struct, so `Sources.Add(...)` mutates a copy and serializes nothing — no error, just
  `totalLength: 0` on disk and a constraint that never runs. Script-built constraints: write
  `Sources.source0.*`, `Sources.totalLength`, and `IsActive` through `SerializedObject`, then re-read
  the saved asset.

## Scale

Systems that size or place in world units must be scale-aware (avatar scaling is on by default).
Read-only params: `ScaleFactor`/`ScaleFactorInverse` (ratio to upload height, for DBT multiplies),
`EyeHeightAsMeters` (absolute metres, linear past the 5 m cap — the robust one), `EyeHeightAsPercent`
(0–1, Motion-Time-compatible, valid 0.2–5 m only), `ScaleModified` (bool).

## Other load-bearing components

- **VRCHeadChop**: exempts chosen head-descendant bones from first-person head shrink (scaleFactor
  1 = visible in first person) — required for self-interactable face gimmicks.
- **VRCRaycast** — the one avatar component that senses **world geometry**: a bone-origin ray with a
  set `distance`; the hit lands in a `resultTransform` (usable as a constraint source) and an
  animator param. Enables aim/attach-at-a-distance (throw a prop onto a wall = raycast hit +
  sample-and-hold). Recent SDK addition: **(~)** remote-side evaluation, culling behavior, and
  emulator reproduction are all unpinned — probe before depending on any of them.
- **VRCAnimatorLocomotionControl** `disableLocomotion`: freezes movement *and stops the player
  capsule from colliding* — a movement-locked player can be pushed through geometry ("reverse"
  collision). VRCAnimatorTrackingControl, VRCPlayableLayerControl: standard layer/tracking tools.
- **Particle system as world-collision sensor**: one immortal motionless particle + world collision
  (`minKillSpeed` ≥ its jitter) + `stopAction: Disable`, wrapped around an always-overlapping
  sender/receiver pair; the FX re-activates the GO each frame to re-arm. Radius must be tuned
  against the player capsule.
- **VRCFury build-time reshaping** (see `nondestructive.md` for the framework model): non-global
  params get instance-prefixed (`GrabBone` → `VF157_GrabBone`, moving physbone `parameter` fields and
  animator conditions with them); generated layers are tagged `[VF…]`. Past **256 synced bits** the
  **Parameter Compressor** engages — not a ceiling but a threshold VRCFury absorbs: it sets the
  overflowing params network-synced-**false** and time-multiplexes their values through one shared
  channel, rebuilding each on the remote clone via a parameter driver (so they update at a reduced
  rate). **Trap:** a compressed param reads *un-synced* in the baked ExpressionParameters yet still
  replicates — never infer sync state from the parameter asset alone. OSC-driven and `Add`-driven
  params stay uncompressed (tag a latency-critical param with an `Add` to exempt it). VRCFury records
  what it did in a `VRCFuryDebugInfo` "Parameter Compressor" component on the avatar root (bit totals,
  sync delay, batch counts) — read that instead of diffing builds. It fails loud only when even
  maximum compression can't fit. `ApplyDuringUpload` swaps editor scaffolding for runtime config at
  build; a mobile build additionally aligns its synced-param order to the last desktop upload's
  on-disk sync data, so that set isn't a pure function of the avatar. Framework choice and ordering
  rules live in `nondestructive.md`.
