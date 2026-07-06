# Verifying a gimmick

How to prove a claim about an avatar system, and how strong the proof is. Every claim states its
**rung**. This is the method; `gimmicks.md` is the patterns, `runtime.md` the physics, `unity.md` the
`execute_code`/MCP plumbing the rung-3 recipes run on (its §Sharp edges owns the compiler-backend, build-queues,
and read-path rules — don't restate them).

## The ladder

1. **Static** — read the assets, run nothing. Animator lint (missing motion GUIDs,
   undeclared/orphaned params, entry-ladder shadowing, WD inconsistency per layer, cross-package GUID
   refs), and constraint-graph review.
   Cheapest; catches the mechanical bug classes.
2. **Bake** — enter play mode (the build runs on the transient play copy; gate below) and read what it
   produced — VRCFury prefix rewrites, Parameter-Compressor membership, layer provenance, and the
   **true synced-param count** (the pre-build asset under-counts — MA/VRCF/prefab merges add synced
   params at build). The build is
   deterministic and fails loud, so **read the result, don't reconcile it against intent**: VRCFury
   reports its own reshaping in a `VRCFuryDebugInfo` "Parameter Compressor" component on the baked root
   (bit totals, sync delay, compressed-param membership — `runtime.md` §VRCFury build-time reshaping).
3. **Emulator** — play mode + Av3Emulator: drive inputs, observe outputs, spawn a remote clone,
   inject contacts, induce a physbone grab/pose. The bulk of this doc.
4. **In-game** — two real clients. The only rung that shows true network timing, IK delay, culling,
   grab/pose late-sync, and feel. Produce a targeted checklist for the human tester; say a claim
   rests on rung 4 rather than asserting it.

Rungs 1–3 are agent-automatable; rung 4 is not, and saying so is part of the report.

## Rung 3 — the Av3Emulator harness

**The play-entry gate — a hard gate before every play entry, in any workflow, not just rung-3.**
A play entry builds every active avatar (minutes each, main thread blocked) and a mis-set scene
silently invalidates everything observed. Never enter play without checking, and re-check every
entry — scenes drift:

- **Exactly one avatar root active** — the emulator builds every active descriptor (extras cost
  their full build time each and make the runtime lists ambiguous); deactivate the rest, restore after.
- **Gesture Manager disabled** — an active one (some avatars carry one) drives the avatar on play
  and fights the emulator.
- **Emulator control object enabled** — the emulator does not auto-spawn; the scene needs an
  enabled `Avatars 3.0 Emulator Control` object carrying the `Av3Emulator` component
  (**Tools → Avatars 3.0 Emulator → Enable** creates it; the Sandbox scene already carries it).
  Missing or disabled, play mode spawns no runtimes and the whole harness reads empty — silently.
- **`RunPreprocessAvatarHook` on** — this is what runs the non-destructive build on play (off →
  you exercise the raw pre-build avatar and every VRCFury/compressor fact here is void); and
  **`EnablePlayerContactPermissions` off** — the self+other default the fake-contact recipe below
  leans on.
- **The avatar carries a VRCFury Fix Write Defaults component** — the first build without one
  pops a blocking dialog that stalls everything (`unity.md` §Sharp edges: create it mode-Disabled).
  The one gate item the assert snippet below does **not** check (VRCFury's model is internal) —
  confirm it separately.

And capture every observation — runtime reads, `AvatarGrab` shots — **before exiting play**:
exit reverts the scene to authoring state, so anything captured after proves nothing about
driven behavior.

Assert before trusting a session:

```csharp
var emu = UnityEngine.Object.FindObjectOfType<Lyuma.Av3Emulator.Runtime.Av3Emulator>();
var gm  = UnityEngine.Object.FindObjectOfType<BlackStartX.GestureManager.GestureManager>();
int avatars = UnityEngine.Object.FindObjectsOfType<
  VRC.SDK3.Avatars.Components.VRCAvatarDescriptor>().Length;   // active only
bool ready = emu != null && emu.isActiveAndEnabled
  && emu.RunPreprocessAvatarHook && !emu.EnablePlayerContactPermissions
  && (gm == null || !gm.isActiveAndEnabled) && avatars == 1;
```

**Runtimes.** On play the emulator spawns three `Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime`: local
(`IsLocal`), MirrorReflection (`IsMirrorClone`), ShadowClone (`IsShadowClone`). Each holds
`Floats/Ints/Bools` lists (`.name/.value/.synced`) plus built-in input fields (`GestureLeftIdx`,
`Viseme`, `TrackingType`…). Get the local one:

```csharp
var rts = UnityEngine.Object.FindObjectsOfType<Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime>();
Lyuma.Av3Emulator.Runtime.LyumaAv3Runtime local=null;
foreach (var rt in rts) if (rt.IsLocal) local = rt;
```

**Drive / observe.** Write `.value` on the local runtime's **input** params (menu/expression inputs —
a driver-written output reverts each frame); it lands next tick. Read outputs from the runtime lists,
scene transforms/blendshapes, or `ContactReceiver.paramValue` — matching the observable to the output
channel (material / transform / blendshape / GO-active), or a naive scene-diff misses it.

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
synced-bit cost from the post-build `VRCFuryDebugInfo` bit totals (rung 2), never a raw param-asset
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
comp.chainId, bone)` returns a `Grab`; set `grab.GlobalPosition` in the **same call** (it defaults to
origin, else the chain snaps to 0,0,0). Move it across calls via `GetGrabs()` (match `chainId`) — the
solver drags the chain and `_IsGrabbed` fires. `ReleaseGrab(chainId)` clears it;
`ReleaseGrab(grab, true, grabberId)` on an `allowPosing` bone leaves it **held** (read the bone
transform; no `_IsPosed` param). Discover grabbable bones by scanning chains for `allowGrabbing != 0`;
offset the target off the bone endpoint or `SolveGrabIK` spams a benign `FromToRotation` assertion.

**Verify mirror-detection.** The MirrorReflection clone runs its animator but skips the local avatar's
init drivers, so driver-set params (a `MirrorDetection/IsMirror` flag, constant-1 params) stay
permanently at their un-driven defaults while local shows the driven value — diff local-vs-mirror.

## What the emulator reproduces — and doesn't

**Reproduced (assert on rung 3):** local param drive/read, driven outputs, `IsLocal`-branch
divergence, 8-bit sync quantization + the ~0.1 s tick, local contact physics, a scripted "other"
sender, **mirror-clone SMB-asymmetry** (so mirror-detection is testable), and a real **local**
physbone grab/pose.

**Not faithful — keep on rung 4:** network-sync *correctness* (the compressor hides it), remote-side
contacts/trackers, real IK smoothing / ~0.5 s body delay, a *networked* grab or **pose late-sync** (a
locally-posed bone does not transport to the clone), distance-culling animator pause, and true feel /
framerate-dependent constants (the editor throttles to ~12 fps unfocused). Don't spend a play session
chasing these.

## Cost

Play-mode entry is the bottleneck — the whole non-destructive build runs on every entry (minutes on a
heavy avatar) — so **batch every assertion into one play session**; re-enter only to test an
asset/controller edit. Within a session compute is cheap, but MCP round-trips and the ~12 fps
unfocused throttle gate wall-clock, so time-based settles cost real seconds.
