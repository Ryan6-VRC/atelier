# Unity

`AvatarProject/` is the sandbox Unity project (its own Git repo). Unity **2022.3.22f1**, VRChat-pinned —
never upgrade (breaks uploaded content).

Packages are VPM-managed and reproducible (constraints: workspace `CLAUDE.md`; commands: `bootstrap.md`).

## Unity MCP

Transport is stdio; the server brokers to each Editor's bridge across recompiles/domain reloads.
Registration, transport, and package-update wiring: `bootstrap.md`.

- Read editor state via **resources** (`mcpforunity://editor/state`, `project_info`, …); perform
  mutations via **tools** (`manage_scene`, `manage_gameobject`, … — permission-gated) or `execute_code`.
- After creating/editing scripts, check `read_console` for compile errors before using new types
  (poll `editor_state.isCompiling` for the domain reload).
- The one `UnityMCP` server reaches every local Editor, carries no default instance, and does **not**
  error on ambiguity — unpinned calls silently land on an arbitrary Editor (observed). So
  `set_active_instance` is the first Unity call of every session, with the **full** `Name@hash`
  (a bare name silently no-ops → crosstalk). The live instance table is injected into session
  context at start (SessionStart hook → `tools/unity-instances-hook.sh`); also queryable via the
  `mcpforunity://instances` resource. Hashes are path-derived cache keys — read them live, never
  copy them into docs or config.
- If `UnityMCP` tools are absent: the Editor isn't open on `AvatarProject`, or Claude Code needs a
  restart (`start-vrc.ps1` is the bring-up doctor).
- **Trust the heartbeat, not the MCP window.** The Editor's *MCP for Unity* window can show "No Session"
  while the stdio bridge is up — a cosmetic desync; the `~/.unity-mcp/` heartbeat (what `start-vrc.ps1`
  reads) is truth.
- **Never switch to the Editor-hosted http transport.** It drops on every domain reload, and its toggle
  (`MCPForUnity.UseHttpTransport`) is a **machine-global** EditorPref shared by every project on this
  Editor version — flipping it hits all of them on the next restart.

## Inspection & reporting (agent-tools)

Shipped as the `com.ryan6vrc.agent-tools` package (from `vrc-unity-tools`, consumed via a local `file:`
ref); also home of the shared reporting conventions (`RunLogFormat`, the `[AgentTool]` marker).
`RunLogFormat.WriteRunLog(dir, label, summary, body, ext)` is the body-agnostic writer every
non-transplant emitter routes through: it owns the dir + timestamped filename and appends the in-band
`| log=<path>` trailer, or returns a bare-FAIL with no trailer when the write fails. `RunLogDir`
(`Assets/Agent/RunLogs/`, verdict records) and `SnapshotDir` (`Assets/Agent/Snapshots/`, read-only
captures) are the single declarations of the two output dirs.
`AgentInspector` walks selected/scene objects (incl. VRChat components,
generically via `SerializedObject`) to JSON under `AvatarProject/Assets/Agent/Snapshots/`; the
written path is emitted in-band on the console line (`… => OK | log=<path>`). Agent door:
`AgentInspector.Snapshot("Root/Child/Path", includeChildren, followAssets)` snapshots by hierarchy
path and returns that summary. Any objectReference resolving to a saved asset carries `guid`/`fileId`
(sub-asset-safe) **unconditionally**, so every ref is edit-addressable; a scene-object ref keeps its
`scenePath` instead. `followAssets` additionally inlines a generic `SerializedObject` dump (`fields`,
recursive) of each **ScriptableObject-asset** ref — a `VRCExpressionsMenu` `subMenu` chain or
`VRCExpressionParameters` expands to the whole tree in one snapshot. Non-SO assets (meshes, clips,
controllers) get identity only, not expansion (no overlap with `ControllerReport`/`ClipReport`). The
expansion is bounded by asset-hop depth and a walk-wide budget, and every cut is signaled inline
(`assetDepthCapped`/`budgetSkipped`/`alreadyDumped`) plus a top-level `assetsTruncated` count — it
dumps raw values; decoding them stays yours.

`ImportVerify.VerifyFolder(path)` / `VerifySelection()` is the deterministic import
health check — reports **missing** (not merely empty) material slots, meshes, and scripts, plus
**stale FBX material remaps** (a model whose external-material remap resolves yet imports empty). Its
one-line PASS/FAIL summary ends with the RunLog path in-band (`… => RESULT | log=<path>`); a bad-input
early return is a bare `[ImportVerify] FAIL: …` with no trailer. Distinguishing missing from intentionally-empty submesh slots is the whole
point; raw null counts false-alarm. Call it after every vendor import.

Three read-only **animator-introspection** tools turn raw `.controller`/`.anim` YAML into cheap
deterministic digests:

- `ControllerReport.Report(controller)` — a ~50:1 markdown
  digest that *decodes* animator semantics rather than echoing YAML: parameters, layers (+ per-layer
  Write-Defaults), states and their motions (clips named by **asset-path + GUID**, an empty-vs-broken
  split that surfaces a dangling motion GUID), the first-match transition ladder, and VRC
  state-machine behaviours decoded **typed**. To `Snapshots/`; `… layers=… states=… params=… => OK | log=<path>`.
- `ClipReport.Report(clip)` / `ReportFolder(folder)` —
  bindings as a `path | type | propertyName | keys` table (one row per curve), paths as-authored (a `""` root shown as `(root)`, never
  judged). To `Snapshots/`. Folder mode mirrors `ImportVerify.VerifyFolder`, down to the
  empty-but-valid `0 clips => OK`.
- `AnimatorLint.Lint(controller, basis, mergeSite, avatarRoot, mountRoot)` — binary **PASS/FAIL**
  (FAIL iff an `error`-tier rule fires) + per-kind counts + a
  two-tier offender body, to `RunLogs/`. Only five `error` rules flip the verdict —
  unresolvable-motion-GUID, undeclared-param (VRC built-ins exempt), unconditional-entry-shadow,
  never-firing transition (a state hop with no condition **and** no exit time), broken-binding; every
  heuristic (WD disagreement, orphans, dead layers, cross-package/archive refs)
  stays **advisory**, so the verdict never rests on a guess. Binding resolution
  needs a root the `.controller` lacks: `basis=auto` reads the merge component at `mergeSite` to take
  the frame the build will (MA `pathMode` / VRCFury prop-root preference — `nondestructive.md`),
  refusing on zero/multiple/mismatched components and rendering the choice
  (`basis=auto→mount(<path>) [MA MergeAnimator]`); `basis=explicit` asserts `avatarRoot`/`mountRoot`.
  Under `auto`, broken-binding demotes to advisory (the build rewrites paths, so an authored-scene
  resolve would false-FAIL).

`AvatarLint.Inspect(avatarRoot)` is the scene-scoped companion to those digests: on an instantiated
in-scene avatar (descriptor) root it names the two path-encoded reference breaks a base rename leaves after
a placement — **MA scene refs** (the `referencePath`+`targetObject` `AvatarObjectReference` signature:
reactive family / BlendshapeSync / Mesh Settings) and **clip/controller bindings** (descriptor playable
layers + every MA MergeAnimator / VRCFury FullController). It resolves every ref against the **placed
scene** — a to-be-merged bone is present pre-bake and resolves now, a base-rename break does not, so it
predicts nothing about what the build will move and never leans on the `Armature.<Name>` convention —
reusing `AnimatorLint`'s extracted binding-walk (MA at its one fixed frame; VRCFury by upward-strip against
every ancestor to the avatar root, so a legit avatar-level ref at a non-mount frame is not a break) with
the build-rewrite demotion off, and resolving MA refs through MA's own `.Get()` (which honours
`targetObject` before `referencePath`) behind a guarded self-resolve fallback — every reflective hop
guarded, never throws. Its verdict is a **new family token, `CLASSIFY`** (unresolved refs found — a finding
for the agent to route, not a tool failure: `Debug.LogWarning`), distinct from `PASS` (`Debug.Log`) and a
bad-input bare `FAIL` (`Debug.LogError`, no trailer). It computes **no** heuristic — it names each offender
and its class, and a `clip-binding` offender carries a distinct `clipAssetPath` (the field the compose
agent routes on: owned/writable ⇒ inline `UC2` clip-fix; `Assets/Vendor/`|`Packages/` ⇒ abort the compose
and route to `own-mergeable`). Inspection-only — no scene dirty, no `.anim` write; the remedy lives in the
skill, not the tool.

`AvatarGrab.Capture(target, angles, hide, margin, showGizmos, resolution)` drives the
operator's **Scene View** to render **one** avatar subtree in isolation to a temp contact-sheet PNG —
the clipping/fit backstop `compose-mergeable` defers to the operator. Where the MCP
`manage_camera`/`manage_scene` screenshots render the whole scene, this shows the target alone with the
**NDMF/MA preview resolved** (reactive fit applied). It auto-frames each angle to the drawn silhouette,
so prop-heavy and shader-scaled avatars fit correctly; `margin` pulls back, `hide` drops clutter props
(the build-added ~10 km `Culling` mesh is dropped automatically), `showGizmos` overlays physbone/contact
gizmos. It renders the avatar **as the operator has it** — eye-hidden children stay hidden; to include a
hidden part, un-hide it before the grab and restore it after (the read-only tool never reveals what the
operator hid). Angles are the six world axes `{front,back,left,right,top,bottom}` (default `[front,back]`);
success carries a `png=` trailer to `Read`.

The traps a model won't hit by just calling it: the fit is the editor *preview*, not the baked upload
clone (`nondestructive.md`) — a play-mode build and the operator's eye stay the bar. **Grab in a separate
call from any edit** — a same-call grab shows the pre-edit proxy; the summary's `note=` flags an in-flight
rebuild but cannot catch the same-call case. Angles are **world** axes, so a rotated target shows the scene's front (the upside: it also
works on a child or non-avatar object). Headlight shading is truthful for geometry/silhouette/clipping/
fit, not matcap/rim/fresnel. INSPECTION-class: it restores the view transform, display toggles,
selection, and root-level visibility, leaving the scene un-dirtied, and writes to
`Application.temporaryCachePath`; visibility restore is coarse — a nested eye-hide the operator set
under a subtree the grab hid isn't preserved. In **play mode** it captures the
driven runtime: play's game loop pumps `update` ticks continuously, so the reactive rebuild settles on its
own — no separate-call step needed — and the `note=` is suppressed (nothing in flight to flag). It doubles
as the visual companion to `verify.md`. **Grab driven state while still in play**: exiting play reverts the
scene to authoring state, so a post-exit grab can verify only the static baseline — never a
toggle/param-driven claim.

`Unity.exe` is GUI-subsystem and does not block under `& exe`; use `Start-Process -Wait` for headless
batchmode runs.

## Avatar tools

`com.ryan6vrc.avatar-tools` (from `vrc-unity-tools`, local `file:` ref) is the agent-callable kit for
turning a vendor avatar into our own normalized avatar. (The package split is by domain, not
read-vs-write: `agent-tools` holds generic Unity inspection/reporting plus the shared conventions;
`avatar-tools` holds the avatar-owning kit, including its own read-only reporters like
`AvatarPackageGraph` — and depends on `agent-tools`, never the reverse.) Each tool is a static method invoked via
`execute_code`, emits a one-line `PASS/FAIL` summary that ends with its JSON RunLog path in-band
(`… => RESULT | log=<path>`, written under `Assets/Agent/RunLogs/`; omitted only when the write
failed), and is **idempotent** (safe to re-run on the same instance). They share `RemapReferencesByPath`, a
path-based remapper that rebinds scene references from the vendor hierarchy to ours, duplicate-sibling
safe.

Avatar assembly here is non-destructive (NDMF / Modular Avatar / VRCFury); see `nondestructive.md` for the
reference-hardening model that governs what these path-based tools can rebind and what they must preserve.

- `AvatarPackageGraph.Report(vendorFolder)` — read-only: per-FBX mesh inventory, a head/body **guess**
  (`headGuess`/`bodyGuess`, a most-blendshapes heuristic — verify), the superset FBX (or "none"),
  toggle membership (renderers a clip drives via `m_IsActive` — GameObject-active — not a name
  convention), constraint count, MA/VRCFury/NDMF detection.
- `MatchHumanoidRig` — builds a fresh humanoid from our own model's skeleton (the bind, so it survives
  reproportioning) and conforms the vendor's bone mapping + muscle settings onto it (copying a rig
  wholesale is unreliable). `poseDriftMm` is informational only — a raw max world-space drift of the
  humanoid bones vs the vendor, in mm; expected nonzero after reproportion, never gates. `Preflight`
  reports the pre-reimport preconditions go/no-go without reimporting (the reimport is the operation, so
  there is no `whatIf`).
- `ReproportionFreshness` — read-only guard: asserts each humanoid bone's stored bind (frozen in the
  `.meta`) still matches the current model's local position, FAILing (named) on drift — catches a
  re-export that skipped re-running `MatchHumanoidRig`. Position-only: Unity stores a thumb-corrected
  bind rotation that legitimately differs even on a healthy rig.
- `ConformRenderers` — assigns vendor materials by renderer name from any source hierarchy (by reference,
  no `.mat` copies; an optional override map covers meshes renamed during normalization) and applies the
  renderer-normalization standard below. `whatIf` previews the full match/verdict and mutates nothing.
- `CopyDescriptor` — gates on scale + face-blendshape parity, transplants the VRCAvatarDescriptor with
  refs remapped, and installs a **fresh PipelineManager** (never the vendor blueprint ID). Post-copy it
  recomputes `ViewPosition` via `FixViewpoint` (non-fatal — a viewpoint miss never flips the transplant
  verdict). `whatIf` runs the gates + critical-ref snapshot and reports the predicted outcome (remap counts
  land only on execute).
- `FixViewpoint(ownedRoot, referenceRoot, whatIf=false)` — recomputes the owned descriptor's `ViewPosition`
  from a **required** known-good `referenceRoot` (vendor source, or the pre-reshape prior version) plus both
  rigs' Head + eyes, re-seating the creator's eye→viewpoint offset on the moved eyes rather than snapping to
  them. **Named FAIL (no guess)** on a non-humanoid rig, unmapped eyes, or coincident eyes. Idempotent. The
  `reproportion` skill drives the in-place case; `CopyDescriptor` calls it post-copy.

The **component-transplant kit** — `CopyComponents`, `RelocateComponents`, `GraftHierarchy` over a shared
transplant core — is **component-agnostic**: selection is a list of **type-name strings** (resolved via
`TypeCache`, matched by assignability, fail-loud on ambiguity), so the same tools serve VRC dynamics on a
base body and MA/VRCFury/NDMF on an outfit without the package referencing those assemblies (stays
VRC-SDK-only). Two tiers: a **deep** tier for the closed, owned VRC set (physbone / collider / contact /
VRC-constraint — dependency-follow, `Col_*` leaf-anchor recreate, hard/soft criticality, `force`/scaffold,
from a typed table) and a **conservative** tier for everything else (MA / VRCFury / NDMF / unknown / Unity
built-in constraints — `CopySerialized` + generic object-ref remap, leave-missing-missing). The **reach
root** `(vendorSource, ownedRoot)` bounds the remap: refs to objects under the vendor source rebind to
our counterparts; out-of-reach refs (assets, other-avatar objects) are left for placement-repair.

A **differently-named armature-root GO** (owned `Armature.1` vs vendor `Armature`) nulls every ref through
it under the name-based matching above. `CopyComponents` / `GraftHierarchy` take an optional `renameMap`
(`vendorName ⇒ ownedName`, injective, **case-sensitive**) that reconciles it — one entry
(`"Armature" ⇒ "Armature.1"`) covers hosts and relocated-outside-armature anchor refs alike. An absent map
is a no-op; a non-injective or ambiguous map (one that can't address a unique dest sibling) is a **named
FAIL in both `whatIf` and execute**, never a silent mis-bind.

- `CopyComponents(ownedRoot, vendorSource, typeNames, force=null, renameMap=null, whatIf=false)` — reproduce all
  components of the named types onto our rig, **additive + idempotent** (count-parity skip per
  `(host, type)`; never destroys; a re-run is a no-op). `whatIf` reports the full plan and mutates nothing;
  a real run replays that same plan (preview == execute). A **flagged-missing host is PASS** — the named
  prune-backstop list to triage (`force` it via `vendorRelativePath :: ComponentType`, re-prune, or
  accept). A **null ref on a copied component** is surfaced separately as "verify — may block build"
  (non-fatal but can abort the downstream VRCF/SDK build). **FAIL** only on a vendor-source leak,
  `AddComponent`/scaffold failure, or unresolved type. Copy from the **standalone** vendor source, not an
  outfit already placed in an avatar.
  Flagged-missing hosts are classified in the RunLog note: **`[bone]`** — a skeleton bone absent on our
  rig, a genuine prune/rename divergence to investigate; **`[holder]`** — a non-bone GO the source parked
  the component on (deep-tier only; conservative hosts are untagged, having no scaffold path). When the
  source parked dynamics on holder GOs (a consolidated/grouped avatar), the holder paths are absent on a
  **faithfully re-exported** target and flag `[holder]` — physbones/constraints always, and
  colliders/contacts too **when their holder's parent is also absent** (holders under an `AvatarDynamics/…`
  container). A collider/contact whose holder sits directly under a **surviving bone** is instead
  auto-recreated (`RecreateLeaf`, no force key needed) and never appears in the `[holder]` set. Forcing the
  `[holder]` keys scaffolds those holders back — anchors path-remap to our bones, collider refs resolve by
  topo order — which **reconstructs the grouping, so a following `RelocateComponents` is redundant**.
  Force-all-`[holder]` is safe **only** when the target is a faithful re-export (no bones pruned, no
  content dropped — the reproportion twin/copy case); on the vendor→owned path a `[holder]` may be a
  deliberately-pruned accessory, so the flagged-missing default (force / re-prune / accept) stands.
- `RelocateComponents(ownedRoot, targetRoot, typeNames, destPath, whatIf=false)` — relocation primitive
  (the type-name list replaces the old `mode`). Matches components whose effective anchor descends from
  `targetRoot`, mints a holder under `destPath`, pins each anchor to its original transform — behavior-neutral,
  **never moves a bone**. Anchor field per type comes from the VRC table; a targeted type with **no table
  anchor FAILs loud** (refuses MA/VRCF/NDMF *and* Unity built-in constraints). Idempotent (skips a holder
  already placed under `destPath`); run **pre-prefab**. Called N times at operator discretion; echoes matches for closed-accounting.
- `GraftHierarchy(ownedRoot, vendorSource, subtreeRoots, renameMap=null, whatIf=false)` — copies named GO **subtrees
  wholesale**: scaffold the full structure (vendor verbatim local TRS) + copy **all** components on every
  GO (type-blind), remapped against the reach root. For pulling an outfit's authoring/menu subtree without
  listing every GameObject. Inverted contract vs CopyComponents: a missing host is **expected/normal**
  (you are scaffolding), never flagged. Count-parity + reuse-by-path idempotent.
- `CleanController(sourceFx, ownedRoot, outDir, keepLayerNames, whatIf=false)` — minimal controller keeping
  the **named** layers (base layer 0 always retained; FAILs on an absent/ambiguous name — no magic layer
  count), its **parameter list pruned to what the kept layers reference**, + empty
  expression params/menu, wired into the descriptor. **Create-if-missing / reuse-if-present** with
  GUID-stable shared asset names (`<sourceFx>_Clean.controller`, `VRCExpressionParameters_Empty.asset`,
  `VRCExpressionsMenu_Empty.asset`) so variations of one base share assets; never delete-recreate. `whatIf`
  reports what it would create/reuse, trim, and wire — touching no asset.

The **clip-repathing pair** rewrites *clip binding paths* / motion refs in on-disk `.anim` assets — a different
domain from `RemapReferencesByPath` (scene-object refs). Both obey the **read-only-asset rule** (`LAYOUT.md`:
`Assets/Vendor/` + `Packages/` read-only) and are single-controller, **frame-blind** rewriters — the **caller
owns frame-correctness** (descriptor / MA MergeAnimator / VRCFury FullController frames differ, VRCFury may mix
absolute + relative in one controller; no whole-avatar sweep) — though the frame is **discoverable
from the merge component** (`nondestructive.md`), which is exactly what `AnimatorLint`'s `auto` basis reads.

- `RepathClips(controller, oldPaths, newPaths, force=false, whatIf=false)` — deterministic **segment-safe**
  repath of the bindings a controller references (float + objectReference; `Armature/Hips` rewrites
  `Armature/Hips[/…]`, never `Armature/HipsFoo`). **Owned-clips-only** (a read-only clip a move would touch
  FAILs unless `force`); curve-collision + duplicate/empty-path FAIL; every write is re-read from disk and
  content-verified (`force` never bypasses that). Mutates each `.anim` in place; idempotent. `whatIf` previews.
- `OwnControllerClips(controller, outDir, scope=VendorOnly, force=false, whatIf=false)` — closes the CleanController
  gap (owned controller still referencing **vendor clips by GUID**): copies in-scope clips (`VendorOnly` default
  | `All`) to owned `.anim` copies under `outDir` (absent-only reuse) and **mutates the controller**, repointing
  every motion slot; disk-truthful residual post-condition. `UC2 = OwnControllerClips → RepathClips`.

`SweepController(controller, force=false, whatIf=false)` is the mutating half of `AnimatorLint`'s orphan
detection — it destroys an owned controller's sub-assets reachable from no layer (states, state-machines,
blend-trees, behaviours, transitions) plus dead-end transitions, then compacts the null slots left behind. It
applies **no `IsSubAsset` filter**: a controller's real orphans are `HideInHierarchy`, for which `IsSubAsset`
returns false — the same reason `AnimatorLint`'s orphan advisory drops it, so detector and remover census one
set. Extracted from DreadScripts' ControllerCleaner (VRLabs, MIT).

`CompileController(sourcePath, outDir, whatIf=false)` is the animator **write substrate** — the inverse of
`ControllerReport`: it compiles a declarative YAML document into a persisted `.controller` (+ inline clips,
embedded blend trees, and a `VRCExpressionParameters` asset listing every non-builtin/non-scratch param,
**unsynced included, for legibility**). Pipeline: parse → validate → emit → the shared `ControllerRules`
graph lint → atomic persist. Atomic + PASS/FAIL: nothing reaches `outDir` unless every stage passes, a
`whatIf` preview leaves nothing on disk, and a recompile of the same source to the same `outDir` is
idempotent (reset-in-place, stable GUID). The RunLog body carries never-failing advisories — per-layer
frame latency (the longest firing-transition chain — conditional or exit-time; a conditional hop is ~1
frame, an exit-time hop costs its state's clip length) and driver↔AAP isolation conflicts
(a driver cannot durably set a clip-written param — `runtime.md`). The schema — every key, accepted
values, and traps — is `docs/animator-schema.md`; the three worked fixtures
(`vrc-unity-tools/fixtures/animator-substrate/{debounce,smoother,codec}.yaml` — a dwell timer, an AAP
exponential smoother, a float→bool codec) are its runnable companions, each compiling clean, linting PASS,
and rung-3 verified. `ControllerRules` is the lint engine extracted from `AnimatorLint` so the **same** rules run on
this emitted in-memory controller as on a saved asset — the two doors can never disagree.

Two standalone **scene utilities** round out the kit, simple enough that the signature is the contract
(open the tool): `RemapMaterials` — swap materials by **asset path** across a hierarchy, in place (no
source hierarchy, no name matching — a different operation from `ConformRenderers`' copy-by-renderer-name);
`DuplicateAndConstrain` — clone a hierarchy and wire VRC constraints between original and duplicate bones.

**Preview grammar.** Every mutating tool takes a default-off preview: **`whatIf`** when the tool can run
its full plan and mutate nothing (preview == execute — `CopyComponents`/`RelocateComponents`/`GraftHierarchy`
/`ConformRenderers`/`CopyDescriptor`/`FixViewpoint`/`CleanController`/`RepathClips`/`OwnControllerClips`/`SweepController`), or **`preflight`** when the operation can't be
dry-run at all and only its preconditions are checkable (`MatchHumanoidRig`, whose reimport *is* the
operation). The dividing line is *ran the plan and mutated nothing* vs *couldn't run the op at all* — not
complete-vs-incomplete numbers (so `CopyDescriptor` stays `whatIf` even though its remap counts land only on
execute).

The **`own-base` skill** (in `vrc-skills`) orchestrates these — it holds the judgment, gates, and
sequencing; the tools hold the mechanics. In a transplant diagnostic, read what each count *means*: a
**flagged-missing host is PASS** (expected subset — triage the named list), while a **vendor-source leak**
or a **null ref on a copied component** stays stop-and-investigate (almost always a name/path mismatch).

**Renderer-normalization standard:** every renderer's bounds are **ensured ≥** center (0,0,0)/extents
(1,1,1) — grown to that anti-cull floor, never shrunk, so a deliberately larger box survives — the
Anchor Override is set to **Hips** only when invalid (null or not a child of `ownedRoot`); a valid
internal anchor is preserved, and a null Root Bone is filled with Hips. Not copied from the vendor (creators get these wrong). On a *composed*
avatar, Modular Avatar `Mesh Settings` can own bounds/anchor at build — there the tool's writes are
authoring-only, so its PASS is not a runtime guarantee.

## Geometry-change reconcile (reproportion / re-export)

Changing avatar geometry leaves Unity-side state stale — it holds frozen references or meters that do
**not** track the new geometry. The `reproportion` skill sequences this; the durable facts:

- **Humanoid bind.** Frozen into the FBX `.meta` at rig time; it does not self-update. **Re-run
  `MatchHumanoidRig` after any geometry change** or the bind disagrees with the bones (folded hips);
  `ReproportionFreshness` verifies it.
- **ViewPosition** (eye height) is an avatar-local **meters** vector — recompute on any height change or
  the viewpoint floats off the eyes (not sub-notice).
- **Absolute component dimensions** — physbone / collider / contact radii are meters; they don't scale
  with a rescale (drift linear in magnitude, negligible at small reproportions).
- **Prefab-persisted SkinnedMeshRenderer blendshape weights unlink (reset to 0) when a mesh is renamed
  or re-exported** — re-verify driven weights, and keep them coherent across meshes (an outfit's
  matching morph is often name-variant, e.g. `Bra_Breasts_big` ↔ `Breasts_big`). A Blender shape-key
  *value* crosses as the imported blendshape weight (see `blender.md`); body-shape morphs can be set in Blender or here, kept coherent across meshes — the one-value-per-morph coherence invariant is the `reproportion` skill's (*Realizing shapekeys*).

## Non-destructive avatar build

Modern avatar tooling — Modular Avatar (on NDMF), VRCFury, the **d4rk Avatar Optimizer**, the
**Limitex (LAC) texture compressor** — is **non-destructive**: the components do nothing to the editor
scene and rebuild a throwaway copy at Play/upload. They **stack freely on an untouched vendor asset**,
and none deep-copies meshes or textures — add them, don't bake them in. This is what makes a vendor
prefab safe to drop optimizers onto, and what lets animator controllers be merged without editing them.
(There's no Add-Component menu over MCP — discover a tool's exact component type with an `AppDomain`
`MonoBehaviour` scan: e.g. `d4rkAvatarOptimizer`, `dev.limitex.avatar.compressor.TextureCompressor`,
VRCFury features under `VF.Model.Feature.*` held by a `VF.Model.VRCFury` component.)

Validate the baked result without uploading: **enter play mode** — it runs the *whole* stack
(VRCFury services + NDMF/MA + d4rk + LAC) on the transient play copy, removed on exit. One session
is both the baked read (the built clone + `VRCFuryDebugInfo`) and the live drive (av3emulator).
The **play-entry gate** is enforced on entry; `verify.md` owns the preconditions and the rung-3 recipes.

## Sharp edges

- **Bridge "Connection closed" on the first call** after the Editor's been idle or just reloaded —
  retry once; it reconnects.
- **Reading `VRCAvatarDescriptor.baseAnimationLayers` from YAML: the `type` field is the
  `AnimLayerType` enum — Base=0, Additive=2, Gesture=3, Action=4, FX=5 (the enum skips 1,
  `Deprecated0`; special layers: Sitting=6, TPose=7, IKPose=8).** Array index ≠ enum value; an
  off-by-one read misattributes the FX slot as Sitting (a real past misread).
- **`execute_code` is async-blind.** `AssetDatabase.ImportPackage(path, false)` returns before the
  import finishes — verify the asset/folder exists in a separate call before chaining dependent ops.
- **`execute_code` `safety_checks` blocks destructive patterns** (`AssetDatabase.DeleteAsset`,
  `File.Delete`, `Process.Start`, loops). Pass `safety_checks=false` for a narrowly-scoped,
  confirmed-intentional one.
- **Editing asset/package files outside Unity** leaves the asset DB stale ("Build asset version
  error"); clear the console + `refresh_unity` (mode=force, scope=all).
- **`execute_code` wraps your snippet as a method body**, so no top-level `using` directives — the
  wrapper pre-imports `System`, `System.Collections.Generic`, `System.Linq`, `System.Reflection`,
  `UnityEngine`, `UnityEditor`; fully-qualify anything else. Scene creation is `NewSceneMode`, not
  `NewSceneSetupMode`.
- **VRCFury's first build of an avatar lacking a "Fix Write Defaults" component pops a blocking
  dialog** that stalls the build waiting for a click. Hard-check before any build; if absent, add
  the VRCFury Fix Write Defaults component with mode **Disabled** (suppresses the prompt, changes
  nothing).
- **Red `Exception` VRCFury build lines (`Progress (n%): …`, `Importing …`) are plain `Debug.Log` info
  — ignore them.** `read_console` mis-tags them: it substring-matches `Exception` in the stack trace,
  which always routes through `VF.Exceptions`. A real failure aborts the build (dialog), not a log line.
- **FBX external-material remap (`materialLocation: External`) applies only at import time.** A model
  imported before its `.mat` targets exist (costume package before a separate MaterialPack) caches
  empty slots that no later import re-triggers — force-reimport the FBX. `ImportVerify` flags it; the
  `import-vendor-asset` skill owns the procedure.
- **Reparenting a prefab instance's internal children silently no-ops.** `Transform.SetParent` on an
  object owned by a prefab instance reverts with no error — restructure before prefab conversion, or
  edit the asset via `PrefabUtility.LoadPrefabContents`. Verify by `childCount`, not `SetParent` calls.
- **The play-entry gate is enforced in-Editor** — the `PlayGate` hook cancels a mis-set entry with a
  console `[PlayGate] … => FAIL` (each offender + its fix) and a one-shot override; see `verify.md`.
  Entering play **blocks the Editor main thread while the non-destructive build runs**
  (NDMF/VRCFury/d4rk/LAC): `editor_state` freezes and reads can time out for ~minutes on a heavy
  avatar. `execute_code` issued during it **queues and returns once the build frees the thread** — don't
  read the delay/timeout as failure. Batch play-mode work; re-entering play re-runs the whole build.
- **Driving Av3Emulator in play mode: read params via the `LyumaAv3Runtime` `Floats/Ints/Bools` lists,
  never `Animator.Get*`.** The emulator drives its own `PlayableGraph`, so the base `Animator`'s
  parameter dictionary reads empty; observe outputs through those lists, scene transforms/blendshapes,
  or `ContactReceiver.paramValue`/`IsColliding()`. Frames advance only *between* `execute_code` calls.
