# Verifying a gimmick

How to prove a claim about an avatar system. The bar is **compiles + `Check*` PASS + behaves in the
emulator** — that is tested as far as an agent can test. This is the method; `gimmicks.md` is the
patterns, `runtime.md` the physics, `unity.md` the `execute_code`/MCP plumbing the emulator recipes run
on (its §Sharp edges owns the compiler-backend, build-queues, and read-path rules — don't restate them).

## The method

**Static** — read the assets, run nothing. Animator lint (missing motion GUIDs,
undeclared/orphaned params, entry-ladder shadowing, never-firing transitions, WD inconsistency per
layer, cross-package GUID refs), a placement check on the in-scene avatar root (`CheckAvatar`: MA-scene-ref + clip-binding refs a
base rename silently broke — `PASS`/`CLASSIFY`), a compose-fit check (`CheckSeam`: weighted-humanoid-bone
world-position coincidence — `PASS`/`NOT-PASS`/`REFUSE`), and constraint-graph review.
Cheapest; catches the mechanical bug classes.

**Bake** — enter play mode (the build runs on the transient play copy; gate below) and read what it
produced — VRCFury prefix rewrites, Parameter-Compressor membership, layer provenance, and the
**true synced-param count** (the pre-build asset under-counts — MA/VRCF/prefab merges add synced
params at build). The build is
deterministic and fails loud, so **read the result, don't reconcile it against intent**: VRCFury
reports its own reshaping in a `VRCFuryDebugInfo` "Parameter Compressor" component on the baked root
(bit totals, sync delay, compressed-param membership — `runtime.md` §VRCFury build-time reshaping).

**Emulator** — play mode + Av3Emulator: drive inputs, observe outputs, spawn a remote clone,
inject contacts, induce a physbone grab/pose. The bulk of this doc.

These are agent-automatable and together are the bar. What only two real clients in-game can show —
true network timing, IK delay, culling, grab/pose late-sync, and feel — is a property of the specific
behavior, not a grade: name it and hand the human tester a targeted checklist rather than asserting it.

**A render is not an agent verdict.** A model can't judge fit or alignment from a single contact sheet — a
~5 cm offset, even a missing body, reads as correct at every tier, and higher tiers only raise the
confidence of the miss. Where a quantified signal (a seam delta from `CheckSeam`, a param read, a `Check*`) and an image
read disagree, the measurement is authoritative and the image is narrative. Renders serve the operator's
eye and the audit trail. The one agent-readable use is **differential** — a before/after pair around a
discrete change (a toggle, a blendshape) shows whether it took effect; a single-sheet absolute judgment
does not.

## Test venue — NUnit vs execute_code

NUnit EditMode tests may build and read live `UnityEngine.Object`s, but must not **mutate** them
(`SerializedObject`/`SerializedProperty` writes, `AddComponent`, `CopySerialized`) when those objects
will later be destroyed: doing so corrupts Unity's global object registry (`ms_IDToPointer` double-
erase → SIGSEGV) at the next allocation, and the crash is unfixable by teardown hygiene (proven — see
the run-tests-test-venue spec). Verify mutation behavior by running the tool via `execute_code` on a
real avatar (the operator's gate above). Run the NUnit suite headless with
`tools/run-editmode-tests.ps1` against the generated `TestEditor` (bootstrap.md). MCP `run_tests` is the
wrong venue (it runs in the live editor) — the proxy allowlist hides it and redirects a call here.

## The Av3Emulator harness

**The play-entry gate is enforced in-Editor.** The `PlayGate` hook (`com.ryan6vrc.agent-tools`)
evaluates the active scene on every entry and **cancels** a mis-set one, naming each offender and its
fix in a `[PlayGate] … => FAIL` console line (plus a Scene-view overlay), with a one-shot
`Tools/Agent/Play Gate/Allow Next Entry` override. It covers the hard preconditions — one active
avatar and a VRCFury Fix Write Defaults feature (**skipped on a VRCFury-free avatar** — `fury.Count == 0`),
plus (when an enabled emulator is present) no active
Gesture Manager and the emulator's `RunPreprocessAvatarHook`/`EnablePlayerContactPermissions` (a
Gesture Manager only fights a *live* emulator). Read the verdict; don't hand-check them.

It does **not** check that an emulator control object is *enabled* — absence is a legitimate bake-only
check, so the gate stays silent, but driving the emulator without it spawns no runtimes and the harness reads empty:

- **Emulator control object enabled** — the emulator does not auto-spawn; the scene needs an enabled
  `Avatars 3.0 Emulator Control` object (the `LyumaAv3Emulator` component). **Tools → Avatars 3.0
  Emulator → Enable** creates it, per-scene — no scene ships it pre-enabled, so run the recipe yourself
  (play then spawns the three runtimes).

And capture every observation — runtime reads, `RenderAvatar` shots — **before exiting play**:
exit reverts the scene to authoring state, so anything captured after proves nothing about
driven behavior.

**Runtimes.** On play the emulator spawns three `Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime`: local
(`IsLocal`), MirrorReflection (`IsMirrorClone`), ShadowClone (`IsShadowClone`). Each holds
`Floats/Ints/Bools` lists (`.name/.value/.synced`) plus built-in input fields (`GestureLeftIdx`,
`Viseme`, `TrackingType`…). Get the local one:

```csharp
var rts = UnityEngine.Object.FindObjectsOfType<Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime>();
Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime local=null;
foreach (var rt in rts) if (rt.IsLocal) local = rt;
```

**Drive / observe.** For menu/expression inputs write **`.expressionValue`** on the local runtime's param,
**not `.value`** — the runtime rewrites `.value` from `.expressionValue` each frame on **synced** params, so
a `.value` write silently reverts (it holds on unsynced params, which hides the trap until a synced one);
`.expressionValue` drives both. (A driver-written *output* also reverts each frame, by design.) It lands next
tick. Read outputs from the runtime lists, scene transforms/blendshapes, or `ContactReceiver.paramValue` —
matching the observable to the output channel (material / transform / blendshape / GO-active), or a naive
scene-diff misses it. **A driven material property lands in the renderer's `MaterialPropertyBlock` in play
too** — not just the edit-mode tick below — so read it with `GetPropertyBlock`, never `.material`/
`.sharedMaterial` (which return the authored asset value → false negative).

**Observation channels — don't cross them.** Three output kinds live in three places. **Driver** outputs
(`VRC_AvatarParameterDriver` Set/Add/Copy — a debounce flag, codec bits) land in the runtime's
`Bools/Floats` mirror: write the input (per §Drive/observe), read the output there. **Blend-tree / AAP** outputs (a
Direct-tree smoother's feedback float) are **not** in the mirror — read them off the live animator by setting
`local.DebugDuplicateAnimator = VRCAvatarDescriptor.AnimLayerType.FX`, then
`avatar.GetComponent<Animator>().GetFloat("<VF##_>name")` (VRCFury prefixes the param). But the debug
animator **runs without the avatar's init drivers**, so drivers don't execute on it: read driver outputs from
the mirror with debug **off**, AAP outputs from the debug animator with debug **on**, never both in one
session (exiting play resets the mode). Crossing them is why a working codec reads all-zero.

**Pure controller math skips play mode entirely.** When a compiled controller's outputs are only
AAPs / blend-tree math — a smoother, a math idiom, a frametime rig, with no drivers, contacts, or sync —
host it on a bare `Animator` and tick `Animator.Update(dt)` in edit mode: `SetFloat` the inputs, tick N
frames, `GetFloat` the outputs. Deterministic, exact `dt` (a frametime rig reads it exactly), one
`execute_code` call, and the inputs need not be synced params. Faithful because AAP writes and blend-tree
evaluation are stock Unity, identical to the FX playable. Two traps: **material** animation lands in the
renderer's `MaterialPropertyBlock` — read `renderer.GetPropertyBlock(mpb); mpb.GetVector(prop)`, not
`sharedMaterial` (which stays at the authored default and reads as a false negative; clone the material
onto a temp renderer so no shared asset is touched); and cross-layer AAP writes propagate one frame late,
so a multi-layer feedback loop (a fixed-step linear smoother) limit-cycles and a feed-forward chain
settles only after ~depth frames — read feed-forward outputs at steady state.

**Two-call assertion** (frames advance only between calls; persist across them in `EditorPrefs`,
editor-local — delete the key after):

```csharp
// Call A: baseline + stimulus
UnityEditor.EditorPrefs.SetString("k", idx.localRotation.eulerAngles.x.ToString());
local.GestureLeftIdx = 1;
// Call B: sample + verdict
float d = UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(
  float.Parse(UnityEditor.EditorPrefs.GetString("k")), idx.localRotation.eulerAngles.x));
string verdict = d > 10f ? "PASS" : "FAIL";
```

**Remote clone.** `local.CreateNonLocalClone = true` spawns a non-local copy. Diff local-vs-clone
params to assert `IsLocal`-branch divergence (a bit-sync system runs its write side on local, read
side on the clone). The emulator models 8-bit float quantization (~1/127 steps) and the ~0.1 s sync
tick (`NonLocalSyncInterval`). **But the `synced` flag lies both ways** — the baked flag reads
synced-false for compressed params that still replicate (VRCFury's Parameter Compressor), and the
pre-build asset under-counts (build-time MA/VRCF/prefab merges add synced params) — so judge the
synced-bit cost from the post-build `VRCFuryDebugInfo` bit totals (from the bake), never a raw param-asset
flag.

**Fake another player's contact.** A scripted sender fires an `allowOthers`-only receiver solo (the
single-avatar `EnablePlayerContactPermissions=false` default treats every contact as self+other):

```csharp
var go = new UnityEngine.GameObject("Sender"); go.transform.position = head.position;
var s = go.AddComponent<VRC.SDK3.Dynamics.Contact.Components.VRCContactSender>();
s.shapeType = VRC.Dynamics.ContactBase.ShapeType.Sphere; s.radius = 0.05f;
s.rootTransform = go.transform;
s.collisionTags = new System.Collections.Generic.List<string>{ "Hand" };
// next call: read the target receiver's .paramValue / .IsColliding()
```

**Induce a physbone grab/pose.** `VRC.Dynamics.PhysBoneManager.Inst.AttemptGrab(grabberId,
comp.chainId, bone)` returns a `Grab` — **`grabberId` must be `0`** (an arbitrary id returns null); set
`grab.GlobalPosition` in the **same call** (it defaults to
origin, else the chain snaps to 0,0,0). Move it across calls via `GetGrabs()` (match `chainId`) — the
solver drags the chain and `_IsGrabbed` fires. `ReleaseGrab(chainId)` clears it;
`ReleaseGrab(grab, true, grabberId)` on an `allowPosing` bone leaves it **held** (read the bone
transform; no `_IsPosed` param). Discover grabbable bones by scanning chains for `allowGrabbing != 0`;
offset the target off the bone endpoint or `SolveGrabIK` spams a benign `FromToRotation` assertion. Two
control-experiment traps: an **`immobile=1.0` AllMotion chain won't drag** under a scripted-position grab
(the solver pins it), and **runtime mutation of physbone settings never reaches the native solver** (they
bake at chain init), so "change a setting, then grab" silently no-ops. A PB with **no `parameter` declared
mints no `_IsGrabbed`/`_Stretch` params at all** — assert the bone transform/chain, not a param.

**Verify mirror-detection.** The MirrorReflection clone runs its animator but skips the local avatar's
init drivers, so driver-set params (a `MirrorDetection/IsMirror` flag, constant-1 params) stay
permanently at their un-driven defaults while local shows the driven value — diff local-vs-mirror.

## What the emulator reproduces — and doesn't

**Reproduced (assert in the emulator):** local param drive/read, driven outputs, `IsLocal`-branch
divergence, 8-bit sync quantization + the ~0.1 s tick, local contact physics, a scripted "other"
sender, **mirror-clone SMB-asymmetry** (so mirror-detection is testable), and a real **local**
physbone grab/pose.

**Not faithful — needs two clients in-game:** network-sync *correctness* (the compressor hides it), remote-side
contacts/trackers, real IK smoothing / ~0.5 s body delay, a *networked* grab or **pose late-sync** (a
locally-posed bone does not transport to the clone), distance-culling animator pause, and true feel /
framerate-dependent constants (the editor throttles to ~12 fps unfocused). Don't spend a play session
chasing these.

## Cost

Play-mode entry is the bottleneck — the whole non-destructive build runs on every entry (minutes on a
heavy avatar) — so **batch every assertion into one play session**; re-enter only to test an
asset/controller edit. Within a session compute is cheap, but MCP round-trips and the ~12 fps
unfocused throttle gate wall-clock, so time-based settles cost real seconds.
